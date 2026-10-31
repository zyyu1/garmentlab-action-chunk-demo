import sys,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else base/'results/day4-square-grasp-hold-20261031-104528-426384'
v3=base/'results/day4-square-grasp-pose-20261031-093041-511232'
r=json.loads((out/'result.json').read_text());prior=json.loads((v3/'result.json').read_text())

# ---- source / upload / runtime integrity ----
manifest=json.loads((out/'source/manifest.json').read_text())
source_hash={n:hashlib.sha256((out/'source'/n).read_bytes()).hexdigest()==h for n,h in manifest.items()}
upload=json.loads((base/'square-grasp-hold-files.json').read_text())
upload_hash={n:hashlib.sha256((base/n).read_bytes()).hexdigest()==h for n,h in upload.items()}
runtime_hash={k:hashlib.sha256((out/'runtime_source'/(k+'.py')).read_bytes()).hexdigest()==m['sha256']
              for k,m in r['runtime_source_hashes'].items()}
assert all(source_hash.values()) and all(upload_hash.values()) and all(runtime_hash.values())

# ---- video ----
sys.path.insert(0,str(base/'.analysis-deps'));import imageio_ffmpeg
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24');meta=next(reader)
decoded=sum(1 for _ in reader)
assert decoded==r['video_frames'] and tuple(meta['size'])==(640,480)

# ---- hold trace ----
rows=[json.loads(l) for l in (out/'hold_trace.jsonl').read_text().splitlines() if l.strip()]
assert len(rows)==60
steps=np.array([x['hold_step'] for x in rows]);phys=np.array([x['physics_step'] for x in rows])
assert np.array_equal(steps,np.arange(1,61)) and np.all(np.diff(phys)==1)
ee=np.array([x['ee_position'] for x in rows]);gt=np.array(r['pose_contract']['ee_target'])
jp=np.array([x['joint_positions'] for x in rows])[:,:7];jv=np.array([x['joint_velocities'] for x in rows])[:,:7]
bp=np.array([x['block_position'] for x in rows]);bt=np.array([x['block_target'] for x in rows])
assert np.isfinite(ee).all() and np.isfinite(jp).all() and np.isfinite(jv).all() and np.isfinite(bp).all()
err=np.linalg.norm(ee-gt,axis=1)*1000;spd=np.abs(jv).max(axis=1)
def qang(a,b):
 qa=np.asarray(a,float);qb=np.asarray(b,float)
 qa/=np.linalg.norm(qa);qb/=np.linalg.norm(qb)
 return float(np.degrees(2*np.arccos(min(1.,abs(float(np.dot(qa,qb)))))))
hold={'steps':len(rows),'physics_steps':[int(phys[0]),int(phys[-1])],
      'ee_error_first_mm':float(err[0]),'ee_error_max_mm':float(err.max()),'ee_error_last_mm':float(err[-1]),
      'ee_drift_first_last_mm':float(np.linalg.norm(ee[-1]-ee[0])*1000),
      'ee_range_mm':[float(x*1000) for x in (ee.max(0)-ee.min(0))],
      'max_arm_speed_rad_s':float(spd.max()),'orientation_drift_deg':qang(rows[0]['ee_quaternion_wxyz'],rows[-1]['ee_quaternion_wxyz']),
      'anchor_gap_max_mm':float(max(x['anchor_gap_max_m'] for x in rows)*1000),
      'holding_all':all(x['holding'] for x in rows),'attachment_enabled_all':all(x['attachment_enabled'] for x in rows),
      'joint_target_max_diff_rad':float(np.abs(jp[0]-np.array(r['hold_target_joint_positions'])).max()),
      'block_position_mean_mm':[float(x*1000) for x in bp.mean(0)],
      'block_target_mean_mm':[float(x*1000) for x in bt.mean(0)],
      'block_z_shortfall_mm':float((bt[:,2]-bp[:,2]).mean()*1000),
      'block_position_range_mm':[float(x*1000) for x in (bp.max(0)-bp.min(0))]}
assert hold['ee_error_max_mm']<10 and hold['max_arm_speed_rad_s']<.1 and hold['anchor_gap_max_mm']<=10

# ---- v3 hold metrics from control trace ----
c3=[json.loads(l) for l in (v3/'control_trace.jsonl').read_text().splitlines() if l.strip()]
st3=[x for x in c3 if x.get('phase')=='held_stationary' and x.get('event')=='state' and x.get('when')=='after']
assert len(st3)==60
ee3=np.array([x['ee_position'] for x in st3]);gt3=np.array(prior['pose_contract']['ee_target'])
err3=np.linalg.norm(ee3-gt3,axis=1)*1000;spd3=np.abs(np.array([x['joint_velocities'][:7] for x in st3])).max(axis=1)
hold3={'ee_error_first_mm':float(err3[0]),'ee_error_max_mm':float(err3.max()),'ee_error_last_mm':float(err3[-1]),
       'ee_drift_first_last_mm':float(np.linalg.norm(ee3[-1]-ee3[0])*1000),'max_arm_speed_rad_s':float(spd3.max())}

