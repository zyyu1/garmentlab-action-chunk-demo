"""Formal hold120 batch controller (deployment layer; no simulation itself).

The production backend calls the frozen initial/rollout/audit entrypoints.  The
controller owns source gate, lock, ledger, resume, stop rules and summaries.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def utc():
    return datetime.now(timezone.utc).isoformat()


class Pause(Exception):
    pass


class Controller:
    def __init__(self, slots_path, state_dir, backend, total_slots=120):
        self.slots = read(slots_path)
        self.initials = self.slots['initials']
        self.matrix = self.slots['slots']
        self.state = Path(state_dir)
        self.backend = backend
        self.total_slots = total_slots
        self.ledger = self.state / 'attempts.jsonl'
        self.init_file = self.state / 'init_dirs.json'
        self.summary_file = self.state / 'summary.json'
        self.lock_dir = self.state / 'driver.lock'
        self.completed = self.state / 'completed'
        self.records = []

    def _write(self, rec):
        with self.ledger.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, sort_keys=True) + '\n')
            f.flush()
            os.fsync(f.fileno())
        self.records.append(rec)

    def _load(self):
        if self.ledger.is_file():
            self.records = [json.loads(l) for l in self.ledger.read_text().splitlines() if l.strip()]

    def _finished(self, seed, mode):
        return [r for r in self.records if r.get('state') == 'finished'
                and int(r.get('seed')) == int(seed) and r.get('mode') == mode]

    def _started(self, seed, mode):
        return [r for r in self.records if r.get('state') == 'started'
                and int(r.get('seed')) == int(seed) and r.get('mode') == mode]

    def _initials(self):
        return read(self.init_file) if self.init_file.is_file() else {}

    def run(self):
        self.state.mkdir(parents=True, exist_ok=True)
        try:
            os.mkdir(self.lock_dir)
        except FileExistsError:
            raise Pause('LOCKED ' + str(self.lock_dir))
        try:
            self._load()
            gate = self.backend.gate()
            if gate.get('exit') != 0:
                raise Pause('GATE_FAILED ' + str(gate))
            init_dirs = self._initials()
            for initial in self.initials:
                seed, level = initial['seed'], initial['level']
                if seed not in init_dirs:
                    gen = self.backend.generate_initial(seed, level)
                    if gen.get('exit') != 0 or not gen.get('dir'):
                        raise Pause('INIT_FAILED %s %s %s' % (seed, level, gen))
                    init_dirs[str(seed)] = gen['dir']
                    self.init_file.write_text(json.dumps(init_dirs, indent=2) + '\n', encoding='utf-8')
                for slot in [s for s in self.matrix if s['seed'] == seed]:
                    mode = slot['mode']
                    if self._finished(seed, mode):
                        continue
                    if self._started(seed, mode):
                        raise Pause('UNFINISHED_ATTEMPT %s %s' % (seed, mode))
                    self._write({'state': 'started', 'utc': utc(), 'slot': slot['slot'],
                                 'seed': seed, 'level': level, 'mode': mode,
                                 'initial': init_dirs[str(seed)]})
                    ep = self.backend.run_episode(init_dirs[str(seed)], seed, mode)
                    if ep.get('exit') != 0 or not ep.get('dir') or not (Path(ep['dir']) / 'result.json').is_file():
                        self._write({'state': 'error', 'utc': utc(), 'slot': slot['slot'],
                                     'seed': seed, 'mode': mode, 'error': 'episode_or_missing_result',
                                     'entry_exit': ep.get('exit'), 'result_dir': ep.get('dir')})
                        raise Pause('EPISODE_ERROR %s %s %s' % (seed, mode, ep))
                    verdict = read(Path(ep['dir']) / 'a5-verdict.json')
                    runner_exit = verdict.get('runner_exit')
                    single = self._finished(seed, 'single')
                    pair = single[0]['result_dir'] if single else None
                    au = self.backend.audit(ep['dir'], seed, mode, pair)
                    if au.get('exit') != 0 or not au.get('semantics'):
                        self._write({'state': 'error', 'utc': utc(), 'slot': slot['slot'],
                                     'seed': seed, 'mode': mode, 'error': 'audit_failed',
                                     'entry_exit': ep.get('exit'), 'runner_exit': runner_exit, 'audit_exit': au.get('exit'),
                                     'result_dir': ep['dir']})
                        raise Pause('AUDIT_FAILED %s %s' % (seed, mode))
                    sem = au['semantics']
                    quality = sem.get('quality_status')
                    if quality not in ('accepted', 'rejected'):
                        raise Pause('BAD_QUALITY %s %s' % (seed, mode))
                    rec = {'state': 'finished', 'utc': utc(), 'slot': slot['slot'],
                           'seed': seed, 'level': level, 'mode': mode,
                           'initial': init_dirs[str(seed)], 'result_dir': ep['dir'],
                           'entry_exit': ep.get('exit'), 'runner_exit': runner_exit, 'audit_exit': au.get('exit'),
                           'file_complete': bool(sem.get('file_complete')),
                           'observation_semantics_valid': bool(sem.get('observation_semantics_valid')),
                           'quality_status': quality,
                           'overall_valid': bool(sem.get('overall_valid')),
                           'hold_applicable': bool(sem.get('hold_applicable')),
                           'recovery_hold': bool(sem.get('recovery_hold'))}
                    self._write(rec)
                    if not (rec['file_complete'] and rec['observation_semantics_valid'] and rec['overall_valid']):
                        raise Pause('EVIDENCE_INCOMPLETE %s %s' % (seed, mode))
                    if mode == 'arc4' and not self.backend.pair_ok(single[0]['result_dir'], ep['dir'], seed):
                        self._write({'state': 'error', 'utc': utc(), 'slot': slot['slot'],
                                     'seed': seed, 'mode': mode, 'error': 'pair_or_hold_mismatch',
                                     'result_dir': ep['dir']})
                        raise Pause('PAIR_MISMATCH %s' % seed)
            self.summary_file.write_text(json.dumps(self.summary(), indent=2) + '\n', encoding='utf-8')
            self.completed.write_text('complete\n', encoding='utf-8')
            return self.summary()
        finally:
            rmdir = getattr(os, 'rmdir')
            try:
                rmdir(self.lock_dir)
            except OSError:
                pass

    def summary(self):
        finished = [r for r in self.records if r.get('state') == 'finished']
        errors = [r for r in self.records if r.get('state') == 'error']
        attempted = len({(r['seed'], r['mode']) for r in finished + errors})
        accepted = sum(1 for r in finished if r['quality_status'] == 'accepted')
        rejected = sum(1 for r in finished if r['quality_status'] == 'rejected')
        error = len(errors)
        not_attempted = max(0, self.total_slots - attempted)
        rate = None if attempted == 0 else (rejected + error) / attempted

        def group(key):
            totals = {}
            for s in self.matrix:
                totals[key(s)] = totals.get(key(s), 0) + 1
            rows = {}
            for r in finished + errors:
                k = key(r)
                rows.setdefault(k, {'attempts': 0, 'accepted': 0, 'rejected': 0, 'error': 0,
                                    'not_attempted': 0, 'rejection_rate': None})
            for r in finished + errors:
                k = key(r); g = rows[k]; g['attempts'] += 1
                if r.get('state') == 'error':
                    g['error'] += 1
                elif r['quality_status'] == 'accepted':
                    g['accepted'] += 1
                else:
                    g['rejected'] += 1
            for k, g in rows.items():
                g['not_attempted'] = max(0, totals.get(k, 0) - g['attempts'])
                g['rejection_rate'] = None if g['attempts'] == 0 else (g['rejected'] + g['error']) / g['attempts']
            return rows

        return {'schema': 'formal-hold120-summary-v1', 'total_slots': self.total_slots,
                'attempts': attempted, 'accepted': accepted, 'rejected': rejected,
                'error': error, 'not_attempted': not_attempted,
                'rejection_rate': rate,
                'by_level': group(lambda r: r['level']),
                'by_mode': group(lambda r: r['mode']),
                'cases': [{k: r.get(k) for k in ('slot', 'seed', 'level', 'mode', 'state',
                                                  'quality_status', 'result_dir', 'error')}
                          for r in finished + errors]}

class SubprocessBackend:
    def __init__(self, config):
        self.c = config
        self.app = Path(config['app'])
        self.candidate = Path(config['candidate'])
        self.python = config['python']
        self.audit_script = str(self.candidate / 'audit_hold120_case.py')
        self.gate_script = str(self.candidate / 'gate_rc7_sources.py')
        self.state = Path(config['state'])

    def _run(self, cmd, cwd):
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def gate(self):
        rc, out = self._run([self.python, self.gate_script], self.candidate)
        return {'exit': rc, 'output': out}

    def generate_initial(self, seed, level):
        runner = 'run-square-initial.sh' if level == 'flat' else 'run-square-initial-stripfold.sh'
        rc, out = self._run(['bash', str(self.app / runner), str(seed)], self.app)
        lines = [l[13:] for l in out.splitlines() if l.startswith('DOWNLOAD_DIR ')]
        return {'exit': rc, 'dir': lines[-1] if lines else None, 'output': out}

    def run_episode(self, initial, seed, mode):
        cmd = [self.python, str(self.app / 'a5_entry.py'), 'run', '--initial', initial,
               '--mode', mode, '--split', 'formal', '--journal', str(self.state / 'episodes')]
        rc, out = self._run(cmd, self.app)
        lines = [l[13:] for l in out.splitlines() if l.startswith('DOWNLOAD_DIR ')]
        return {'exit': rc, 'dir': lines[-1] if lines else None, 'output': out}

    def audit(self, result_dir, seed, mode, single_dir=None):
        out = self.state / ('slot-semantics-%s-%s.json' % (seed, mode))
        cmd = [self.python, self.audit_script, '--run', result_dir, '--seed', str(seed),
               '--mode', mode, '--out', str(out)]
        if single_dir:
            cmd += ['--single-dir', single_dir]
        rc, log = self._run(cmd, self.candidate)
        return {'exit': rc, 'semantics': json.loads(out.read_text()) if out.is_file() else None,
                'output': log}

    def pair_ok(self, single_dir, arc_dir, seed):
        s = read(Path(single_dir) / 'result.json')
        a = read(Path(arc_dir) / 'result.json')
        if seed == 4100 or str(seed).startswith('41'):
            x = s['actions'][0]['target_pose']; y = a['actions'][0]['target_pose']
        else:
            x = next(z['target_pose'] for z in s['actions'] if z['label'] == 'fold_approach')
            y = next(z['target_pose'] for z in a['actions'] if z['label'] == 'fold_approach')
        if max(abs(float(p) - float(q)) for p, q in zip(x, y)) > 1e-6:
            return False
        if str(seed).startswith('42') or str(seed).startswith('43'):
            for d in (single_dir, arc_dir):
                h = read(Path(d) / 'recovery_hold_metadata.json')
                if int(h['completed_steps']) != 120 or int(h['frames']) != 121 or abs(float(h['duration_s']) - 2.0) > 1e-6:
                    return False
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, default=HERE / 'formal_config.json')
    ap.add_argument('--state', type=Path)
    ap.add_argument('--preflight', action='store_true')
    a = ap.parse_args()
    config = read(a.config)
    if a.state:
        config['state'] = str(a.state)
    if a.preflight:
        b = SubprocessBackend(config)
        g = b.gate()
        if g['exit'] != 0:
            raise SystemExit('GATE_FAILED ' + g['output'])
        slots = read(config['slots'])
        assert slots['counts'] == {'initials': 60, 'slots': 120}
        print('FORMAL_HOLD120_PREFLIGHT_OK', config['state'])
        return
    b = SubprocessBackend(config)
    c = Controller(config['slots'], config['state'], b)
    try:
        s = c.run()
    except Pause as exc:
        print('FORMAL_HOLD120_PAUSED', exc)
        raise SystemExit(3)
    print('FORMAL_HOLD120_COMPLETE', json.dumps({k: s[k] for k in
          ('attempts', 'accepted', 'rejected', 'error', 'not_attempted', 'rejection_rate')}))


if __name__ == '__main__':
    main()
