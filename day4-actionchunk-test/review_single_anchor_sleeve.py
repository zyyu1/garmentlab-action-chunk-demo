"""Matched first-stage comparison: point-grasp proxy versus multi-anchor patch."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'.analysis-deps'))
import imageio_ffmpeg
base=root/'results/day4-official-three-fold-20261027-000627-746461'
out=root/'results/day4-single-anchor-sleeve-20261027-004413-549160'
a=json.loads((base/'result.json').read_text());b=json.loads((out/'result.json').read_text())
assert b['passed'] and b['pipeline_completed'] and not b['formal_day4_success'] and not b['fold_success_accepted']
for name,h in json.loads((out/'source/manifest.json').read_text()).items():assert hashlib.sha256((out/'source'/name).read_bytes()).hexdigest()==h
for label,item in b['runtime_source_hashes'].items():assert hashlib.sha256((out/'runtime_source'/(label+'.py')).read_bytes()).hexdigest()==item['sha256']
old_actions=[x for x in a['actions'] if x['label'].startswith('1_right_sleeve')]
assert len(old_actions)==len(b['actions'])==34
assert [x['label'] for x in old_actions]==[x['label'] for x in b['actions']]
assert [x['matrix'] for x in old_actions]==[x['matrix'] for x in b['actions']]
assert a['robot_config']==b['robot_config'] and a['material_readback']==b['material_readback']
assert a['cycles'][0]['actual_waypoints']==b['cycles'][0]['actual_waypoints']
initial=np.load(base/'00_initial.npz')['vertices'];assert np.array_equal(initial,np.load(out/'00_initial.npz')['vertices'])
mass=json.loads((out/'mass_audit.json').read_text());assert all(all(x['checks'].values()) for x in mass['reads'].values())
trace=json.loads((out/'state_trace.json').read_text());assert all(sum(x['enabled'] for x in s['slots'])<=1 for s in trace)
assert [x['used'] for x in b['slot_status_final']]==[True,False,False]
assert all(not x['enabled'] and not x['holding'] and x['constraint_exists'] for x in b['slot_status_final'])
assert all(len(x['anchor_ids'])==1 for x in b['slots_precreated'])
assert b['single_anchor_max_gap_m']['right_sleeve']<.01
faces=np.load(base/'cloth_constructed.npz')['faceVertexIndices'].reshape(-1,3)
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
length=np.linalg.norm(initial[edges[:,0]]-initial[edges[:,1]],axis=1)
plan=json.loads((base/'expert_plan.json').read_text());T=np.asarray(plan['xy_affine_transform'])
canonical=(initial[:,:2]-T[2])@np.linalg.inv(T[:2]);core=(abs(canonical[:,0])<.08)&(canonical[:,1]>-.42)&(canonical[:,1]<-.32)
pick=b['slots_precreated'][0]['pick_index'];common_ids=np.asarray(a['slots_precreated'][0]['anchor_ids'])
neighborhood=np.isin(edges,common_ids).any(axis=1)
def geometry(v):
    x=initial[core,:2];y=v[core,:2];U,_,V=np.linalg.svd((x-x.mean(0)).T@(y-y.mean(0)));R=U@V
    if np.linalg.det(R)<0:U[:,-1]*=-1;R=U@V
    t=y.mean(0)-x.mean(0)@R
    ratio=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)/length
    worst=int(ratio.argmax())
    return {'core_yaw_deg':float(np.rad2deg(np.arctan2(R[0,1],R[0,0]))),
            'core_centroid_xy_drift_m':(y.mean(0)-x.mean(0)).tolist(),
            'edge_ratio_to_initial_p95_p99_max':np.percentile(ratio,[95,99,100]).tolist(),
            'common_anchor_neighborhood_edge_ratio_max':float(ratio[neighborhood].max()),
            'worst_edge_vertices':edges[worst].tolist(),
            'core_registered_material_xy_error_p95_m':float(np.percentile(np.linalg.norm((v[:,:2]-t)@R.T-initial[:,:2],axis=1),95))}
rows=[];meshes={}
for folder,label in [(base,'multi-anchor'),(out,'single-anchor')]:
    held=np.load(folder/'1_right_sleeve_move_2.npz')['vertices'];released=np.load(folder/'1_right_sleeve_released.npz')['vertices']
    rows.append({'model':label,'held':geometry(held),'released_after_common_120_steps':geometry(released),
                 'release_pick_xy_motion_m':float(np.linalg.norm(held[pick,:2]-released[pick,:2])),
                 'held_pick_xyz':held[pick].tolist(),'released_pick_xyz':released[pick].tolist()})
    meshes[label]={'initial':initial,'held':held,'released':released}
fig,axs=plt.subplots(2,3,figsize=(13,8))
moving=canonical[:,0]>.11641
for row,(model,stages) in enumerate(meshes.items()):
    for ax,(phase,v) in zip(axs[row],stages.items()):
        ax.scatter(initial[::4,0],initial[::4,1],s=1,color='gray',alpha=.25)
        ax.scatter(v[~moving,0],v[~moving,1],s=.8,color='tab:blue',alpha=.5)
        ax.scatter(v[moving,0],v[moving,1],s=1,color='tab:orange',alpha=.6)
        ax.scatter(*v[pick,:2],s=30,marker='x',color='red')
        ax.set(xlim=(-.55,.6),ylim=(-.85,.02),xlabel='x (m)',ylabel='y (m)',title=model+' / '+phase);ax.set_aspect('equal')
fig.suptitle('Matched initial mesh and 34 action matrices; both release toward an unfolded sleeve')
fig.tight_layout();fig.savefig(out/'single_vs_multi_material_comparison.png',dpi=160);plt.close(fig)
frames,duration=imageio_ffmpeg.count_frames_and_secs(str(out/'episode.mp4'))
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24');meta=next(reader);w,h=meta['size'];wanted=set(np.linspace(0,frames-1,6).astype(int).tolist());decoded=[]
try:
    for i,raw in enumerate(reader):
        if i in wanted:decoded.append((i,np.frombuffer(raw,dtype=np.uint8).reshape(h,w,3).copy()))
finally:reader.close()
assert len(decoded)==6
fig,axs=plt.subplots(2,3,figsize=(12,6))
for ax,(i,im) in zip(axs.flat,decoded):ax.imshow(im);ax.set_title(f"t={i/meta['fps']:.1f}s");ax.axis('off')
fig.tight_layout();fig.savefig(out/'single_anchor_video_contact_sheet.png',dpi=140);plt.close(fig)
audit={'source_and_runtime_hashes_verified':True,'initial_vertices_exact':True,'first_stage_34_action_matrices_exact':True,
       'robot_and_material_readbacks_exact':True,'single_anchor_count_per_slot_verified':True,
       'max_reported_physical_anchor_gap_m':b['single_anchor_max_gap_m']['right_sleeve'],
       'same_120_step_post_release_snapshot_comparison':rows,'candidate_extra_final_settle_not_compared_to_full_fold_final':True,
       'video_frames':frames,'video_duration_seconds':duration,'full_three_stage_extension_recommended':False,
       'conclusion':'Single-anchor alone does not solve rebound; do not infer unique cause or physical clamp fidelity.'}
(out/'single_anchor_comparison_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
table='\n'.join(f"|{x['model']}|{x['release_pick_xy_motion_m']*1000:.1f}|{x['released_after_common_120_steps']['core_yaw_deg']:.2f}|{x['held']['edge_ratio_to_initial_p95_p99_max'][2]:.3f}|{x['held']['edge_ratio_to_initial_p95_p99_max'][1]:.3f}|" for x in rows)
(out/'pilot_review.md').write_text(f'''# 单锚点首袖对照核对（2026-10-26）

源文件/运行源码哈希通过；两组初始9945点网格完全相同，首袖34个动作标签及矩阵、实际两段目标一致，机器人与材料读回一致。质量读回通过，单锚点每槽1点，右袖最大实际顶点-刚体锚点间距5.324mm，通过10mm诊断界限。候选未用左袖/下摆，最终均禁用且路径保留。视频已在本地解码。

|模型|放置→释放120步后抓点XY回移 mm|释放后核心yaw °|放置最大边长比|放置P99边长比|
|---|---:|---:|---:|---:|
{table}

单点将回移减少约16%，躯干转动减少，但袖口仍展开。最大边长比升高；P99降低，说明分布与峰值变化不能用单一平均数概括。全部边长比对比相同初始settled网格，不是材料应力。局部峰值与共同锚点邻域指标见JSON。

只比较两组共同的释放后120步快照；单点额外final静置不能和基线完成全部三阶段后的04_final混用。下摆指标不适合判定单袖成功。候选最后画面仍为展开衣物。

结论：单锚点没有解决回弹，不推广到三阶段，不计正式成功。它同时改变自动附件生成/过滤声明，不能当成绝对隔离所有细节的纯锚点数试验；现有证据只否定“换成当前单点抓取就足以修复”的建议，不能排除任何多点姿态作用。

下一步停止锚点数/腕部/机器人参数链。已有构造源码和早先物理审计表明衣物使用stretch=10000、bend=100、shear=100、damping=0.2的粒子弹簧配置。SDK将bend描述为抵抗弯曲的线性弹簧，不能把数值100误解成旋转铰链刚度或据此直接判定不合理；该旧审计也不是本轮实时弹簧读回。若继续推进，应先明确物理可折性与路径放置的区分，避免凭最终IoU调参。当前未创建或启动下一组参数试跑。

![材料对照](single_vs_multi_material_comparison.png)

![单锚点视频抽帧](single_anchor_video_contact_sheet.png)
''',encoding='utf-8')
print('SINGLE_ANCHOR_MATCHED_COMPARISON_OK; NO_THREE_STAGE_EXTENSION')