# ---- control trace: joint hold has no RMP calls ----
ctrl=[json.loads(l) for l in (out/'control_trace.jsonl').read_text().splitlines() if l.strip()]
hc=[x for x in ctrl if x.get('phase')=='held_stationary' and x.get('event')=='call']
assert len(hc)==60 and all(x['method']=='apply_action' for x in hc)
for x in hc:
 sub=x['submitted_action']
 assert sub['joint_indices']==list(range(7)) and sub['joint_velocities']==[0.]*7
 assert np.allclose(sub['joint_positions'],r['hold_target_joint_positions'],atol=1e-9)
assert not any(x.get('phase')=='held_stationary' and x.get('event')=='controller_output' for x in ctrl)
forbidden=[x for x in ctrl if x.get('event')=='call' and any(k in str(x.get('method','')).lower() for k in
           ('set_world_pose','set_local_pose','set_joint_positions','set_joint_position'))]
assert not forbidden

# ---- snapshots: deterministic through close, divergence only in hold ----
def snapdiff(lab):
 a=np.load(out/(lab+'.npz'));b=np.load(v3/(lab+'.npz'))
 keys=sorted(set(a.files)&set(b.files));exact=all(np.array_equal(a[k],b[k]) for k in keys)
 dv=np.linalg.norm(a['vertices']-b['vertices'],axis=1) if a['vertices'].shape==b['vertices'].shape else None
 return {'exact':bool(exact),'max_vertex_diff_mm':None if dv is None else float(dv.max()*1000),
         'mean_vertex_diff_mm':None if dv is None else float(dv.mean()*1000),
         'ee_diff_mm':float(np.linalg.norm(a['ee_position']-b['ee_position'])*1000)}
common={lab:snapdiff(lab) for lab in ['00_initial','01_before_close','02_grasp','03_held','04_released']}
assert all(common[lab]['exact'] for lab in ['00_initial','01_before_close','02_grasp'])
assert not common['03_held']['exact']

# ---- actions / contact / release ----
acts=r['actions']
through_close=[(a['label'],a['matrix'],a['response']['info']['step_count']) for a in acts[:3]]
through_close3=[(a['label'],a['matrix'],a['response']['info']['step_count']) for a in prior['actions'][:3]]
release_steps=[a['response']['info']['step_count'] for a in acts][3]
contact=json.loads((out/'block_contact_report.json').read_text())
filters=json.loads((out/'collision_filter_audit.json').read_text())
slot_final=r['slot_status_final']
release_ok=(not any(s['holding'] or s['enabled'] for s in slot_final))
contact_valid=contact['positive_control_block_ground_events']>0 and contact['callback_count']>0
assert r['passed'] is True and r['fold_success_accepted'] is False and r['formal_day4_success'] is False
assert release_ok and contact['unexpected_robot_block_contacts']==0 and not contact['errors']

audit={'version':r['probe_version'],'source_hash':source_hash,'upload_hash':upload_hash,'runtime_hash':runtime_hash,
       'video_frames':decoded,'video_size':list(meta['size']),'frame_errors':r['frame_errors'],'stage_images':r['stage_images'],
       'hold':hold,'v3_hold':hold3,'hold_calls':{'apply_action':len(hc),'controller_forward':0},'forbidden_setter_calls':len(forbidden),
       'common_snapshots':common,'action_steps':[a['response']['info']['step_count'] for a in acts],
       'through_close_exact':through_close==through_close3,'release_steps_v3':[a['response']['info']['step_count'] for a in prior['actions']][3],
       'release_state_ok':release_ok,'contact_valid':contact_valid,'contact':contact,'collision_groups':filters['groups'],
       'passed':r['passed'],'fold_success_accepted':r['fold_success_accepted'],'formal_day4_success':r['formal_day4_success'],
       'errors':r['errors']}
(out/'independent_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')

fig,axs=plt.subplots(1,2,figsize=(11,4))
axs[0].plot(steps,err3,label='v3 RMP hold');axs[0].plot(steps,err,label='v4 joint hold')
axs[0].axhline(10,color='red',linestyle='--',label='10 mm gate')
axs[0].set(xlabel='hold step',ylabel='EE position error (mm)');axs[0].legend()
axs[1].plot(steps,spd3,label='v3 RMP hold');axs[1].plot(steps,spd,label='v4 joint hold')
axs[1].axhline(.1,color='red',linestyle='--',label='0.1 rad/s gate');axs[1].set_yscale('log')
axs[1].set(xlabel='hold step',ylabel='max arm joint speed (rad/s)');axs[1].legend()
fig.tight_layout();fig.savefig(out/'hold_v3_v4.png',dpi=150);plt.close(fig)

