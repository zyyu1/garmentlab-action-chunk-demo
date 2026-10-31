"""Audit initialization-time velocity iteration control against v7b/v8."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
out=root/'results/day4-wrist-ik-execution-20261026-222519-595953'
baseline=root/'results/day4-wrist-ik-execution-20261026-193733-229449'
r=json.loads((out/'result.json').read_text());a=json.loads((baseline/'result.json').read_text())
c=json.loads((out/'runtime_config.json').read_text());ca=json.loads((baseline/'runtime_config.json').read_text())
pre=json.loads((out/'pre_reset_solver_config.json').read_text())
assert r['script_sha256']==hashlib.sha256((root/'day4-wrist-ik-execution-v9.py').read_bytes()).hexdigest()
assert pre['timeline_stopped_before'] and pre['time_step_before']==0 and pre['time_before']==0
assert pre['velocity_iterations_before']==64 and pre['velocity_iterations_after_reset']==0
assert pre['position_iterations_after_reset']==64
for name,v in c['source_hashes'].items():
    assert v['sha256']==ca['source_hashes'][name]['sha256']
    assert v['sha256']==hashlib.sha256((out/(name+'_runtime.py')).read_bytes()).hexdigest()
assert c['runtime_getters']['controller']['get_gains']==ca['runtime_getters']['controller']['get_gains']
assert c['runtime_getters']['world']==ca['runtime_getters']['world']
assert len(r['targets'])==len(a['targets'])
for ta,tb in zip(a['targets'],r['targets']):
    assert ta['label']==tb['label']
    if not ta['label'].startswith('descend_'):
        assert ta['target_position']==tb['target_position']
    assert ta.get('target_quaternion_wxyz')==tb.get('target_quaternion_wxyz')
states=[json.loads(s) for s in (out/'step_states.jsonl').read_text().splitlines()]
assert len(states)==sum(t.get('steps',len(t.get('trace',[]))) for t in r['targets'])
assert all(states[i]['after']==states[i+1]['before'] for i in range(len(states)-1))
dt=c['runtime_getters']['world']['get_physics_dt']['value']
assert np.allclose([x['after']['current_time']-x['before']['current_time'] for x in states],dt,rtol=1e-6)
t=r['targets'][-1];s=[x for x in t['trace'] if x['phase']=='settling']
assert len(s)==240 and not t['reached']
q=np.asarray([x['actual'] for x in s]);v=np.asarray([x['actual_velocity'] for x in s])
command=np.asarray([x['command'] for x in s]);assert np.all(command==command[0])
bounds={x['path'].rsplit('/',1)[-1]:np.deg2rad([x['lower'],x['upper']]) for x in r['usd_joint_limits_degrees']}
margins={name:float(min(q[:,j].min()-bounds[name][0],bounds[name][1]-q[:,j].max())) for j,name in enumerate(t['joint_names'])}
rows=[]
for j,name in enumerate(t['joint_names']):
    rows.append({'joint':name,'last60_position_range_rad':float(np.ptp(q[-60:,j])),
       'last60_reported_velocity_min_rad_s':float(v[-60:,j].min()),
       'last60_reported_velocity_max_rad_s':float(v[-60:,j].max()),
       'last60_difference_speed_max_rad_s':float(abs(np.diff(q[-60:,j])/dt).max()),
       'minimum_limit_margin_during_settle_rad':margins[name]})
old_speed=a['targets'][-1]['final_joint_speed_rad_s'];new_speed=t['final_joint_speed_rad_s']
descent_diff=max(float(np.linalg.norm(np.asarray(x['target_position'])-y['target_position'])) for x,y in zip(a['targets'],r['targets']) if x['label'].startswith('descend_'))
audit={'script_hash_matches':True,'source_hashes_match_baseline':True,'arc_and_approach_targets_exact':True,
       'adaptive_descent_max_target_difference_m':descent_diff,
       'initial_config_verified':pre,'state_samples':len(states),'state_continuity_verified':True,
       'physics_dt_s':dt,'gain_and_dt_match_baseline':True,'baseline_final_speed_rad_s':old_speed,
       'v9_final_speed_rad_s':new_speed,'final_speed_reduction_percent':100*(1-new_speed/old_speed),
       'all_targets_reached':r['all_targets_reached'],'joints':rows}
(out/'v9_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
fig,axs=plt.subplots(3,1,figsize=(11,9),sharex=True)
for record,label in [(a,'v7b: 64 velocity iterations'),(r,'v9: 0 configured before first reset')]:
    trace=[x for x in record['targets'][-1]['trace'] if x['phase']=='settling']
    speed=np.max(abs(np.asarray([x['actual_velocity'] for x in trace])),axis=1)
    axs[0].plot(np.arange(1,len(trace)+1)*dt,speed,label=label)
axs[0].axhline(.05,color='red',ls=':',label='0.05 rad/s gate');axs[0].set_ylabel('Max reported speed (rad/s)')
time=np.arange(1,241)*dt
for j in [4,5,6]:
    axs[1].plot(time,v[:,j],label=t['joint_names'][j])
    axs[2].plot(time,q[:,j]-q[0,j],label=t['joint_names'][j])
axs[1].set_ylabel('v9 reported velocity (rad/s)');axs[2].set_ylabel('v9 position change (rad)');axs[2].set_xlabel('Waypoint 27 settling time (s)')
for ax in axs:ax.legend();ax.grid(alpha=.3)
fig.suptitle('Pre-reset solver configuration changes the outcome, but velocity convergence still fails')
fig.tight_layout();fig.savefig(out/'v9_pre_reset_comparison.png',dpi=170);plt.close(fig)
table='\n'.join(f"|{x['joint']}|{x['last60_position_range_rad']:.9g}|{x['last60_reported_velocity_min_rad_s']:.6f} … {x['last60_reported_velocity_max_rad_s']:.6f}|{np.rad2deg(x['minimum_limit_margin_during_settle_rad']):.2f}|" for x in rows)
(out/'pilot_review.md').write_text(f'''# v9 初始化前TGS配置对照（2026-10-26）

v9仍未通过第27点速度收敛检查；没有新增Day4正式成功episode。

## 核对通过的证据

- 运行脚本哈希匹配；导出的Backend、FoldEnv、机器人包装器源码哈希与v7b一致。
- timeline停止、时间0、step0时，速度迭代64→0，位置迭代保持64；首次reset后配置仍为64/0。
- 实际dt=1/60秒、1086步pre/post状态连续。目标标签、approach/30点圆弧目标定义及对应已执行目标、姿态与基线相同；下探起点取实测末端，因此下探目标最大差{descent_diff*1000:.6f} mm。从初始化改变物理配置后，不要求实际状态前缀精确相同，不能声称所有实际控制目标完全相同。
- 增益、dt与基线一致。25、26点通过，27点固定目标等待240步失败，位置误差{t['position_error_m']*1000:.6f} mm，姿态误差{t['rotation_error_rad']:.6f} rad，关节误差{t['joint_error_rad']:.6f} rad。

## 效果与边界

第27点末最大报告速度从{old_speed:.9f}降至{new_speed:.9f} rad/s，下降{audit['final_speed_reduction_percent']:.2f}%。joint5旧约4.7 rad/s大幅下降，但joint6残留约1.2745 rad/s。第27点插值末段仍出现异常，保持阶段速度未继续衰减。该设置产生了行为变化，仍不足以修复；getter是USD读回，不能把它称为直接查询引擎内部迭代计数。

最后60帧：

|关节|位置范围 rad|报告速度范围 rad/s|整个保持阶段最小限位余量 °|
|---|---:|---:|---:|
{table}

没有接近已导出硬限位的证据；这不排除动力学、软约束或模型问题。joint6最后60帧位置范围仅约7.75e-7 rad，而报告速度约1.2745 rad/s，离散位置差分与速度差异仍存在，不能因此放宽速度门限。

## 下一步

停止继续扫描迭代数。优先审查七个臂关节极高驱动增益及机器人惯量的资产来源、长度/质量单位和实际有效值，再选择一个有依据的修正。当前有效kp=572957824、kd=5729578；一些link的USD authored inertia约1e-6，但尚未导出有效惯量或资产layer出处，不能仅凭量级认定资产错误。USD angular与有效gains的换算不是错误证据。

v8运行中修改无轨迹变化，而v9初始化前修改有变化，支持后续配置应在首次reset前完成；并不证明所有类似参数都只在reset时生效。下一次诊断先补资产来源/有效惯量证据，不再重复v7–v9原路径。完成后回到符合公共接口的L1折叠，空载探针仍不属于正式示范。

![对照](v9_pre_reset_comparison.png)
''',encoding='utf-8')
print(json.dumps({'audit_ok':True,'final_speed_reduction_percent':audit['final_speed_reduction_percent'],'limit_margins_deg':{k:float(np.rad2deg(x)) for k,x in margins.items()}},indent=2))
