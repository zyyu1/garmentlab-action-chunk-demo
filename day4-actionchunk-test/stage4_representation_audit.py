"""Stage 4 step 3: audit paired single-step vs H=4 fold episodes.

Each pair must be the same task, the same initial state and the same test seed,
differing only in the waypoint representation.  The audit checks three things:

1. Targets.  For every episode it recomputes the four arc targets from that
   episode's own recorded inputs (measured grasp pick, fold yaw, width,
   overhang) with ``l1_yaw_fold_geometry.local_arc`` and requires the public
   targets to match exactly.  So both runs obey one target rule.  The residual
   target difference between a pair is reported next to the residual
   measured-pick difference; it is a closed-loop measurement difference, not a
   definition difference.
2. Evaluator.  Both episodes are scored by ``stage4_fold_metrics``, whose own
   file hashes are verified against ``stage4-evaluator-files.json``.
3. Seeds.  Seed, level, initial directory, fold edge and frozen constants must
   be identical within a pair.

Offline tool: no simulation, no model.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import l1_yaw_fold_geometry as geo  # noqa: E402
import stage4_fold_metrics as ev  # noqa: E402
from square_pose_contract import grasp_to_ee  # noqa: E402

WIDTH = 0.2
ARC_LABELS = {'l1': ('arc45', 'arc90', 'arc135', 'place'),
              'l2l3': ('fold_arc45', 'fold_arc90', 'fold_arc135', 'fold_place')}
EXPECTED_HORIZONS = {'l1': {'single': [1] * 7,
                            'arc4': [1, 1, 4, 1]},
                     'l2l3': {'single': [1] * 12,
                              'arc4': [1] * 7 + [4, 1]}}
HORIZON_TOLERANCE_M = 1e-9


def load(result_dir):
    with open(os.path.join(result_dir, 'result.json'), encoding='utf-8') as handle:
        return json.load(handle)


def task_of(result):
    return 'l1' if 'fold_definition' in result else 'l2l3'


def arc_rows(result, task):
    by_label = {action['label']: action for action in result['actions']}
    missing = [label for label in ARC_LABELS[task] if label not in by_label]
    if missing:
        raise ValueError('missing arc rows: ' + ', '.join(missing))
    return [by_label[label] for label in ARC_LABELS[task]]


def fold_inputs(result, task):
    """Pick, yaw, width, overhang and lateral sign actually used by the run."""
    if task == 'l1':
        definition = result['fold_definition']
        pick = np.asarray(result['grasp_pick_world'], dtype=float)
        yaw = float(result['fold_yaw'])
        width = float(definition['fold_width_m'])
        overhang = float(definition['fold_overhang_m'])
        lateral = np.array([1. if definition.get('fold_edge', 'left') == 'left' else -1., 0., 0.])
    else:
        record = next(x for x in result['records'] if x['label'] == 'fold_targets')
        pick = np.asarray(record['pick_world'], dtype=float)
        yaw = float(record['fold_yaw'])
        width = float(record['width_m'])
        overhang = 0.
        lateral = np.array([1. if result['fold_edge'] == 'left' else -1., 0., 0.])
    return {'pick': pick, 'yaw': yaw, 'width': width, 'overhang': overhang,
            'lateral_local': lateral}


def target_rule_check(result, task):
    """Recompute the four arc targets from the run's own inputs and compare."""
    inputs = fold_inputs(result, task)
    material = geo.local_arc(inputs['pick'], inputs['yaw'], inputs['lateral_local'],
                             inputs['width'], overhang=inputs['overhang'])
    expected = np.asarray([grasp_to_ee(point, inputs['yaw']) for point in material])
    rows = arc_rows(result, task)
    recorded = np.asarray([row['target_pose'] for row in rows], dtype=float)
    position_error = np.abs(recorded[:, :3] - expected).max(axis=0)
    yaw_error = np.abs(recorded[:, 3] - inputs['yaw']).max()
    commands = [int(row['command']) for row in rows]
    return {'targets_reproduced': bool(position_error.max() <= HORIZON_TOLERANCE_M and
                                       yaw_error <= HORIZON_TOLERANCE_M),
            'position_error_m': position_error.tolist(),
            'max_position_error_m': float(position_error.max()),
            'yaw_error_rad': float(yaw_error),
            'commands': commands,
            'inputs': {'pick_world': inputs['pick'].tolist(), 'yaw_rad': inputs['yaw'],
                       'width_m': inputs['width'], 'overhang_m': inputs['overhang'],
                       'lateral_local': inputs['lateral_local'].tolist()}}


