"""H=4 chunk scheduler used by the single runner's H4 policy mode.

The runner helpers are resolved from the already-loaded __main__ module so
this module does not import/execute the runner a second time.
"""
from __future__ import annotations

import json
import sys

import numpy as np


def run_policy_h4(rt, backend, out, result, evidence, case, level, args,
                  local_points, policy, initial, obs_rows=None):
    base = sys.modules.get('a5_bc_single') or sys.modules['__main__']
    observe = base._observe
    engaged_state = base._engaged_state
    execute_action = base._execute_action
    terminal_release = base._terminal_release
    make_fold_reference = base._make_fold_reference
    slot_label = base._slot_label
    if obs_rows is None:
        obs_rows = []
    control = backend._env.control
    level_limit = int(rt.LEVEL_BUDGET[level])
    budget = int(min(level_limit, args.max_actions
                     if args.max_actions is not None else level_limit))
    result['budget'] = {
        'level_limit': level_limit,
        'requested': int(args.max_actions if args.max_actions is not None
                         else level_limit),
        'used': 0,
        'within_limit': True,
    }
    result.setdefault('policy_calls', [])
    grasp_events = 0
    release_events = 0
    nonterminal_opens = 0
    repeated_closes = 0
    initial_or_idle_opens = 0
    fold = None
    last_target = None
    last_yaw = None

    if level == 'flat':
        slot = control.fold_slot
        fold = make_fold_reference(
            rt, backend, out, result, level, case, local_points,
            initial, 'initial_settled', slot)
        result['events'].append({
            'name': 'bc_fold_reference',
            'source': 'initial_settled',
            'pick_index': fold['pick_index'],
            'yaw_rad': fold['yaw'],
            'slot_label': slot_label(slot),
            'step': int(backend._step_count['n']),
            'sim_time_s': float(backend._env.world.current_time),
        })

    def execute_one(prediction, obs_row, before):
        nonlocal grasp_events, release_events, nonterminal_opens
        nonlocal repeated_closes, initial_or_idle_opens, fold
        nonlocal last_target, last_yaw
        action_index = len(result['actions'])
        if (level != 'flat' and grasp_events == 1 and fold is None
                and not before['engaged']):
            state = np.asarray(
                backend._garment_world_positions(), dtype=np.float64)
            slot = control.slots[0]
            fold = make_fold_reference(
                rt, backend, out, result, level, case, local_points,
                state, 'post_recovery_nonengaged', slot)
            result['events'].append({
                'name': 'bc_fold_reference',
                'source': 'post_recovery_nonengaged',
                'pick_index': fold['pick_index'],
                'yaw_rad': fold['yaw'],
                'slot_label': slot_label(slot),
                'step': int(backend._step_count['n']),
                'sim_time_s': float(backend._env.world.current_time),
            })
        command = int(prediction['gripper'])
        if command == int(rt.GripperCommand.OPEN):
            required_grasps = 1 if level == 'flat' else 2
            terminal = bool(before['engaged']
                            and grasp_events >= required_grasps)
            if terminal:
                obs_row['action_label'] = 'bc_release_open'
                terminal_release(
                    rt, backend, out, result, evidence, case, level, fold,
                    last_target, last_yaw, prediction, obs_row,
                    grasp_events, release_events)
                return 'bc_release_open', True
            if before['engaged'] and level != 'flat' and grasp_events == 1:
                label = 'bc_recovery_release'
            elif grasp_events == 0:
                label = 'bc_initial_open_%03d' % action_index
            elif level != 'flat' and grasp_events == 1:
                label = 'bc_fold_approach_open_%03d' % action_index
            else:
                label = 'bc_nonterminal_open_%03d' % action_index
            row = execute_action(
                rt, backend, result, prediction['xyz'], prediction['yaw'],
                int(rt.GripperCommand.OPEN), label,
                policy=prediction, obs_row=obs_row)
            after = engaged_state(backend)
            nonterminal_opens += 1
            if before['engaged'] and not after['engaged']:
                release_events += 1
                event_name = ('bc_recovery_release'
                              if level != 'flat' and grasp_events == 1
                              else 'bc_nonterminal_release')
            elif not before['engaged'] and not after['engaged']:
                initial_or_idle_opens += 1
                event_name = ('bc_fold_approach_open'
                              if level != 'flat' and grasp_events == 1
                              else 'bc_initial_or_idle_open')
            else:
                event_name = 'bc_open_no_release'
            last_target = np.asarray(row['target_pose'][:3], dtype=float)
            last_yaw = float(row['target_pose'][3])
            result['events'].append({
                'name': event_name,
                'label': label,
                'policy_action_index': action_index,
                'grasp_events_before': int(grasp_events),
                'step': row['step'],
                'sim_time_s': float(backend._env.world.current_time),
                'target_pose': row['target_pose'],
                'target_override': False,
                'engaged_before': bool(before['engaged']),
                'engaged_after': bool(after['engaged']),
                'holding_after': row['holding'],
            })
            obs_row['action_label'] = label
            return label, False
        if command == int(rt.GripperCommand.CLOSE):
            if before['engaged']:
                label = 'bc_repeated_close_%03d' % action_index
            else:
                label = 'bc_grasp_%02d' % (grasp_events + 1)
            row = execute_action(
                rt, backend, result, prediction['xyz'], prediction['yaw'],
                int(rt.GripperCommand.CLOSE), label,
                policy=prediction, obs_row=obs_row)
            after = engaged_state(backend)
            if not before['engaged'] and after['engaged']:
                grasp_events += 1
                event_name = 'bc_grasp'
            elif before['engaged'] and after['engaged']:
                repeated_closes += 1
                event_name = 'bc_repeated_close'
            else:
                event_name = 'bc_grasp_failed'
            last_target = np.asarray(row['target_pose'][:3], dtype=float)
            last_yaw = float(row['target_pose'][3])
            result['events'].append({
                'name': event_name,
                'label': label,
                'policy_action_index': action_index,
                'grasp_events_after': int(grasp_events),
                'step': row['step'],
                'sim_time_s': float(backend._env.world.current_time),
                'target_pose': row['target_pose'],
                'target_override': False,
                'engaged_before': bool(before['engaged']),
                'engaged_after': bool(after['engaged']),
                'holding_after': row['holding'],
            })
            obs_row['action_label'] = label
            return label, False
        label = 'bc_hold_%03d' % action_index
        row = execute_action(
            rt, backend, result, prediction['xyz'], prediction['yaw'],
            command, label, policy=prediction, obs_row=obs_row)
        after = engaged_state(backend)
        event_name = None
        if not before['engaged'] and after['engaged']:
            grasp_events += 1
            event_name = 'bc_unexpected_grasp_on_hold'
        elif before['engaged'] and not after['engaged']:
            release_events += 1
            event_name = 'bc_unexpected_release_on_hold'
        last_target = np.asarray(row['target_pose'][:3], dtype=float)
        last_yaw = float(row['target_pose'][3])
        if event_name is not None:
            result['events'].append({
                'name': event_name,
                'label': label,
                'policy_action_index': action_index,
                'grasp_events_after': int(grasp_events),
                'step': row['step'],
                'sim_time_s': float(backend._env.world.current_time),
                'target_pose': row['target_pose'],
                'target_override': False,
                'engaged_before': bool(before['engaged']),
                'engaged_after': bool(after['engaged']),
                'holding_after': row['holding'],
            })
        obs_row['action_label'] = label
        return label, False

    while len(result['actions']) < budget:
        before_call = engaged_state(backend)
        observation = observe(rt, backend)
        chunk = policy.predict_chunk(observation['obs'])
        predictions = list(chunk['actions'])
        if len(predictions) != 4:
            raise RuntimeError('H4 policy did not return 4 actions')
        start_action = len(result['actions'])
        remaining_budget = budget - start_action
        limit = min(int(args.execute_k), remaining_budget, 4)
        call = {
            'call_index': len(result['policy_calls']),
            'start_action_index': start_action,
            'observation': {
                'sim_time_s': observation['sim_time_s'],
                'absolute_step': observation['absolute_step'],
                'backend_step': observation['backend_step'],
                'holding': observation['holding'],
                'engaged_before': before_call['engaged'],
            },
            'predicted_actions': [dict(p) for p in predictions],
            'inference_ms': float(chunk['inference_ms']),
            'cont_shape': chunk['cont_shape'],
            'gripper_logits_shape': chunk['gripper_logits_shape'],
            'execute_k': int(args.execute_k),
            'remaining_budget': int(remaining_budget),
            'executed_in_chunk': [],
            'discarded': [],
            'stop_reason': None,
        }
        call_obs_rows = []
        for k, prediction in enumerate(predictions):
            obs_row = dict(observation)
            obs_row['prediction'] = dict(prediction)
            obs_row['action_target'] = np.r_[prediction['xyz'], prediction['yaw']]
            obs_row['action_command'] = int(prediction['gripper'])
            obs_row['action_label'] = 'pending'
            obs_row['policy_call_index'] = call['call_index']
            obs_row['chunk_action_index'] = k
            obs_rows.append(obs_row)
            call_obs_rows.append(obs_row)
        result['policy_calls'].append(call)
        print('BC_H4_POLICY_CALL', call['call_index'],
              json.dumps({'start_action': start_action,
                          'inference_ms': call['inference_ms'],
                          'remaining_budget': remaining_budget,
                          'execute_k': int(args.execute_k)}), flush=True)
        j = 0
        terminal = False
        try:
            while j < limit:
                before = engaged_state(backend)
                label, terminal = execute_one(
                    predictions[j], call_obs_rows[j], before)
                call['executed_in_chunk'].append({
                    'chunk_index': j,
                    'action_index': start_action + j,
                    'label': label,
                    'command': int(predictions[j]['gripper']),
                    'terminal': bool(terminal),
                })
                j += 1
                if terminal:
                    call['stop_reason'] = 'terminal_release'
                    break
        except BaseException as exc:
            call['stop_reason'] = 'action_error: ' + repr(exc)
            for k in range(j, 4):
                call_obs_rows[k]['action_label'] = 'discarded_%03d' % (
                    start_action + k)
                call['discarded'].append({
                    'chunk_index': k,
                    'action': predictions[k],
                    'reason': 'action_error',
                })
            raise
        if not terminal:
            for k in range(j, 4):
                reason = ('budget' if remaining_budget < 4
                          else 'execute_k' if limit < 4 else 'stopped')
                call_obs_rows[k]['action_label'] = 'discarded_%03d' % (
                    start_action + k)
                call['discarded'].append({
                    'chunk_index': k,
                    'action': predictions[k],
                    'reason': reason,
                })
        else:
            for k in range(j, 4):
                call_obs_rows[k]['action_label'] = 'discarded_%03d' % (
                    start_action + k)
                call['discarded'].append({
                    'chunk_index': k,
                    'action': predictions[k],
                    'reason': 'terminal_stop',
                })
        if terminal:
            break

    if len(result['actions']) >= budget and 'terminal_release' not in result:
        result['events'].append({
            'name': 'bc_budget_exhausted_without_terminal_release',
            'used': len(result['actions']),
            'level_limit': level_limit,
        })
    result['budget']['used'] = len(result['actions'])
    result['budget']['within_limit'] = bool(
        len(result['actions']) <= level_limit)
    result['bc_grasps'] = grasp_events
    result['bc_release_events'] = release_events
    result['bc_recovery_releases'] = release_events
    result['bc_nonterminal_opens'] = nonterminal_opens
    result['bc_repeated_closes'] = repeated_closes
    result['bc_initial_or_idle_opens'] = initial_or_idle_opens
    result['bc_grasp_events'] = grasp_events
    return obs_rows, budget
