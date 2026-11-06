"""Stage 5 minimal demonstration collector.

One process per episode (no in-process scene reuse), single GPU, serial.
Reuses adapter_run.py -> a5_entry.py run (frozen candidate); only episodes whose
verdict is 'accepted' enter demonstrations; every attempt is kept in the ledger.

Default mode is --plan-only: prints the schedule and exits without GPU.
"""
import argparse
import hashlib
import json
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


def split_for(seed, accepted_sorted):
    """70/15/15 by seed order within a level (episode-level split)."""
    n = len(accepted_sorted)
    idx = accepted_sorted.index(int(seed))
    if idx < int(0.7 * n):
        return 'train'
    if idx < int(0.85 * n):
        return 'val'
    return 'test'


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
        return {'manifest_sha256': sha(self.app / 'a5-manifest.json'),
                'gate': p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ''}

    # -- episode ------------------------------------------------------
    def run_episode(self, initial, seed, level):
        cmd = [self.python, str(HERE / 'adapter_run.py'), 'run',
               '--initial', str(initial), '--mode', 'single', '--split', 'formal',
               '--journal', str(self.journal)]
        p = subprocess.run(cmd, cwd=str(self.app), capture_output=True, text=True)
        out = p.stdout + p.stderr
        dirs = [l[13:] for l in out.splitlines() if l.startswith('DOWNLOAD_DIR ')]
        return {'exit': p.returncode, 'dir': dirs[-1] if dirs else None, 'output': out[-4000:]}

    def record(self, path, rec):
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, sort_keys=True) + '\n')
            f.flush()

    def load_attempts(self):
        if self.attempts.is_file():
            return [json.loads(l) for l in self.attempts.read_text().splitlines() if l.strip()]
        return []

    # -- main ---------------------------------------------------------
    def run(self, plan_only):
        info = self.preflight()
        seeds = self.cfg['seeds']
        target = int(self.cfg['target_per_level'])
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
            accepted = [r['seed'] for r in done if r.get('state') == 'accepted']
            attempts = len(done)
            for seed in seeds[level]:
                if len(accepted) >= target or attempts >= cap:
                    break
                if any(r.get('seed') == seed for r in done):
                    continue
                initial = self.initials.get(str(seed))
                if not initial or not (Path(initial) / 'result.json').is_file():
                    self.record(self.attempts, {'state': 'error', 'utc': utc(), 'seed': seed,
                                                'level': level, 'error': 'missing_initial',
                                                'initial': initial})
                    attempts += 1
                    continue
                self.record(self.attempts, {'state': 'started', 'utc': utc(), 'seed': seed,
                                            'level': level, 'initial': initial})
                ep = self.run_episode(initial, seed, level)
                verdict = None
                if ep['dir'] and (Path(ep['dir']) / 'a5-verdict.json').is_file():
                    verdict = read(Path(ep['dir']) / 'a5-verdict.json')
                status = (verdict or {}).get('status')
                attempts += 1
                self.record(self.attempts, {'state': status or 'error', 'utc': utc(), 'seed': seed,
                                            'level': level, 'initial': initial,
                                            'result_dir': ep['dir'], 'entry_exit': ep['exit'],
                                            'manifest_sha256': (verdict or {}).get('manifest_sha256')})
                if status == 'accepted':
                    accepted.append(seed)
                    self.record(self.demos, {'seed': seed, 'level': level,
                                             'result_dir': ep['dir'], 'initial': initial,
                                             'manifest_sha256': (verdict or {}).get('manifest_sha256'),
                                             'recorded_utc': utc()})
            self.summary.write_text(json.dumps({
                'level': level, 'attempts': attempts, 'accepted': len(accepted),
                'stop': 'target' if len(accepted) >= target else ('cap' if attempts >= cap else 'seeds_exhausted'),
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
