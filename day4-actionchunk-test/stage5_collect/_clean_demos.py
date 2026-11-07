import json
from datetime import datetime, timezone
from pathlib import Path

S = Path('/root/autodl-tmp/stage5-formal-state-v1')
OBS = Path('/root/autodl-tmp/stage5-trial/obs-formal')


def load(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


attempts = load(S / 'attempts.jsonl')
demos = load(S / 'demonstrations.jsonl')
by_seed = {r['seed']: r for r in attempts if r.get('state') == 'accepted' and r.get('result_dir')}

valid, invalid = [], []
for d in demos:
    seed = d.get('seed')
    a = by_seed.get(seed)
    if not a:
        invalid.append(d)
        continue
    obs_dir = OBS / Path(a['result_dir']).name
    rp = Path(a['result_dir']) / 'result.json'
    ok = False
    if obs_dir.is_dir() and rp.is_file():
        n = len(json.loads(rp.read_text()).get('actions') or [])
        files = list(obs_dir.glob('action_*_obs.npz'))
        ok = n > 0 and len(files) == n
    if ok:
        d['obs'] = {'obs_dir': str(obs_dir), 'obs_count': len(files), 'action_count': n}
        valid.append(d)
    else:
        invalid.append(d)

# add 6114 with its (moved) per-episode obs dir
if not any(d.get('seed') == 6114 for d in valid):
    a = by_seed.get(6114)
    if a:
        obs_dir = OBS / Path(a['result_dir']).name
        n = len(json.loads((Path(a['result_dir']) / 'result.json').read_text()).get('actions') or [])
        if obs_dir.is_dir() and len(list(obs_dir.glob('action_*_obs.npz'))) == n:
            valid.append({'seed': 6114, 'level': 'flat', 'result_dir': a['result_dir'],
                          'initial': a.get('initial'), 'manifest_sha256': a.get('manifest_sha256'),
                          'obs': {'obs_dir': str(obs_dir), 'obs_count': n, 'action_count': n},
                          'recorded_utc': datetime.now(timezone.utc).isoformat()})

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
(S / ('demonstrations.before-clean-%s.jsonl' % stamp)).write_text(
    '\n'.join(json.dumps(d) for d in demos) + '\n', encoding='utf-8')
(S / 'demonstrations.jsonl').write_text(
    '\n'.join(json.dumps(d) for d in sorted(valid, key=lambda x: x['seed'])) + '\n', encoding='utf-8')
print('CLEANED demos', len(demos), 'valid', len(valid), 'invalid', len(invalid))
print('valid seeds', [d['seed'] for d in sorted(valid, key=lambda x: x['seed'])])
