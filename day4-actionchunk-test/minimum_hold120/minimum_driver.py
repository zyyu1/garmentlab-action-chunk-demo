"""Minimum Stage 4 acceptance driver: per level, stop at 5 valid successes.

Single expert only.  Frozen candidate/physics/evaluator; new plan and ledger.
"""
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'formal_hold120'))
from formal_driver import SubprocessBackend, Pause, read  # noqa: E402


class MinimumBackend(SubprocessBackend):
    def run_episode(self, initial, seed, mode):
        import subprocess
        cmd = [self.python, str(HERE / 'adapter_run.py'), 'run', '--initial', initial,
               '--mode', mode, '--split', 'formal', '--journal', str(self.state / 'episodes')]
        p = subprocess.run(cmd, cwd=str(self.app), capture_output=True, text=True)
        out = p.stdout + p.stderr
        lines = [l[13:] for l in out.splitlines() if l.startswith('DOWNLOAD_DIR ')]
        return {'exit': p.returncode, 'dir': lines[-1] if lines else None, 'output': out}


def utc():
    return datetime.now(timezone.utc).isoformat()


class MinimumController:
    def __init__(self, slots_path, state_dir, backend):
        self.slots = read(slots_path)
        self.matrix = self.slots['slots']
        self.state = Path(state_dir)
        self.backend = backend
        self.ledger = self.state / 'attempts.jsonl'
        self.init_file = self.state / 'init_dirs.json'
        self.screen_file = self.state / 'screenshots.json'
        self.summary_file = self.state / 'summary.json'
        self.lock_dir = self.state / 'driver.lock'
        self.completed = self.state / 'completed'
        self.records = []
        self.shots = {}

    def _write(self, rec):
        with self.ledger.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, sort_keys=True) + '\n')
            f.flush(); os.fsync(f.fileno())
        self.records.append(rec)

    def _load(self):
        if self.ledger.is_file():
            self.records = [json.loads(l) for l in self.ledger.read_text().splitlines() if l.strip()]
        if self.init_file.is_file():
            self.initials = read(self.init_file)
        else:
            self.initials = {}
        if self.screen_file.is_file():
            self.shots = read(self.screen_file)

    def _save_init(self):
        self.init_file.write_text(json.dumps(self.initials, indent=2) + '\n', encoding='utf-8')

    def _save_shots(self):
        self.screen_file.write_text(json.dumps(self.shots, indent=2) + '\n', encoding='utf-8')

    def _finished(self, seed):
        return [r for r in self.records if r.get('state') == 'finished' and int(r['seed']) == int(seed)]

    def _error(self, seed):
        return [r for r in self.records if r.get('state') == 'error' and int(r['seed']) == int(seed)]

    def _started(self, seed):
        return [r for r in self.records if r.get('state') == 'started' and int(r['seed']) == int(seed)]

    def _ensure_initial(self, seed, level):
        if str(seed) in self.initials:
            d = Path(self.initials[str(seed)])
            if (d / 'result.json').is_file():
                return d
        g = self.backend.generate_initial(seed, level)
        if g.get('exit') != 0 or not g.get('dir') or not (Path(g['dir']) / 'result.json').is_file():
            raise Pause('INIT_FAILED %s %s %s' % (seed, level, g))
        self.initials[str(seed)] = g['dir']; self._save_init()
        return Path(g['dir'])

    def _screenshot(self, seed, level):
        key = '%s-%s' % (level, seed)
        if key in self.shots:
            return
        d = self._ensure_initial(seed, level)
        shot = self.state / 'initial_screenshots' / (key + '.png')
        shot.parent.mkdir(parents=True, exist_ok=True)
        src = d / 'initial.png'
        if not src.is_file():
            raise Pause('MISSING_INITIAL_SCREENSHOT %s' % key)
        shutil.copy2(src, shot)
        import hashlib
        self.shots[key] = {'level': level, 'seed': seed,
                           'initial_dir': str(d), 'screenshot': str(shot),
                           'screenshot_sha256': hashlib.sha256(shot.read_bytes()).hexdigest(),
                           'initial_geometry_sha256': hashlib.sha256((d / 'initial_geometry.npz').read_bytes()).hexdigest()}
        self._save_shots()

    def run(self):
        self.state.mkdir(parents=True, exist_ok=True)
        try:
            os.mkdir(self.lock_dir)
        except FileExistsError:
            raise Pause('LOCKED ' + str(self.lock_dir))
        try:
            self._load()
            g = self.backend.gate()
            if g.get('exit') != 0:
                raise Pause('GATE_FAILED ' + str(g))
            # Fixed first 10 seeds per level for initial-state screenshots.
            for row in self.slots['screenshot_seeds']:
                self._screenshot(row['seed'], row['level'])
            levels = []
            for level in ('flat', 'perturbed', 'crumpled'):
                seed_slots = [s for s in self.matrix if s['level'] == level]
                finished = {int(r['seed']): r for r in self.records if r.get('state') == 'finished'}
                errors = {int(r['seed']): r for r in self.records
                          if r.get('state') == 'error' and r['level'] == level}
                successes = sum(1 for s in seed_slots if int(s['seed']) in finished
                                and finished[int(s['seed'])]['quality_status'] == 'accepted')
                attempts = sum(1 for s in seed_slots if int(s['seed']) in finished or int(s['seed']) in errors)
                reason = None
                for slot in seed_slots:
                    if successes >= 5:
                        reason = 'five_valid_successes'; break
                    if attempts >= 20:
                        reason = 'attempt_limit_20'; break
                    seed = int(slot['seed'])
                    if seed in finished or seed in errors:
                        continue
                    if self._started(seed):
                        raise Pause('UNFINISHED_ATTEMPT %s' % seed)
                    d = self._ensure_initial(seed, level)
                    self._write({'state': 'started', 'utc': utc(), 'slot': slot['slot'],
                                 'seed': seed, 'level': level, 'mode': 'single',
                                 'initial': str(d)})
                    ep = self.backend.run_episode(str(d), seed, 'single')
                    if not ep.get('dir') or not (Path(ep['dir']) / 'result.json').is_file():
                        self._write({'state': 'error', 'utc': utc(), 'slot': slot['slot'],
                                     'seed': seed, 'level': level, 'mode': 'single',
                                     'error': 'episode_or_missing_result', 'entry_exit': ep.get('exit')})
                        raise Pause('EPISODE_ERROR %s' % seed)
                    verdict = read(Path(ep['dir']) / 'a5-verdict.json')
                    if verdict.get('status') not in ('accepted', 'rejected'):
                        self._write({'state': 'error', 'utc': utc(), 'slot': slot['slot'],
                                     'seed': seed, 'level': level, 'mode': 'single',
                                     'error': 'execution_error', 'entry_exit': ep.get('exit'),
                                     'result_dir': ep['dir']})
                        raise Pause('EXECUTION_ERROR %s' % seed)
                    au = self.backend.audit(ep['dir'], seed, 'single')
                    if au.get('exit') != 0 or not au.get('semantics'):
                        self._write({'state': 'error', 'utc': utc(), 'slot': slot['slot'],
                                     'seed': seed, 'level': level, 'mode': 'single',
                                     'error': 'audit_failed', 'entry_exit': ep.get('exit'),
                                     'audit_exit': au.get('exit'), 'result_dir': ep['dir']})
                        raise Pause('AUDIT_FAILED %s' % seed)
                    sem = au['semantics']
                    rec = {'state': 'finished', 'utc': utc(), 'slot': slot['slot'],
                           'seed': seed, 'level': level, 'mode': 'single',
                           'initial': str(d), 'result_dir': ep['dir'],
                           'entry_exit': ep.get('exit'), 'runner_exit': verdict.get('runner_exit'),
                           'audit_exit': au.get('exit'),
                           'file_complete': bool(sem.get('file_complete')),
                           'observation_semantics_valid': bool(sem.get('observation_semantics_valid')),
                           'quality_status': sem.get('quality_status'),
                           'overall_valid': bool(sem.get('overall_valid')),
                           'hold_applicable': bool(sem.get('hold_applicable')),
                           'recovery_hold': bool(sem.get('recovery_hold'))}
                    self._write(rec)
                    attempts += 1
                    if not (rec['file_complete'] and rec['observation_semantics_valid'] and rec['overall_valid']):
                        raise Pause('EVIDENCE_INCOMPLETE %s' % seed)
                    if rec['quality_status'] not in ('accepted', 'rejected'):
                        raise Pause('BAD_QUALITY %s' % seed)
                    if rec['quality_status'] == 'accepted':
                        successes += 1
                if reason is None:
                    if successes >= 5:
                        reason = 'five_valid_successes'
                    elif attempts >= 20:
                        reason = 'attempt_limit_20'
                    else:
                        reason = 'seed_list_exhausted'
                levels.append({'level': level, 'successes': successes, 'attempts': attempts,
                               'rejected': attempts - successes, 'not_attempted': 20 - attempts,
                               'rejection_rate': None if attempts == 0 else (attempts - successes) / attempts,
                               'stop_reason': reason, 'passed': successes >= 5})
            self.summary_file.write_text(json.dumps({'levels': levels,
                                                     'passed': all(x['passed'] for x in levels),
                                                     'rule': 'per level stop at 5 valid successes; max 20 attempts'},
                                                    indent=2) + '\n', encoding='utf-8')
            self.completed.write_text('complete\n', encoding='utf-8')
            return {'levels': levels, 'passed': all(x['passed'] for x in levels)}
        finally:
            try:
                os.rmdir(self.lock_dir)
            except OSError:
                pass


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, default=HERE / 'minimum_config.json')
    ap.add_argument('--preflight', action='store_true')
    ap.add_argument('--state', type=Path)
    a = ap.parse_args()
    c = read(a.config)
    if a.state:
        c['state'] = str(a.state)
    if a.preflight:
        b = MinimumBackend(c)
        g = b.gate()
        if g['exit'] != 0:
            raise SystemExit('GATE_FAILED ' + g['output'])
        s = read(c['slots'])
        assert s['initials'] == 60 and len(s['slots']) == 60
        assert len(s['screenshot_seeds']) == 30
        print('MINIMUM_HOLD120_PREFLIGHT_OK', c['state'])
        return
    b = MinimumBackend(c)
    ctl = MinimumController(c['slots'], c['state'], b)
    try:
        s = ctl.run()
    except Pause as exc:
        print('MINIMUM_HOLD120_PAUSED', exc)
        raise SystemExit(3)
    print('MINIMUM_HOLD120_COMPLETE', json.dumps(s))


if __name__ == '__main__':
    main()
