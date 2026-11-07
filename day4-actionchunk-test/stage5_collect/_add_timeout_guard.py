from pathlib import Path

p = Path('collect_demos.py')
s = p.read_text(encoding='utf-8')

if 'import signal' not in s:
    s = s.replace('import subprocess\n', 'import signal\nimport subprocess\n', 1)

helper = '''EPISODE_TIMEOUT_S = 2700


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


'''
anchor = 'def split_for(seed, accepted_sorted):'
assert anchor in s
if 'def run_with_timeout' not in s:
    s = s.replace(anchor, helper + anchor, 1)

old = '''    def run_episode(self, initial, seed, level):
        split = self.cfg.get('split', 'formal')
        if split == 'demo':
            cmd = [self.python, str(HERE / 'demo' / 'a5_entry_demo.py'), 'run',
                   '--initial', str(initial), '--mode', 'single', '--split', 'demo',
                   '--journal', str(self.journal)]
        else:
            cmd = [self.python, str(HERE / 'adapter_run.py'), 'run',
                   '--initial', str(initial), '--mode', 'single', '--split', split,
                   '--journal', str(self.journal)]
        p = subprocess.run(cmd, cwd=str(self.app), capture_output=True, text=True)
        out = p.stdout + p.stderr
        dirs = [l[13:] for l in out.splitlines() if l.startswith('DOWNLOAD_DIR ')]
        return {'exit': p.returncode, 'dir': dirs[-1] if dirs else None, 'output': out[-4000:]}'''

new = '''    def run_episode(self, initial, seed, level):
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
                'output': out, 'timeout': r['timeout']}'''
assert old in s, 'run_episode body not found'
s = s.replace(old, new, 1)

old2 = '''                ep = self.run_episode(initial, seed, level)'''
new2 = '''                ep = self.run_episode(initial, seed, level)
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
                    raise SystemExit('EPISODE_TIMEOUT seed=%s log=%s' % (seed, tlog))'''
assert old2 in s, 'episode call not found'
s = s.replace(old2, new2, 1)

p.write_text(s, encoding='utf-8')
print('timeout_guard_added')