review=f'''# v4 关节锁定保持审查

结论：held gate 通过，v3 的固定目标 RMP 发散在关节锁定下消失；但接触通道正控为 0，通道无效，第 1 步不能按预登记规则解锁，不进入 L1 折叠。正式成功 0。

## 完整性

19 份源码自哈希、20 份上传清单哈希及 4 份运行时源码哈希全部一致；视频 255 帧、640×480 解码通过，5 张阶段图、0 帧错误；4 个公共动作全部执行且 checks 全真，无运行错误。00_initial、01_before_close、02_grasp 三个快照与 v3 逐顶点、逐位姿完全相同，说明关节锁定前的路径确定性一致。

|指标|v3|v4|
|---|---:|---:|
|保持末端位置误差（首/轨迹最大/末）|0.46/35.04/19.19 mm|0.474/0.474/0.473 mm|
|保持臂速（轨迹最大/末值）|4.40/0.518 rad/s|0.0091/0.0086 rad/s|
|保持末端漂移（首→末）|19.12 mm|0.003 mm|
|保持姿态漂移（首→末）|—|0.0005°|
|锚点最大间隙|2.81 mm|1.36 mm|
|release 动作步数|753|731|

v3 控制轨迹中保持阶段的瞬时最大位置误差 35.0 mm、瞬时最大臂速 4.40 rad/s；判定所用保持末值 19.19 mm/0.518 rad/s，两者都超过门槛。v4 的 60 步保持中，每一步都只提交 7 个臂关节的位置目标与零速度目标（joint_indices 0–6），保持阶段 controller.forward 为 0，controller_output 为 0；全轨迹未出现 Python 层 set_world_pose/set_local_pose/set_joint_positions 调用。相对保持起始关节目标的最大偏差约 1.5×10⁻⁵ rad。因此 v3 的失稳确实可以在不调用 RMP 的条件下绕过，且保持期间没有出现末端/关节瞬移。

## 接触通道无效

`block_contacts.jsonl` 为空；`callback_count=0`、`event_count=0`，块-地正控也是 0。保持阶段辅助块中心 z 恒为 15.000 mm，而目标 z 为 10.207 mm（低 4.79 mm，低于地面），块位置变化 <0.001 mm；这与块被地面持续支撑一致，但接触记录器没有给出任何事件。按预登记判读，正控为 0 时通道记无效，不能据此判定无 robot_block 接触。

碰撞审计显示 robot_group 与 attach_group 互相 filteredGroups，辅助块碰撞体 enabled。robot↔attach 本就被设计过滤，因此即使记录器正常，robot_block 类别也不应出现——它不是机械隔离的独立证据。需要先做出有效正控，才能把“0 接触”作为解锁依据。

## 判读与限制

- held gate 通过（0.474 mm、0.0086 rad/s、姿态到达、锚点间隙 1.36 mm），说明关节空间锁定可稳定维持，且 v3 的 19 mm/10.7° 漂移不是保持期间不可避免的。
- 但本轮仍不能排除通过夹爪/辅助块传入的外力；辅助块始终被地面挡住，没有离地，因此本轮没有验证“夹起”或块-手指夹持，只验证了固定构型下的控制与释放。
- 接触证据无效，故第 1 步不解锁；不接回 L1，不延长保持、不改阈值、不调 RMP 增益。正式成功保持 0。
- 日志在 reset 后出现一次原生 PhysX `setGlobalPose/setLinearVelocity/setAngularVelocity` 被 direct-GPU API 拒绝的错误（158 s，首个动作前），与 v3 相同；Python 层无对应调用，保持阶段未再出现。

## 下一步

先修复并验证接触正控（例如在仿真启动前应用接触报告 API，或设计一个必然发生的确定性接触），确认能记录到块-地事件后，再决定是否复跑 v4 保持。未取得有效接触证据前不进入 L1。

产物：independent_audit.json、hold_v3_v4.png；本地分析脚本 review_square_grasp_hold_v4.py。
'''
(out/'review.md').write_text(review,encoding='utf-8')
print(json.dumps({'hold':hold,'v3_hold':hold3,'common_snapshots':common,'contact_valid':contact_valid,
                  'contact_counts':contact['counts'],'video_frames':decoded,'release_steps':release_steps,
                  'through_close_exact':through_close==through_close3},indent=2,ensure_ascii=False))
