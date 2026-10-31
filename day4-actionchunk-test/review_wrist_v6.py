"""Offline audit: reported joint velocity versus sampled joint displacement."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
out=root/'results/day4-wrist-ik-execution-20261026-192104-045218'
r=json.loads((out/'result.json').read_text(encoding='utf-8'))
assert r['script_sha256']==hashlib.sha256((root/'day4-wrist-ik-execution-v6.py').read_bytes()).hexdigest()
t=r['targets'][-1]
assert t['label']=='opposite_delayed_pitch_27' and not t['reached']
s=[x for x in t['trace'] if x['phase']=='settling']
assert len(s)==240
q=np.asarray([x['actual'] for x in s]);v=np.asarray([x['actual_velocity'] for x in s])
c=np.asarray([x['command'] for x in s])
assert np.isfinite(q).all() and np.isfinite(v).all() and np.all(c==c[0])
old=json.loads((root/'results/day4-wrist-ik-execution-20261026-185833-233928/result.json').read_text())
prefix=[]
for a,b in zip(old['targets'],r['targets']):
    if 'trace' not in a:
        prefix.append(a==b)
    else:
        common=[{k:x[k] for k in y}==y for x,y in zip(b['trace'],a['trace'])]
        prefix.append(all(common))
assert all(prefix)
stats=[]
for j,n in enumerate(t['joint_names']):
    stats.append(dict(joint=n,last60_position_range_rad=float(np.ptp(q[-60:,j])),
        last60_reported_speed_min_rad_s=float(v[-60:,j].min()),
        last60_reported_speed_max_rad_s=float(v[-60:,j].max()),
        last60_max_position_difference_rad=float(abs(np.diff(q[-60:,j])).max()),
        nominal_60Hz_max_difference_speed_rad_s=float(abs(np.diff(q[-60:,j])*60).max())))
audit=dict(script_hash_matches=True,recorded_common_prefix_equal=True,settling_samples=len(s),
    constant_settling_command=True,physics_dt_verified=False,
    note='60 Hz finite differences are nominal only; v6 did not export runtime physics dt. Sample differences cannot resolve intra-step solver motion.',joints=stats)
(out/'v6_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
fig,ax=plt.subplots(3,1,figsize=(11,9),sharex=True)
idx=np.arange(181,241)
for j in (4,6):
    ax[0].plot(idx,q[-60:,j]-q[-60,j],label=t['joint_names'][j])
    ax[1].plot(idx,v[-60:,j],label=t['joint_names'][j])
    ax[2].plot(idx[1:],np.diff(q[-60:,j])*60,label=t['joint_names'][j])
ax[0].set_ylabel('Position change from frame 181 (rad)')
ax[1].set_ylabel('Reported velocity (rad/s)')
ax[2].set_ylabel('Position difference × 60 (rad/s)')
ax[2].set_xlabel('Waypoint 27 settling frame (last 60 of 240)')
for a in ax:a.legend(loc='upper right');a.grid(alpha=.25)
fig.suptitle('v6: nearly fixed sampled positions with persistently nonzero reported velocities\nBottom panel assumes nominal 60 Hz; runtime dt was not recorded')
fig.tight_layout();fig.savefig(out/'position_velocity_consistency.png',dpi=170);plt.close(fig)
table='\n'.join(f"|{x['joint']}|{x['last60_position_range_rad']:.9f}|{x['last60_reported_speed_min_rad_s']:.6f} … {x['last60_reported_speed_max_rad_s']:.6f}|{x['nominal_60Hz_max_difference_speed_rad_s']:.9f}|" for x in stats)
report=f'''# v6 速度收敛与位置一致性核对（2026-10-26）

运行脚本SHA256与本地v6一致；与v5可比较的公共前缀字段及逐步轨迹全部一致。25、26点通过速度门限；27点固定目标等待240步后仍未满足速度条件，正确停止，未进入28点。最终位置误差1.946747 mm、姿态误差0.014356 rad、关节误差0.010232 rad，最大报告关节速度4.717120 rad/s。没有新增正式Day4成功episode。

最后60帧：

|关节|位置范围 rad|报告速度范围 rad/s|名义60Hz逐帧差分最大速度 rad/s|
|---|---:|---:|---:|
{table}

等待期间命令完全固定。joint5和joint7报告速度持续较大，但采样位置几乎固定，不能将其直接描述为关节持续按该速度旋转。差分列仅使用历史配置的名义60Hz；本轮没有导出实际physics dt。即便dt已知，离散位置差分也不等于求解器步内的瞬时速度，不能直接据此判定SDK读回错误或否定动力学异常。

接触报告仍为12个刚体、0事件、无回调错误；缺少已知接触正对照，不证明无接触。启动日志的TGS velocity-iterations警告和Direct GPU setGlobalPose错误值得随配置审查，但目前没有因果证据。

下一步v7只增加运行时配置、源码及逐步pre/post状态记录，保持v6路径、控制、门限和预算。导出USD机器人/物理场景属性、实际dt、有效gains及求解器属性（可用则记录，不可用显式记录错误）。不扫描质量、阻尼或迭代数，不改为只用位置差分放行。

![位置与速度](position_velocity_consistency.png)
'''
(out/'pilot_review.md').write_text(report,encoding='utf-8')
print('V6_AUDIT_OK')
