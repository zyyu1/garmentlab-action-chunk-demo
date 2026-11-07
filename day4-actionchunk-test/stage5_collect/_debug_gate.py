import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '/root/autodl-tmp/stage5-trial/collect')
os.environ['STAGE5_OBS_DIR'] = '/root/autodl-tmp/stage5-trial/obs-formal'
import collect_demos as cd  # noqa: E402

cfg = json.loads(Path('/root/autodl-tmp/stage5-trial/collect/trial/stage5_config_formal.json').read_text())
ctl = cd.Collector(cfg)
rows = [json.loads(l) for l in ctl.attempts.read_text().splitlines() if l.strip()]
for seed in (6118, 6119, 6120):
    rec = [r for r in rows if r.get('seed') == seed and r.get('state') == 'accepted'][0]
    print('seed', seed, 'result', rec.get('result_dir'))
    obs = ctl._valid_obs(rec)
    print('  _valid_obs', obs)
    if obs:
        out = ctl.state / 'exports' / ('%s-%s' % (rec.get('level'), seed))
        cmd = [ctl.python, str(cd.HERE / 'verify_export.py'), '--run-dir', str(rec['result_dir']),
               '--obs-dir', obs['obs_dir'], '--phase-map', str(cd.HERE / 'phase_map.json'),
               '--out', str(out)]
        print('  cmd', cmd)
        import subprocess
        p = subprocess.run(cmd, capture_output=True, text=True)
        print('  rc', p.returncode, 'stderr', p.stderr[-500:])
