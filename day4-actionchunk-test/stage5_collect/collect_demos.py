"""Stage 5 minimal demonstration collector.

One process per episode (no in-process scene reuse), single GPU, serial.
Reuses adapter_run.py -> a5_entry.py run (frozen candidate); only episodes whose
verdict is 'accepted' enter demonstrations; every attempt is kept in the ledger.

Default mode is --plan-only: prints the schedule and exits without GPU.
"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


EPISODE_TIMEOUT_S = 2700


def run_with_timeout(cmd, cwd, env, timeout):
    """Run one episode in its own process group; kill the group on timeout."""
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=timeout)
        return {'exit': p.returncode, 'timeout': False, 'output': out}
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            out, _ = p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, _ = p.communicate()
        return {'exit': p.returncode, 'timeout': True, 'output': out}


def split_for(seed, accepted_sorted):
    """70/15/15 by seed order within a level (episode-level split)."""
    n = len(accepted_sorted)
    idx = accepted_sorted.index(int(seed))
    if idx < int(0.7 * n):
        return 'train'
    if idx < int(0.85 * n):
        return 'val'
    return 'test'


def _episode_started(seed, records):
    """A seed consumed its one episode attempt only if a rollout actually started."""
    return any(int(r.get('seed', -1)) == int(seed) and r.get('state') == 'started'
               for r in records)


class Collector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.app = Path(cfg['app'])
        self.candidate = Path(cfg['candidate'])
        self.python = cfg['python']
        self.state = Path(cfg['state'])
        self.journal = Path(cfg.get('journal', self.state / 'episodes'))
        self.attempts = self.state / 'attempts.jsonl'
        self.demos = self.state / 'demonstrations.jsonl'
        self.summary = self.state / 'summary.json'
        if cfg.get('initials_file'):
            self.initials = read(cfg['initials_file'])
        else:
            self.initials = cfg.get('initials', {})

    # -- identity -----------------------------------------------------
    def preflight(self):
        need = [self.app / 'a5_entry.py', self.app / 'a5-manifest.json',
                HERE / 'adapter_run.py', self.candidate / 'E_RELEASE.json',
                self.candidate / 'gate_rc7_sources.py']
        missing = [str(p) for p in need if not p.is_file()]
        if missing:
            raise SystemExit('MISSING ' + json.dumps(missing))
        p = subprocess.run([self.python, str(self.candidate / 'gate_rc7_sources.py')],
                           cwd=str(self.candidate), capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit('GATE_FAILED ' + p.stdout + p.stderr)
        seed_check = self.check_seed_pool()
        return {'manifest_sha256': sha(self.app / 'a5-manifest.json'),
                'gate': p.stdout.strip().splitlines()[-1] if p.stdout.strip() else '',
                'seed_pool': seed_check}

    def check_seed_pool(self):
        """Verify every registered seed can be authorised and generated."""
        split = self.cfg.get('split', 'formal')
        report = {'split': split, 'blocked': False}
        if split == 'demo':
            demo = HERE / 'demo'
            if not os.environ.get('STAGE5_OBS_DIR'):
                raise SystemExit('OBS_DIR_MISSING: STAGE5_OBS_DIR is required for split=demo '
                                 '(pre-action observations would be lost)')
            need = ['stage5-demo-seeds.json', 'stage5-demo-initial-plan.json',
                    'stage5-demo-initial-files.json', 'a5_entry_demo.py', 'run-demo-initial.sh']
            missing = [n for n in need if not (demo / n).is_file()]
            if missing:
                raise SystemExit('DEMO_LAYER_MISSING ' + json.dumps(missing))
            ranges = read(demo / 'stage5-demo-seeds.json')['ranges']
            plan = {(int(r['seed']), r['level'])
                    for r in read(demo / 'stage5-demo-initial-plan.json')['episodes']}
            report.update({'demo_layer_present': True, 'plan_entries': len(plan),
                           'ranges': ranges, 'missing_plan': {}, 'out_of_range': {},
                           'missing_initial': {}})
            for level, seeds in self.cfg['seeds'].items():
                lo, hi = ranges[level]
                for seed in seeds:
                    if (int(seed), level) not in plan:
                        report['missing_plan'].setdefault(level, []).append(int(seed))
                    if not (int(lo) <= int(seed) <= int(hi)):
                        report['out_of_range'].setdefault(level, []).append(int(seed))
                    initial = self.initials.get(str(seed))
                    if not initial or not (Path(initial) / 'result.json').is_file():
                        report['missing_initial'].setdefault(level, []).append(int(seed))
            report['blocked'] = bool(report['missing_plan'] or report['out_of_range'])
            report['initials_required_at_launch'] = True
            report['initials_generated_on_demand'] = True
            report['missing_initial_counts'] = {k: len(v) for k, v in report.pop('missing_initial').items()}
            if report['blocked']:
                raise SystemExit('DEMO_POOL_BLOCKED ' + json.dumps(report))
            return report

        plan = read(self.app / 'square-initial-plan.json')['episodes']
        plan_keys = {(int(r['seed']), r['level']) for r in plan}
        held = read(self.app / 'stage4-heldout-seeds.json')['heldout']
        held_seeds = {int(r['seed']) for r in held}
        dev = {int(k) for k in read(self.app / 'a5-candidate.json').get('development', {})}
        report.update({'missing_plan': {}, 'missing_auth': {}, 'missing_initial': {}})
        for level, seeds in self.cfg['seeds'].items():
            for seed in seeds:
                if (int(seed), level) not in plan_keys:
                    report['missing_plan'].setdefault(level, []).append(int(seed))
                if split == 'formal' and int(seed) not in held_seeds:
                    report['missing_auth'].setdefault(level, []).append(int(seed))
                if split == 'dev' and int(seed) not in dev:
                    report['missing_auth'].setdefault(level, []).append(int(seed))
                initial = self.initials.get(str(seed))
                if not initial or not (Path(initial) / 'result.json').is_file():
                    report['missing_initial'].setdefault(level, []).append(int(seed))
        report['blocked'] = any(report[k] for k in ('missing_plan', 'missing_auth', 'missing_initial'))
        if report['blocked']:
            raise SystemExit('SEED_POOL_BLOCKED ' + json.dumps(report))
        return report

    # -- episode ------------------------------------------------------
    def run_episode(self, initial, seed, level):
        split = self.cfg.get('split', 'formal')
        if split == 'demo':
            cmd = [self.python, str(HERE / 'demo' / 'a5_entry_demo.py'), 'run',
                   '--initial', str(initial), '--mode', 'single', '--split', 'demo',
                   '--journal', str(self.journal)]
        else:
            cmd = [self.python, str(HERE / 'adapter_run.py'), 'run',
                   '--initial', str(initial), '--mode', 'single', '--split', split,
                   '--journal', str(self.journal)]
        r = run_with_timeout(cmd, str(self.app), dict(os.environ),
                             int(self.cfg.get('episode_timeout_s', EPISODE_TIMEOUT_S)))
        out = r.get('output') or ''
        lines = [l[13:] for l in out.splitlines() if l.startswith('DOWNLOAD_DIR ')]
        return {'exit': r['exit'], 'dir': lines[-1] if lines else None,
                'output': out, 'timeout': r['timeout']}

    def generate_initial(self, seed):
        p = subprocess.run(['bash', str(HERE / 'demo' / 'run-demo-initial.sh'), str(seed)],
                           cwd=str(HERE / 'demo'), capture_output=True, text=True)
        out = p.stdout + p.stderr
        dirs = [l[len('DEMO_INITIAL_DIR '):] for l in out.splitlines() if l.startswith('DEMO_INITIAL_DIR ')]
        return {'exit': p.returncode, 'dir': dirs[-1] if dirs else None, 'output': out[-3000:]}

    def record(self, path, rec):
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, sort_keys=True) + '\n')
            f.flush()

    def load_attempts(self):
        if self.attempts.is_file():
            return [json.loads(l) for l in self.attempts.read_text().splitlines() if l.strip()]
        return []

    def _obs_reason(self, rec):
        """Return a specific reason string when the obs archive is invalid, else None."""
        base = os.environ.get('STAGE5_OBS_DIR')
        rd = rec.get('result_dir')
        if not base:
            return 'STAGE5_OBS_DIR unset'
        if not rd:
            return 'no result_dir'
        d = Path(base) / Path(rd).name
        if not d.is_dir():
            return 'obs dir missing: %s' % d
        files = sorted(d.glob('action_*_obs.npz'))
        rp = Path(rd) / 'result.json'
        if not rp.is_file():
            return 'result.json missing: %s' % rp
        try:
            n = len(read(rp).get('actions') or [])
        except Exception as exc:
            return 'result.json unreadable: %r' % exc
        if n == 0:
            return 'zero actions in result.json'
        if len(files) != n:
            return 'obs count %d != action count %d' % (len(files), n)
        try:
            import numpy as np
            for f in files:
                z = np.load(f)
                if z['vertices'].shape != (441, 3) or z['quat'].shape != (4,):
                    return 'bad npz shapes: %s' % f.name
        except Exception as exc:
            return 'npz unreadable: %r' % exc
        return None

    def _valid_obs(self, rec):
        """Valid demo evidence: per-episode obs dir with one obs per action."""
        if self._obs_reason(rec):
            return None
        base = os.environ['STAGE5_OBS_DIR']
        d = Path(base) / Path(rec['result_dir']).name
        files = sorted(d.glob('action_*_obs.npz'))
        n = len(read(Path(rec['result_dir']) / 'result.json').get('actions') or [])
        return {'obs_dir': str(d), 'obs_count': len(files), 'action_count': n}

    def _verify_export(self, rec):
        """Full demo gate; returns (evidence, None) or (None, reason)."""
        reason = self._obs_reason(rec)
        if reason:
            return None, reason
        obs = self._valid_obs(rec)
        rd = rec.get('result_dir')
        out = self.state / 'exports' / ('%s-%s' % (rec.get('level'), rec.get('seed')))
        cmd = [self.python, str(HERE / 'verify_export.py'), '--run-dir', str(rd),
               '--obs-dir', obs['obs_dir'], '--phase-map', str(HERE / 'phase_map.json'),
               '--out', str(out)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            return None, 'export subprocess rc=%d: %s' % (p.returncode, (p.stderr or '')[-400:])
        try:
            s = json.loads((out / 'export_summary.json').read_text(encoding='utf-8'))
        except Exception as exc:
            return None, 'export summary unreadable: %r' % exc
        c = s.get('checks') or {}
        failed = [k for k in ('count_match', 'pairing_ok', 'quat_shape_ok', 'quat_unit_norm')
                  if not c.get(k)]
        if s.get('verdict_status') != 'accepted':
            failed.append('verdict_status=%r' % s.get('verdict_status'))
        if (s.get('single_step') or {}).get('count') != obs['action_count']:
            failed.append('single_step_count')
        if not (s.get('h4') or {}).get('no_cross_episode'):
            failed.append('h4_no_cross_episode')
        if failed:
            return None, 'export checks failed: ' + ','.join(failed)
        return {'obs_dir': obs['obs_dir'], 'export_dir': str(out),
                'obs_count': obs['obs_count'], 'action_count': obs['action_count'],
                'single_step': s['single_step']['count'], 'h4_chunks': s['h4']['total_chunks']}, None

    # -- main ---------------------------------------------------------
    def run(self, plan_only):
        info = self.preflight()
        seeds = self.cfg['seeds']
        default_target = int(self.cfg['target_per_level'])
        cap = int(self.cfg['max_attempts_per_level'])
        if plan_only:
            print(json.dumps({'mode': 'plan_only', **info,
                              'levels': {k: {'seeds': len(v), 'target': target, 'cap': cap}
                                         for k, v in seeds.items()}}, indent=2))
            return
        self.state.mkdir(parents=True, exist_ok=True)
        prior = self.load_attempts()
        for level in ('flat', 'perturbed', 'crumpled'):
            done = [r for r in prior if r.get('level') == level]
            accepted = [r['seed'] for r in done
                        if r.get('state') == 'accepted' and self._verify_export(r)[0]]
            attempts = sum(1 for s in seeds[level] if _episode_started(s, done))
            target = int((self.cfg.get('targets') or {}).get(level, default_target))
            for seed in seeds[level]:
                if len(accepted) >= target or attempts >= cap:
                    break
                if _episode_started(seed, done):
                    continue
                initial = self.initials.get(str(seed))
                if not initial or not (Path(initial) / 'result.json').is_file():
                    if self.cfg.get('split') == 'demo':
                        gen = self.generate_initial(seed)
                        if not gen['dir']:
                            self.record(self.attempts, {'state': 'error', 'utc': utc(), 'seed': seed,
                                                        'level': level, 'error': 'initial_generation_failed',
                                                        'output': gen.get('output')})
                            raise SystemExit('INIT_FAILED %s %s' % (seed, gen))
                        initial = gen['dir']
                        self.initials[str(seed)] = initial
                    else:
                        self.record(self.attempts, {'state': 'error', 'utc': utc(), 'seed': seed,
                                                    'level': level, 'error': 'missing_initial',
                                                    'initial': initial})
                        attempts += 1
                        continue
                self.record(self.attempts, {'state': 'started', 'utc': utc(), 'seed': seed,
                                            'level': level, 'initial': initial})
                ep = self.run_episode(initial, seed, level)
                if ep.get('timeout'):
                    tdir = self.state / 'timeouts'
                    tdir.mkdir(parents=True, exist_ok=True)
                    tlog = tdir / ('%s-%s.log' % (seed, utc().replace(':', '')))
                    tlog.write_text(ep.get('output') or '', encoding='utf-8')
                    self.record(self.attempts, {'state': 'error', 'utc': utc(), 'seed': seed,
                                                'level': level, 'initial': initial,
                                                'error': 'episode_timeout',
                                                'timeout_s': int(self.cfg.get('episode_timeout_s', EPISODE_TIMEOUT_S)),
                                                'log': str(tlog)})
                    raise SystemExit('EPISODE_TIMEOUT seed=%s log=%s' % (seed, tlog))
                verdict = None
                if ep['dir'] and (Path(ep['dir']) / 'a5-verdict.json').is_file():
                    verdict = read(Path(ep['dir']) / 'a5-verdict.json')
                status = (verdict or {}).get('status')
                attempts += 1
                rec = {'state': status or 'error', 'utc': utc(), 'seed': seed,
                       'level': level, 'initial': initial,
                       'result_dir': ep['dir'], 'entry_exit': ep['exit'],
                       'manifest_sha256': (verdict or {}).get('manifest_sha256')}
                self.record(self.attempts, rec)
                if status == 'accepted':
                    valid, reason = self._verify_export(rec)
                    if valid:
                        accepted.append(seed)
                        self.record(self.demos, {'seed': seed, 'level': level,
                                                 'result_dir': ep['dir'], 'initial': initial,
                                                 'manifest_sha256': (verdict or {}).get('manifest_sha256'),
                                                 'obs': valid, 'recorded_utc': utc()})
                    else:
                        self.record(self.attempts, {'state': 'error', 'utc': utc(), 'seed': seed,
                                                    'level': level, 'result_dir': ep['dir'],
                                                    'error': 'export_gate_failed', 'reason': reason})
                        raise SystemExit('EXPORT_GATE_FAILED seed=%s reason=%s' % (seed, reason))
            self.summary.write_text(json.dumps({
                'level': level, 'attempts': attempts, 'accepted': len(accepted),
                'stop': 'target' if len(accepted) >= target else ('cap' if attempts >= cap else 'seeds_exhausted'),
                'target': target,
                'rule': 'one process per episode; accepted only; keep all attempts',
            }, indent=2) + '\n', encoding='utf-8')
        print('STAGE5_COLLECT_DONE')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, default=HERE / 'stage5_config.json')
    ap.add_argument('--run', action='store_true',
                    help='actually launch episodes (default: plan-only, no GPU)')
    ap.add_argument('--preflight', action='store_true')
    a = ap.parse_args()
    c = read(a.config)
    ctl = Collector(c)
    if a.preflight:
        print(json.dumps(ctl.preflight(), indent=2))
        return
    ctl.run(plan_only=not a.run)


if __name__ == '__main__':
    main()
