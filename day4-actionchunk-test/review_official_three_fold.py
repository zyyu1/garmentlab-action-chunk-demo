"""Locate failure phases using material correspondences, topology, and saved video."""
import hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'.analysis-deps'))
import imageio_ffmpeg
from hem_fold_geometry import hem_metrics
root=Path(__file__).resolve().parent
out=root/'results/day4-official-three-fold-20261027-000627-746461'
r=json.loads((out/'result.json').read_text());plan=json.loads((out/'expert_plan.json').read_text())
for n,h in json.loads((out/'source/manifest.json').read_text()).items():assert hashlib.sha256((out/'source'/n).read_bytes()).hexdigest()==h
for label,item in r['runtime_source_hashes'].items():assert hashlib.sha256((out/'runtime_source'/(label+'.py')).read_bytes()).hexdigest()==item['sha256']
assert r['pipeline_completed'] and r['passed'] and not r['formal_day4_success'] and not r['formal_12_action_budget_passed']
assert len(r['actions'])==r['public_action_count']==102 and all(all(a['checks'].values()) for a in r['actions'])
assert [x['slot'] for x in r['cycles']]==['right_sleeve','left_sleeve','hem']
assert all(all(x['checks'].values()) for x in r['cycles'])
trace=json.loads((out/'state_trace.json').read_text());assert all(sum(x['enabled'] for x in s['slots'])<=1 for s in trace)
assert all(not s['enabled'] and not s['holding'] and s['used'] and s['constraint_exists'] for s in r['slot_status_final'])
mass=json.loads((out/'mass_audit.json').read_text());assert all(all(x['checks'].values()) for x in mass['reads'].values())
with np.load(out/'fold_definition.npz') as f:initial=f['initial_vertices'].copy();mask=f['source_mask'].copy();line=float(f['fold_line_y'])
faces=np.load(out/'cloth_constructed.npz')['faceVertexIndices'].reshape(-1,3)
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
length=np.linalg.norm(initial[edges[:,0]]-initial[edges[:,1]],axis=1);assert np.all(length>1e-8)
T=np.asarray(plan['xy_affine_transform']);canonical=(initial[:,:2]-T[2])@np.linalg.inv(T[:2])
core=(abs(canonical[:,0])<.08)&(canonical[:,1]>-.42)&(canonical[:,1]<-.32)
assert core.sum()>100
def fit_core(vertices):
    x=initial[core,:2];y=vertices[core,:2];U,_,V=np.linalg.svd((x-x.mean(0)).T@(y-y.mean(0)));R=U@V
    if np.linalg.det(R)<0:U[:,-1]*=-1;R=U@V
    t=y.mean(0)-x.mean(0)@R
    return R,t,np.linalg.norm(x@R+t-y,axis=1)
labels=['00_initial','1_right_sleeve_move_2','1_right_sleeve_released','2_left_sleeve_move_2','2_left_sleeve_released','3_hem_move_2','3_hem_released','04_final']
rows=[];data={}
for label in labels:
    with np.load(out/(label+'.npz')) as f:v=f['vertices'].copy()
    assert v.shape==initial.shape and np.isfinite(v).all();data[label]=v
    ratio=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)/length
    R,t,res=fit_core(v);normalized=v.copy();normalized[:,:2]=(v[:,:2]-t)@R.T
    rows.append({'stage':label,'edge_ratio_to_initial_p95_p99_max':np.percentile(ratio,[95,99,100]).tolist(),
                 'core_centroid_displacement_m':(v[core,:2].mean(0)-initial[core,:2].mean(0)).tolist(),
                 'core_rigid_yaw_deg':float(np.rad2deg(np.arctan2(R[0,1],R[0,0]))),
                 'core_fit_p95_residual_m':float(np.percentile(res,95)),
                 'full_xy_material_error_after_core_registration_p95_m':float(np.percentile(np.linalg.norm(normalized[:,:2]-initial[:,:2],axis=1),95)),
                 'hem_proxy_metrics':hem_metrics(initial,v,{'fold_line_y':line,'source_mask':mask})})
assert all(np.isclose(rows[-1]['hem_proxy_metrics'][k],value) for k,value in r['fold_metrics'].items() if isinstance(value,(int,float)))
release=[]
for i,cycle in enumerate(r['cycles'],1):
    label=str(i)+'_'+cycle['slot'];pick=cycle['reference_stage']['pick_index']
    held=np.load(out/(label+'_move_2.npz'))['vertices'];end=np.load(out/(label+'_released.npz'))['vertices']
    release.append({'slot':cycle['slot'],'pick_index':pick,'held_pick_xyz':held[pick].tolist(),
                    'released_pick_xyz':end[pick].tolist(),'pick_release_xy_displacement_m':float(np.linalg.norm(end[pick,:2]-held[pick,:2]))})