def representation_check(result, task, mode):
    horizons = result.get('call_horizons')
    chunks = result.get('chunks', [])
    executed = int(result.get('action_count', len(result['actions'])))
    expected = EXPECTED_HORIZONS[task][mode]
    structure = {
        'execution_mode': result.get('execution_mode'),
        'call_horizons': horizons,
        'chunk_count': len(chunks),
        'chunk_labels': [chunk['label'] for chunk in chunks],
        'chunk_horizons': [chunk['horizon'] for chunk in chunks],
        'action_count': executed,
    }
    ok = (structure['execution_mode'] == mode and horizons == expected and
          sum(horizons or []) == executed and
          len(chunks) == (0 if mode == 'single' else 1))
    if chunks:
        ok = ok and chunks[0]['labels'] == list(ARC_LABELS[task]) and chunks[0]['horizon'] == 4
        rows = [row for row in result['actions']
                if row.get('chunk_label') == chunks[0]['label']]
        ok = ok and [row['target_pose'] for row in rows] == chunks[0]['targets']
    return {'structure': structure, 'matches_expected': bool(ok)}


def seed_identity(result, task):
    case = result.get('initial_case', {})
    edge = (result.get('fold_edge') if task == 'l2l3'
            else result.get('fold_definition', {}).get('fold_edge', 'left'))
    return {'seed': case.get('seed'), 'level': case.get('level'),
            'yaw_rad': case.get('yaw_rad'), 'initial_dir': result.get('initial_dir'),
            'fold_edge': edge}


def constants(result, task):
    inputs = fold_inputs(result, task)
    return {'width_m': inputs['width'], 'overhang_m': inputs['overhang'],
            'lateral_local': inputs['lateral_local'].tolist()}


