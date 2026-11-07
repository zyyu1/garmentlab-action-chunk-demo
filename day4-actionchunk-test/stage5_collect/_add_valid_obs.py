from pathlib import Path

p = Path('collect_demos.py')
s = p.read_text(encoding='utf-8')
anchor = '    # -- main ---------------------------------------------------------\n'
assert anchor in s, 'anchor missing'
method = '''    def _valid_obs(self, rec):
        """Valid demo evidence: per-episode obs dir with one obs per action."""
        base = os.environ.get('STAGE5_OBS_DIR')
        rd = rec.get('result_dir')
        if not base or not rd:
            return None
        d = Path(base) / Path(rd).name
        if not d.is_dir():
            return None
        files = sorted(d.glob('action_*_obs.npz'))
        rp = Path(rd) / 'result.json'
        if not rp.is_file():
            return None
        try:
            n = len(read(rp).get('actions') or [])
        except Exception:
            return None
        if n == 0 or len(files) != n:
            return None
        try:
            import numpy as np
            for f in files:
                z = np.load(f)
                if z['vertices'].shape != (441, 3) or z['quat'].shape != (4,):
                    return None
        except Exception:
            return None
        return {'obs_dir': str(d), 'obs_count': len(files), 'action_count': n}

'''
s = s.replace(anchor, method + anchor)
p.write_text(s, encoding='utf-8')
print('method_added')