fig,axs=plt.subplots(2,4,figsize=(15,8))
for ax,label,row in zip(axs.flat,labels,rows):
    v=data[label];ax.scatter(initial[::5,0],initial[::5,1],s=1,color='gray',alpha=.25)
    ax.scatter(v[~mask,0],v[~mask,1],s=.8,color='tab:blue',alpha=.5)
    ax.scatter(v[mask,0],v[mask,1],s=.8,color='tab:orange',alpha=.7)
    ax.axhline(line,color='black',ls=':',lw=1);ax.set_aspect('equal')
    ax.set(xlim=(-.65,.65),ylim=(-.95,.02),xlabel='x (m)',ylabel='y (m)',title=label+'\nyaw(core)='+format(row['core_rigid_yaw_deg'],'.1f')+'°')
fig.suptitle('Three-stage pilot: nominal moving hem half (orange) and other material (blue)')
fig.tight_layout();fig.savefig(out/'three_stage_material_comparison.png',dpi=160);plt.close(fig)
frames,duration=imageio_ffmpeg.count_frames_and_secs(str(out/'episode.mp4'))
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24')
metadata=next(reader);fps=float(metadata['fps']);width,height=metadata['size']
assert frames>20 and fps>0
selected=set(np.linspace(0,frames-1,8).astype(int).tolist());decoded=[]
try:
    for frame,raw in enumerate(reader):
        if frame in selected:decoded.append((frame,np.frombuffer(raw,dtype=np.uint8).reshape(height,width,3).copy()))
finally:reader.close()
assert len(decoded)==8
fig,axes=plt.subplots(2,4,figsize=(14,6))
for ax,(frame,image) in zip(axes.flat,decoded):
    ax.imshow(image);ax.set_title(f'Video t={frame/fps:.1f}s');ax.axis('off')
fig.tight_layout();fig.savefig(out/'video_contact_sheet.png',dpi=140);plt.close(fig)
audit={'source_hashes_verified':True,'runtime_source_hashes_verified':True,'public_actions':102,
       'video_frames_decoded_metadata':frames,'fps':fps,'sampled_states':len(trace),'core_material_points':int(core.sum()),
       'stage_geometry':rows,'release_material_motion':release,'formal_fold_success':False,
       'conclusion':'All three slots execute, but transfer stretches/reorients garment and release returns toward unfolded shape. Attachment torque hypothesis not proven.'}
(out/'three_fold_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
table='\n'.join(f"|{x['slot']}|{x['pick_release_xy_displacement_m']*1000:.1f}|" for x in release)
(out/'pilot_review.md').write_text(f'''# 三阶段位置折叠核对（2026-10-26）

流程与产物通过，折叠失败。源文件/运行源码哈希、三个抓取释放状态、质量记录和视频解码通过。102个公开动作，超过正式12步预算；不能计入正式Day4成功。

## 失败从第一阶段已经出现

|阶段|放置快照→释放静置后抓点XY位移 mm|
|---|---:|
{table}

右袖释放后上躯干核心材料点（999个）拟合yaw约-19.98°，质心平移约[58.6,-14.3]mm；左袖释放后yaw约7.60°，平移[-25.9,37.4]mm；最终yaw约18.93°，平移[-9.4,43.0]mm。核心选择来自初始映射到官方坐标后的abs(x)<0.08、-0.42<y<-0.32，仅用于诊断，不是新成功标准。

三个放置快照相对初始settled网格的最大边长比分别约1.621、1.930、2.288，释放后明显下降。此为几何长度比，不是应力或材料质量认证。视频和材料对应点共同显示拉伸、整件转动及释放后回弹；不是单纯末端没到目标。不能把hem半片指标用于评价前两次袖折是否完成，也不能由此唯一归因于多点约束。

最终原代理指标独立复算与结果一致：XY对齐约150.34mm、投影IoU约0.0361、越线比例约0.2374、反射目标误差约168.12mm。最后画面仍接近展开衣物。

下一步只做一组抓取模型对照：保留三阶段位置路径、物理配置及状态/预算记录，用预建单顶点锚点替代多点刚体锚定，检验局部旋转自由度是否改变回弹。该候选是抽象点抓取模型，不是已验证物理夹持；不能因更易折叠就直接当成正式机器人示范。必须检查实际跟随、局部伸长与释放结果。无需重新扫描质量、增益或迭代数。

![材料分阶段](three_stage_material_comparison.png)

![视频抽帧](video_contact_sheet.png)
''',encoding='utf-8')
print('OFFICIAL_THREE_FULL_REVIEW_OK; FOLD_FAILED')