def audit_pair(single_dir, arc4_dir):
    single, arc4 = load(single_dir), load(arc4_dir)
    task = task_of(single)
    if task_of(arc4) != task:
        raise ValueError(f'pair mixes tasks: {single_dir} vs {arc4_dir}')
    rule = {'single': target_rule_check(single, task),
            'arc4': target_rule_check(arc4, task)}
    shape = {'single': representation_check(single, task, 'single'),
             'arc4': representation_check(arc4, task, 'arc4')}
    seeds = {'single': seed_identity(single, task), 'arc4': seed_identity(arc4, task)}
    frozen = {'single': constants(single, task), 'arc4': constants(arc4, task)}
    same_seed = seeds['single'] == seeds['arc4']
    same_constants = frozen['single'] == frozen['arc4']
    same_constants = same_constants and abs(frozen['single']['width_m'] - WIDTH) <= 1e-12
    same_code = bool(single.get('code_files')) and single.get('code_files') == arc4.get('code_files')
    single_inputs = rule['single']['inputs']
    arc4_inputs = rule['arc4']['inputs']
    pick_delta = float(np.linalg.norm(np.asarray(single_inputs['pick_world']) -
                                      np.asarray(arc4_inputs['pick_world'])))
    single_targets = np.asarray([row['target_pose'][:3] for row in arc_rows(single, task)])
    arc4_targets = np.asarray([row['target_pose'][:3] for row in arc_rows(arc4, task)])
    target_delta = float(np.abs(single_targets - arc4_targets).max())
    yaw_delta = float(abs(single_inputs['yaw_rad'] - arc4_inputs['yaw_rad']))
    metrics = {'single': ev.evaluate(single_dir, task, write=False),
               'arc4': ev.evaluate(arc4_dir, task, write=False)}
    delta = {}
    for key in ('moving_half_crossed_fraction', 'particle_occupancy_iou',
                'symmetric_xy_alignment_mean_m', 'moving_material_reflected_target_mean_error_m',
                'cloth_z_p95_m'):
        delta[key] = float(metrics['arc4']['metrics'][key] - metrics['single']['metrics'][key])
    comparable = (all(rule[mode]['targets_reproduced'] for mode in rule) and
                  all(shape[mode]['matches_expected'] for mode in shape) and
                  same_seed and same_constants and same_code and
                  metrics['single']['evaluator_files'] == metrics['arc4']['evaluator_files'])
    return {'task': task, 'single_dir': os.path.abspath(single_dir),
            'arc4_dir': os.path.abspath(arc4_dir),
            'seed': seeds['single']['seed'], 'level': seeds['single']['level'],
            'fold_edge': seeds['single']['fold_edge'],
            'target_rule': rule, 'representation': shape,
            'seed_identity': seeds, 'same_seed_state': bool(same_seed),
            'frozen_constants': frozen, 'same_frozen_constants': bool(same_constants),
            'code_files': single.get('code_files'), 'same_code_identity': bool(same_code),
            'measured_pick_delta_m': pick_delta,
            'measured_fold_yaw_delta_rad': yaw_delta,
            'paired_target_delta_m': target_delta,
            'execution_mode': {'single': single.get('execution_mode'),
                               'arc4': arc4.get('execution_mode')},
            'passed': {'single': bool(metrics['single']['passed']),
                       'arc4': bool(metrics['arc4']['passed'])},
            'metrics': {mode: metrics[mode]['metrics'] for mode in metrics},
            'metric_delta_arc4_minus_single': delta,
            'evaluator_files': metrics['single']['evaluator_files'],
            'comparable': bool(comparable),
            'scope': 'Paired representation audit; not a formal Stage 4 success.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pair', nargs=2, action='append', required=True,
                        metavar=('SINGLE_DIR', 'ARC4_DIR'),
                        help='one single-step dir and the matching H=4 dir; repeat')
    parser.add_argument('--out', default=os.path.join(HERE, 'representation_audit.json'))
    args = parser.parse_args()
    pairs = [audit_pair(single, arc4) for single, arc4 in args.pair]
    print(f"{'seed':>5} {'task':>5} {'edge':>5} {'dpick_mm':>8} {'dtgt_mm':>7} "
          f"{'dcross':>7} {'dIoU':>7} {'dalign_mm':>9} {'drefl_mm':>8} "
          f"{'pass s/a':>9} {'comparable':>10}")
    for pair in pairs:
        delta = pair['metric_delta_arc4_minus_single']
        passed = '/'.join('Y' if pair['passed'][mode] else 'N' for mode in ('single', 'arc4'))
        print(f"{str(pair['seed']):>5} {pair['task']:>5} {str(pair['fold_edge']):>5} "
              f"{1000 * pair['measured_pick_delta_m']:8.2f} "
              f"{1000 * pair['paired_target_delta_m']:7.2f} "
              f"{delta['moving_half_crossed_fraction']:7.3f} "
              f"{delta['particle_occupancy_iou']:7.3f} "
              f"{1000 * delta['symmetric_xy_alignment_mean_m']:9.2f} "
              f"{1000 * delta['moving_material_reflected_target_mean_error_m']:8.2f} "
              f"{passed:>9} {str(pair['comparable']):>10}")
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'pairs': pairs, 'comparable_all': all(p['comparable'] for p in pairs),
                   'scope': 'Paired representation audit; not a formal Stage 4 success.'},
                  handle, ensure_ascii=False, indent=1)
    print('WROTE', args.out)
    if not all(pair['comparable'] for pair in pairs):
        print('PAIR_NOT_COMPARABLE', flush=True)
        return 1
    print('PAIRS_COMPARABLE', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
