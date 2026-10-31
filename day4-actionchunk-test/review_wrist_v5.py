"""Offline v4/v5 comparison and velocity-gate candidate preparation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
old = root/'results/day4-wrist-ik-execution-20261026-072444-531501'
new = root/'results/day4-wrist-ik-execution-20261026-185833-233928'
a = json.loads((old/'result.json').read_text(encoding='utf-8'))
b = json.loads((new/'result.json').read_text(encoding='utf-8'))
assert b['probe_version'] == 'ik-tail-execution-v5-contact-report'
equal = a['targets'] == b['targets']
assert equal, 'Inspect changed trajectories before interpreting contact instrumentation'
assert (new/'contacts.jsonl').stat().st_size == 0
rows = []
fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
offset = 0
for target in b['targets']:
    trace = target.get('trace', [])
    if not trace:
        continue
    actual = np.asarray([x['actual'] for x in trace])
    command = np.asarray([x['command'] for x in trace])
    velocity = np.asarray([x['actual_velocity'] for x in trace])
    assert np.isfinite(actual).all() and np.isfinite(velocity).all()
    err = np.max(np.abs(actual-command), axis=1)
    speed = np.max(np.abs(velocity), axis=1)
    x = np.arange(offset, offset+len(trace))
    label = target['label'].rsplit('_', 1)[-1]
    axes[0].plot(x, err, label=f'Waypoint {label}')
    axes[1].plot(x, speed)
    for ax in axes:
        ax.axvline(offset, color='gray', alpha=.3)
    rows.append(dict(label=target['label'], samples=len(trace), reached=target['reached'],
                     peak_error_rad=float(err.max()), final_error_rad=float(err[-1]),
                     peak_speed_rad_s=float(speed.max()), final_speed_rad_s=float(speed[-1])))
    offset += len(trace)
axes[0].axhline(.15, color='red', linestyle='--', label='Tracking stop 0.15 rad')
axes[0].set_ylabel('Max joint error (rad)')
axes[0].legend(loc='upper left', ncol=2)
axes[1].axhline(.05, color='red', linestyle='--', label='Proposed settling gate 0.05 rad/s')
axes[1].set_yscale('log')
axes[1].set_ylim(.0005, 100)
axes[1].set_ylabel('Max absolute joint velocity (rad/s)')
axes[1].set_xlabel('Recorded IK-tail simulation step (waypoints 25–28)')
axes[1].legend()
fig.suptitle('v4 / v5: exactly matching recorded trajectories\nWaypoint 27 passes pose criteria while still moving rapidly')
fig.tight_layout()
fig.savefig(new/'wrist_v4_v5_comparison.png', dpi=170)
plt.close(fig)
audit = dict(target_records_exact_match=equal, target_count=len(b['targets']),
             contact_report_body_count=len(b['contact_report_bodies']),
             contact_events=b['contact_event_count'], callback_errors=b['contact_callback_errors'],
             rows=rows, error=b['error'],
             limitation='No known-contact positive control or runtime applied-script hash; zero events do not certify collision absence.')
(new/'v5_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
table = '\n'.join(f"|{r['label'].rsplit('_',1)[-1]}|{r['samples']}|{r['reached']}|{r['peak_error_rad']:.6f}|{r['peak_speed_rad_s']:.6f}|{r['final_speed_rad_s']:.6f}|" for r in rows)
report = f'''# v5 接触诊断核对（2026-10-26）

v5与v4全部36个目标记录（包括末段逐步位置、速度、目标和误差）完全相同。第28点跟踪发散，完整空载路径未通过；不是正式Day4成功episode。

对12个机器人刚体申请了接触报告，事件0，回调错误空，contacts.jsonl为0字节。没有已知接触正对照，不能确认整个报告通路能捕获实际接触；不能排除碰撞。结果文件也没有运行脚本哈希，不把本地manifest当成服务器运行时源码证明。

|路点|记录步数|旧到达标志|峰值误差 rad|峰值速度 rad/s|最后速度 rad/s|
|---|---:|---|---:|---:|---:|
{table}

第27点位置和姿态条件通过时速度仍约4.72 rad/s；随后进入第28点。这证明旧到达条件缺少动态收敛检查，不证明它是最初失稳原因。末段第28点峰值速度约50.68 rad/s。

下一步独立v6保留路径、前24点RMP及末段插值，末段到达增加所有7个运动学关节速度绝对值<0.05 rad/s，和原位置、姿态、关节误差条件同时连续满足6步。原240步等待预算不变；等待期增加同样0.15 rad跟踪保护及非有限值检查。阈值是诊断门限，不是折叠质量验收。

若第27点等待期不能收敛，应停止并审查控制/动力学配置，不继续推进第28点或调高阈值。v6尚未远端验证，也不意味着整个RMP前缀已增加速度验收。

![轨迹对比](wrist_v4_v5_comparison.png)
'''
(new/'pilot_review.md').write_text(report, encoding='utf-8')

source = (root/'day4-wrist-ik-execution-v5.py').read_text(encoding='utf-8')
source = source.replace('ik-tail-execution-v5-contact-report', 'ik-tail-execution-v6-velocity-gate')
source = source.replace("'all_targets_reached':False,'formal_day4_success':False,'targets':[]}",
    "'all_targets_reached':False,'formal_day4_success':False,'targets':[],\n        'settle_velocity_limit_rad_s':0.05,'settle_consecutive_steps':6,\n        'velocity_gate_scope':'IK tail only; RMP prefix unchanged',\n        'script_sha256':__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()}")
needle = '        reached=pe<.01 and re<.1 and je<.02'
replacement = '''        velocity=array(robot._robot.get_joint_velocities())[ids]
        speed=float(np.max(np.abs(velocity)))
        row['trace'][-1]['joint_speed_max_rad_s']=speed
        row['trace'][-1]['position_error_m']=pe
        row['trace'][-1]['rotation_error_rad']=re
        row['trace'][-1]['joint_error_rad']=je
        if not (np.isfinite(velocity).all() and np.isfinite(je) and np.isfinite(pe) and np.isfinite(re)) or je>.15:
            row.update(settling_step=step+1,tracking_error_rad=je,final_joint_speed_rad_s=speed)
            raise RuntimeError('Settling tracking diverged: '+label)
        reached=pe<.01 and re<.1 and je<.02 and speed<.05'''
assert source.count(needle) == 1
source = source.replace(needle, replacement)
source = source.replace('settling_steps=step+1,joint_positions=', 'settling_steps=step+1,final_joint_speed_rad_s=speed,joint_positions=')
assert "'script_sha256'" in source
compile(source, 'day4-wrist-ik-execution-v6.py', 'exec')
(root/'day4-wrist-ik-execution-v6.py').write_text(source, encoding='utf-8', newline='\n')
manifest = {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
            ['day4-wrist-ik-execution-v6.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'wrist-ik-execution-v6-files.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
runner = (root/'run-wrist-ik-execution-v5.sh').read_text(encoding='utf-8').replace('v5', 'v6')
(root/'run-wrist-ik-execution-v6.sh').write_text(runner, encoding='utf-8', newline='\n')
print(json.dumps(audit, indent=2))
print('V5_REVIEW_OK; V6_PREPARED_NOT_RUN')
