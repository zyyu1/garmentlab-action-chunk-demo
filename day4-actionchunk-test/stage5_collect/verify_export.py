"""Build and verify single-step / H=4 samples from one Stage 5 trial episode.

Rules (registered 2026-11-06):
- H=4 samples use ONLY the observation captured before the chunk's first action.
- Tail: remaining real actions are padded to 4 with mask=[1,...,0]; padding is
  excluded from the loss. Full chunks keep mask=[1,1,1,1].
- train/val/test split is fixed per seed by a stable hash, shared by both views.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

H = 4
SPLIT_SALT = 'stage5-split-v1'


def split_for(seed):
    h = int(hashlib.sha256(('%s-%d' % (SPLIT_SALT, int(seed))).encode()).hexdigest()[:8], 16) % 100
    return 'train' if h < 70 else ('val' if h < 85 else 'test')


def load_obs(obs_dir):
    rows = []
    for jf in sorted(Path(obs_dir).glob('action_*_obs.json')):
        meta = json.loads(jf.read_text(encoding='utf-8'))
        z = np.load(jf.with_suffix('.npz'))
        rows.append({'call_id': meta['call_id'], 'meta': meta,
                     'vertices': z['vertices'], 'ee': z['ee'],
                     'quat': z['quat'] if 'quat' in z else np.zeros(4),
                     'joints': z['joints']})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--obs-dir', required=True)
    ap.add_argument('--phase-map', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    run = Path(a.run_dir)
    result = json.loads((run / 'result.json').read_text(encoding='utf-8'))
    meta = json.loads((run / 'success_meta.json').read_text(encoding='utf-8'))
    verdict = (json.loads((run / 'a5-verdict.json').read_text(encoding='utf-8'))
               if (run / 'a5-verdict.json').is_file() else {})
    accepted = verdict.get('status') == 'accepted'
    phase_map = json.loads(Path(a.phase_map).read_text(encoding='utf-8'))
    actions = result['actions']
    labels = [act.get('label') for act in actions]
    obs = load_obs(a.obs_dir)
    seed, level = meta['seed'], meta['level']
    split = split_for(seed)

    checks = {
        'obs_count': len(obs), 'action_count': len(actions),
        'count_match': len(obs) == len(actions),
        'call_ids_1_to_n': [o['call_id'] for o in obs] == list(range(1, len(obs) + 1)),
        'vertices_shape_ok': all(o['vertices'].shape == (441, 3) for o in obs),
        'ee_shape_ok': all(o['ee'].shape == (3,) for o in obs),
        'quat_shape_ok': all(o['quat'].shape == (4,) for o in obs),
        'quat_unit_norm': all(abs(np.linalg.norm(o['quat']) - 1.0) < 1e-6 for o in obs),
        'joints_len': sorted({len(o['joints']) for o in obs}),
        'steps_monotonic': all(obs[i]['meta']['backend_step'] <= obs[i + 1]['meta']['backend_step']
                               for i in range(len(obs) - 1)),
        'time_monotonic': all(obs[i]['meta']['sim_time_s'] <= obs[i + 1]['meta']['sim_time_s']
                              for i in range(len(obs) - 1)),
        'unknown_phase_labels': [l for l in labels if l not in phase_map],
    }
    max_dp, max_dc = 0.0, 0
    for o, act in zip(obs, actions):
        max_dp = max(max_dp, max(abs(float(p) - float(q)) for p, q in
                                 zip(o['meta']['targets'][0], act['target_pose'])))
        max_dc = max(max_dc, abs(int(o['meta']['commands'][0]) - int(act['command'])))
    checks['target_max_abs_diff'] = max_dp
    checks['command_max_abs_diff'] = max_dc
    checks['pairing_ok'] = max_dp <= 1e-6 and max_dc == 0

    action_vec = np.asarray([[*(act['target_pose'][:4]), int(act['command'])] for act in actions],
                            dtype=np.float64)
    phase = np.asarray([phase_map.get(l, 'UNKNOWN') for l in labels])
    single = {
        'obs_vertices': np.stack([o['vertices'] for o in obs]),
        'obs_ee': np.stack([o['ee'] for o in obs]),
        'obs_quat': np.stack([o['quat'] for o in obs]),
        'obs_joints': np.stack([o['joints'] for o in obs]),
        'action': action_vec, 'phase': phase,
        'seed': np.asarray([seed] * len(obs)),
        'level': np.asarray([level] * len(obs)),
        'split': np.asarray([split] * len(obs)),
        'success': np.asarray([bool(accepted)] * len(obs)),
    }

    n = len(obs)
    starts = list(range(0, n - H + 1, H))
    tail = n % H if starts else (n % H if n else 0)
    chunks = []
    for s in starts:
        chunks.append({'start': s, 'vertices': obs[s]['vertices'], 'ee': obs[s]['ee'],
                       'quat': obs[s]['quat'], 'joints': obs[s]['joints'],
                       'action': action_vec[s:s + H], 'phase': phase[s:s + H],
                       'mask': np.ones(H, dtype=np.int8)})
    audit = []
    for s in starts:
        audit.append(np.stack([o['vertices'] for o in obs[s:s + H]]))
    if tail:
        s = starts[-1] + H if starts else 0
        chunks.append({'start': s, 'vertices': obs[s]['vertices'], 'ee': obs[s]['ee'],
                       'quat': obs[s]['quat'], 'joints': obs[s]['joints'],
                       'action': np.concatenate([action_vec[s:s + tail], np.zeros((H - tail, 5))]),
                       'phase': np.concatenate([phase[s:s + tail], np.asarray(['PAD'] * (H - tail))]),
                       'mask': np.asarray([1] * tail + [0] * (H - tail), dtype=np.int8)})

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'single_step.npz', **single)
    np.savez_compressed(
        out / 'h4.npz',
        obs_vertices_start=np.stack([c['vertices'] for c in chunks]),
        obs_ee_start=np.stack([c['ee'] for c in chunks]),
        obs_quat_start=np.stack([c['quat'] for c in chunks]),
        obs_joints_start=np.stack([c['joints'] for c in chunks]),
        action=np.stack([c['action'] for c in chunks]),
        phase=np.stack([c['phase'] for c in chunks]),
        mask=np.stack([c['mask'] for c in chunks]),
        chunk_start_index=np.asarray([c['start'] for c in chunks], dtype=np.int64),
        seed=np.asarray([seed] * len(chunks)), level=np.asarray([level] * len(chunks)),
        split=np.asarray([split] * len(chunks)))
    if audit:
        np.savez_compressed(out / 'h4_audit.npz', obs_vertices_all=np.stack(audit))

    summary = {
        'seed': seed, 'level': level, 'task': meta.get('task'), 'split': split,
        'verdict_status': verdict.get('status'), 'result_passed': result.get('passed'),
        'action_labels': labels,
        'checks': checks,
        'single_step': {'count': int(n),
                        'obs_vertices': list(single['obs_vertices'].shape),
                        'obs_ee': list(single['obs_ee'].shape),
                        'obs_quat': list(single['obs_quat'].shape),
                        'obs_joints': list(single['obs_joints'].shape),
                        'action': list(single['action'].shape)},
        'h4': {'chunk_size': H,
               'full_chunks': int(len(starts)),
               'tail_actions': int(tail),
               'total_chunks': int(len(chunks)),
               'input_policy': 'observation at chunk start only',
               'mask_rule': 'full=[1,1,1,1]; tail=[1,...,0]; padding excluded from loss',
               'shape': [int(len(chunks)), H, 5],
               'no_cross_episode': True},
        'phase_counts': {str(k): int(v) for k, v in zip(*np.unique(phase, return_counts=True))},
    }
    (out / 'export_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
