"""Reject failed finite-gain candidate and document the return to the Day4 interface."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
out=root/'results/day4-wrist-ik-execution-20261026-231825-412721'
r=json.loads((out/'result.json').read_text());e=json.loads((out/'effective_inertia.json').read_text());c=json.loads((out/'runtime_config.json').read_text())
assert r['script_sha256']==hashlib.sha256((root/'day4-wrist-ik-execution-v11.py').read_bytes()).hexdigest()
assert e['verified'] and len(r['arm_gain_overrides'])==7 and len(r['inertia_overrides'])==11
assert len(r['targets'])==1 and r['targets'][0]['label']=='approach' and not r['targets'][0]['reached']
assert np.allclose(e['gains'],e['expected_gains'],rtol=1e-5)
states=[json.loads(x) for x in (out/'step_states.jsonl').read_text().splitlines()]
assert len(states)==240 and all(x['phase']=='approach' for x in states)
assert all(states[i]['after']==states[i+1]['before'] for i in range(len(states)-1))
dt=c['runtime_getters']['world']['get_physics_dt']['value']
assert np.allclose([x['after']['current_time']-x['before']['current_time'] for x in states],dt,rtol=1e-6)
q=np.asarray([x['after']['position'] for x in states])[:,:7]
v=np.asarray([x['after']['velocity'] for x in states])[:,:7]
limits={x['path'].rsplit('/',1)[-1]:np.deg2rad([x['lower'],x['upper']]) for x in r['usd_joint_limits_degrees']}
bounds=np.asarray([limits['panda_joint'+str(j)] for j in range(1,8)])
margin=np.minimum(q-bounds[:,0],bounds[:,1]-q)
stats=[]
for j in range(7):
    near=np.flatnonzero(margin[:,j]<np.deg2rad(1))
    stats.append({'joint':'panda_joint'+str(j+1),'peak_abs_velocity_rad_s':float(abs(v[:,j]).max()),
                  'minimum_limit_margin_deg':float(np.rad2deg(margin[:,j].min())),
                  'first_within_1_degree_of_limit_step':None if not len(near) else int(near[0]+1)})
audit={'script_hash_matches':True,'effective_gain_profile_verified':True,'only_approach_executed':True,
       'sample_count':240,'actual_dt':dt,'final_position_error_m':r['targets'][0]['position_error_m'],
       'candidate_rejected':True,'joint_stats':stats,
       'cause_not_proven':'No per-step RMP targets, efforts or EE poses in this record; gain insufficiency versus other control dynamics not separated.'}
(out/'v11_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True)
time=np.arange(1,241)*dt
for j in range(7):
    ax[0].plot(time,(q[:,j]-bounds[j,0])/(bounds[j,1]-bounds[j,0]),label='joint'+str(j+1))
    ax[1].plot(time,v[:,j])
ax[0].axhline(0,color='black',ls=':');ax[0].axhline(1,color='black',ls=':');ax[0].set_ylabel('Joint position in limit range [0, 1]');ax[0].legend(ncol=4)
ax[1].set_ylabel('Reported joint velocity (rad/s)');ax[1].set_xlabel('Approach time (s)')
for a in ax:a.grid(alpha=.3)
fig.suptitle('v11 rejected: approach fails before wrist trajectory begins')
fig.tight_layout();fig.savefig(out/'v11_approach_failure.png',dpi=170);plt.close(fig)
table='\n'.join(f"|{x['joint']}|{x['peak_abs_velocity_rad_s']:.4f}|{x['minimum_limit_margin_deg']:.5f}|{x['first_within_1_degree_of_limit_step']}|" for x in stats)
(out/'pilot_review.md').write_text(f'''# v11 增益候选审查（2026-10-26）

候选拒绝：首次approach等待240步后位置误差{r['targets'][0]['position_error_m']*1000:.3f} mm，没有进入下探或任何翻腕路点。不能用于判断第27点改善。

脚本哈希匹配，7个臂关节缩放配置与有效增益读回一致；继承v10几何惯量并通过既有质量/惯量检查。实际dt=1/60秒，240条状态连续。不是上传错误或跳过配置验证。

|关节|峰值报告速度 rad/s|最小限位余量 °|首次距限位<1°的step|
|---|---:|---:|---:|
{table}

多个关节接近模型边界，位置持续偏离。微小负限位余量应按数值精度解释，不据此单独宣称越限损坏。没有逐步RMP控制目标、力矩或末端姿态记录，不能从结果唯一归因于增益太低、重力补偿或某项SDK错误。此次只说明这个固定增益profile在现有执行器/控制组合下不满足基本approach任务。

不增加等待预算、不放宽门限、不按结果继续扫描增益。所有候选修改仅在实验进程内，未整合到正式Backend。原高增益配置也未通过翻腕路径，不能称为已验证完整机器人修复。

下一步转回Day4既定公共接口与官方多抓取流程，详细评估见项目根目录DAY4_ROUTE_REASSESSMENT.md。v5–v11均是诊断，不能计入正式成功episode。

![approach失败轨迹](v11_approach_failure.png)
''',encoding='utf-8')
print('V11_AUDIT_OK; CANDIDATE_REJECTED; NO_NEW_SIMULATION_PREPARED')
