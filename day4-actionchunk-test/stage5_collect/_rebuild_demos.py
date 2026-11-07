import json
import sys
from pathlib import Path

sys.path.insert(0, '/root/autodl-tmp/stage5-trial/collect')
import collect_demos as cd  # noqa: E402

cfg = json.loads(Path('/root/autodl-tmp/stage5-trial/collect/trial/stage5_config_formal.json').read_text())
ctl = cd.Collector(cfg)
rows = [json.loads(l) for l in ctl.attempts.read_text().splitlines() if l.strip()]
accepted = [r for r in rows if r.get('state') == 'accepted' and r.get('result_dir')]
valid = []
for r in accepted:
    v, reason = ctl._verify_export(r)
    if v:
        valid.append({'seed': r['seed'], 'level': r['level'], 'result_dir': r['result_dir'],
                      'initial': r.get('initial'), 'manifest_sha256': r.get('manifest_sha256'),
                      'obs': v, 'recorded_utc': r.get('utc')})
    else:
        print('INVALID', r['seed'])
ctl.demos.write_text('\n'.join(json.dumps(d) for d in sorted(valid, key=lambda x: x['seed'])) + '\n',
                     encoding='utf-8')
print('REBUILT demos', len(valid), [d['seed'] for d in sorted(valid, key=lambda x: x['seed'])])
for d in valid:
    print(d['seed'], d['obs']['obs_dir'], d['obs']['single_step'], d['obs']['export_dir'])
