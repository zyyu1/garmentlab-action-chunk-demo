"""Assemble the Stage 5 demonstration dataset from per-episode exports.

State input (1340 dims): vertices (441*3) + ee_position (3) + ee_quat_wxyz (4)
+ joints (9) + holding (1). `holding` is read from the per-action observation
JSON (`action_XXX_obs.json`, field `holding`, bool) of the same episode and
call_id; it is never guessed.

Episode (seed) splits come from the export files and are preserved.
Action stats (continuous dims 0..3 only, gripper excluded) are computed from the
train split's real single-step actions only; H=4 chunks are not double counted
and padding is excluded.
"""
import argparse
import json
from pathlib import Path

import numpy as np

SINGLE_KEYS = ['obs_vertices', 'obs_ee', 'obs_quat', 'obs_joints', 'action',
               'phase', 'seed', 'level', 'split', 'success']
H4_KEYS = ['obs_vertices_start', 'obs_ee_start', 'obs_quat_start', 'obs_joints_start',
           'action', 'phase', 'mask', 'chunk_start_index', 'seed', 'level', 'split']


def load_demos(state):
    rows = [json.loads(l) for l in (Path(state) / 'demonstrations.jsonl').read_text().splitlines() if l.strip()]
    return {(r['level'], int(r['seed'])): r for r in rows}


def holding_for(obs_dir, n):
    vals = []
    for i in range(1, n + 1):
        p = obs_dir / ('action_%03d_obs.json' % i)
        if not p.is_file():
            raise SystemExit('missing observation json: %s' % p)
        d = json.loads(p.read_text())
        if int(d.get('call_id', -1)) != i:
            raise SystemExit('call_id mismatch in %s' % p)
        if 'holding' not in d:
            raise SystemExit('missing holding field in %s' % p)
        if not isinstance(d['holding'], bool):
            raise SystemExit('non-boolean holding field in %s' % p)
        vals.append(float(d['holding']))
    return np.asarray(vals, dtype=np.float32)


def load_all(exports, filename, keys, demos, obs_root):
    parts = {k: [] for k in keys}
    holdings = []
    used = []
    for d in sorted(Path(exports).iterdir()):
        p = d / filename
        if not (d.is_dir() and p.is_file()):
            continue
        level, seed = d.name.rsplit('-', 1)
        rec = demos.get((level, int(seed)))
        if rec is None:
            raise SystemExit('export without demonstration record: %s' % d.name)
        obs_dir = Path(obs_root) / Path(rec['result_dir']).name
        z = np.load(p, allow_pickle=True)
        n = len(z['seed'])
        h = holding_for(obs_dir, n)
        for k in keys:
            parts[k].append(z[k])
        holdings.append(h)
        used.append(d.name)
    if not used:
        raise SystemExit('no exports found in %s' % exports)
    out = {k: np.concatenate(v) for k, v in parts.items()}
    out['obs_holding'] = np.concatenate(holdings)
    return out, used


def obs_matrix(d):
    v = d['obs_vertices'].reshape(len(d['obs_vertices']), -1).astype(np.float32)
    return np.concatenate([v, d['obs_ee'], d['obs_quat'], d['obs_joints'],
                           d['obs_holding'][:, None]], axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exports', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--state', type=Path, default=Path('/root/autodl-tmp/stage5-formal-state-v1'))
    ap.add_argument('--obs-root', type=Path, default=Path('/root/autodl-tmp/stage5-trial/obs-formal'))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    demos = load_demos(a.state)
    single, used_s = load_all(a.exports, 'single_step.npz', SINGLE_KEYS, demos, a.obs_root)
    h4, used_h = load_all(a.exports, 'h4.npz', H4_KEYS, demos, a.obs_root)

    # H4 states must carry the holding flag of the chunk's first observation.
    base = {}
    pos = 0
    for name in used_s:
        level, seed = name.rsplit('-', 1)
        n = int(((single['level'] == level) & (single['seed'] == int(seed))).sum())
        base[(level, int(seed))] = (pos, n)
        pos += n
    chunk_hold = np.zeros(len(h4['seed']), dtype=np.float32)
    for j in range(len(h4['seed'])):
        key = (str(h4['level'][j]), int(h4['seed'][j]))
        b, n = base[key]
        start = int(h4['chunk_start_index'][j])
        if start >= n:
            raise SystemExit('chunk start out of range: %s %s' % (key, start))
        chunk_hold[j] = single['obs_holding'][b + start]
    h4['obs_holding_start'] = chunk_hold

    np.savez_compressed(a.out / 'dataset_single.npz', **single)
    np.savez_compressed(a.out / 'dataset_h4.npz', **h4)

    X = obs_matrix(single)
    y = single['action'].astype(np.float32)
    train = single['split'] == 'train'
    assert X.shape[1] == 1340, X.shape
    stats = {
        'obs_dim': int(X.shape[1]),
        'obs_mean': X[train].mean(0).tolist(),
        'obs_std': (X[train].std(0) + 1e-6).tolist(),
        'cont_mean': y[train][:, :4].mean(0).tolist(),
        'cont_std': (y[train][:, :4].std(0) + 1e-6).tolist(),
        'gripper_classes': sorted(int(v) for v in np.unique(y[:, 4])),
        'single_samples': int(len(X)),
        'h4_chunks': int(len(h4['action'])),
        'h4_mask_ones': int(h4['mask'].sum()),
        'h4_mask_total': int(h4['mask'].size),
        'episodes': len(used_s),
        'episode_names': used_s,
        'splits': {s: int((single['split'] == s).sum()) for s in ('train', 'val', 'test')},
        'levels': {l: int((single['level'] == l).sum()) for l in sorted(set(single['level']))},
    }
    (a.out / 'stats.json').write_text(json.dumps(stats, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: stats[k] for k in ('obs_dim', 'single_samples', 'h4_chunks',
                                            'h4_mask_ones', 'h4_mask_total', 'episodes',
                                            'splits', 'gripper_classes')}, indent=2))
    print('DATASET_OK', a.out)


if __name__ == '__main__':
    main()
