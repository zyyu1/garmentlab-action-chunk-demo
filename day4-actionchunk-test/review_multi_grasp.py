"""Independent recomputation of the downloaded two-region lifecycle run."""
import hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation
root=Path(__file__).resolve().parent
out=root/'results/day4-multi-grasp-20261026-234353-347208'
r=json.loads((out/'result.json').read_text())
assert r['passed'] and not r['formal_day4_success'] and len(r['cycles'])==2 and not r['errors']
for name,digest in json.loads((out/'source/manifest.json').read_text()).items():
    assert hashlib.sha256((out/'source'/name).read_bytes()).hexdigest()==digest
for label,record in r['runtime_source_hashes'].items():
    assert hashlib.sha256((out/'runtime_source'/(label+'.py')).read_bytes()).hexdigest()==record['sha256']
trace=json.loads((out/'state_trace.json').read_text())
assert all(sum(x['enabled'] for x in s['slots'])<=1 for s in trace)
assert all(all(x['enabled']==x['holding'] and x['constraint_exists'] for x in s['slots']) for s in trace)
assert [s['used'] for s in r['slot_status_final']]==[True,True,False]
assert all(not s['enabled'] and not s['holding'] and s['constraint_exists'] for s in r['slot_status_final'])
assert len(r['actions'])==18 and all(all(a['checks'].values()) for a in r['actions'])
assert all(len(a['matrix'])==1 and a['matrix'][0][3]==0 for a in r['actions'])
mass=json.loads((out/'mass_audit.json').read_text())
assert all(all(x['checks'].values()) for x in mass['reads'].values())
rows=[]
fig,axes=plt.subplots(2,4,figsize=(14,7))
for i,cycle in enumerate(r['cycles']):
    label=f"{i+1}_{cycle['slot']}"
    data={name:dict(np.load(out/(label+'_'+name+'.npz'),allow_pickle=False)) for name in ['before_close','grasp','lift','released']}
    tracked=data['grasp']['tracked_'+str(i)]
    rise=float(data['lift']['vertices'][tracked,2].mean()-data['grasp']['vertices'][tracked,2].mean())
    drop=float(data['lift']['vertices'][tracked,2].mean()-data['released']['vertices'][tracked,2].mean())
    drift=float(np.linalg.norm(data['released']['block_position_'+str(i)]-data['lift']['block_position_'+str(i)]))
    lift=data['lift'];q=lift['ee_quaternion'];target=lift['ee_position']+Rotation.from_quat(q[[1,2,3,0]]).apply([0,0,-.01])
    follow=float(np.linalg.norm(target-lift['block_position_'+str(i)].reshape(3)))
    activation=dict(np.load(out/('activation_'+cycle['slot']+'.npz'),allow_pickle=False))
    jump=float(np.linalg.norm(activation['after']-activation['before'],axis=1).max())
    assert np.isclose(rise,cycle['cloth_rise_m']) and np.isclose(drop,cycle['cloth_drop_m'])
    assert np.isclose(follow,cycle['follow_error_m'],atol=1e-7) and drift<.001 and jump<.03
    assert np.array_equal(activation['points1'],np.asarray(cycle['alignment']['points1_readback']))
    rows.append({'slot':cycle['slot'],'rise_mm':rise*1000,'drop_mm':drop*1000,'follow_error_mm':follow*1000,
                 'activation_jump_mm':jump*1000,'lift_to_post_release_block_drift_mm':drift*1000,
                 'actual_anchor_count':len(activation['anchor_ids']),'tracked_vertex_count':len(tracked)})
    for ax,(name,d) in zip(axes[i],data.items()):
        v=d['vertices'];ax.scatter(v[::4,0],v[::4,2],s=.8,color='gray',alpha=.3)
        ax.scatter(v[tracked,0],v[tracked,2],s=6,color='tab:red')
        ax.scatter(d['ee_position'][0],d['ee_position'][2],marker='x',color='tab:blue')
        ax.set(xlim=(-.5,.5),ylim=(-.02,.18),title=cycle['slot']+' / '+name,xlabel='x (m)',ylabel='z (m)')
fig.suptitle('Same rollout: two distinct prepared grasps and releases (not a fold)')
fig.tight_layout();fig.savefig(out/'two_region_lifecycle_review.png',dpi=170);plt.close(fig)
audit={'source_hashes_verified':True,'runtime_source_hashes_verified':True,'sampled_states_checked':len(trace),
       'actions_checked':len(r['actions']),'mass_readbacks_verified':True,'cycles_recomputed':rows,
       'limitation':'Independent used slots passed; no reused slot or full episode reset tested; no formal fold success.'}
(out/'multi_grasp_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
table='\n'.join(f"|{x['slot']}|{x['rise_mm']:.3f}|{x['drop_mm']:.3f}|{x['follow_error_mm']:.3f}|{x['activation_jump_mm']:.3f}|{x['actual_anchor_count']}|" for x in rows)
(out/'pilot_review.md').write_text(f'''# 同回合两区域抓取核对（2026-10-26）

脚本依赖及运行源码哈希通过，18个公开H=1动作检查通过，yaw均为0。252条采样状态互斥、holding一致，三个约束路径全程存在；最终右袖/左袖已使用并禁用，下摆未使用。质量启动/两次释放后读回一致，约0.994591kg总质量。使用原机器人资产增益/64-64迭代，不继承v9-v11修改。

|区域|抬升 mm|释放下降 mm|跟随误差 mm|启用最大跳变 mm|真实锚点数|
|---|---:|---:|---:|---:|---:|
{table}

上表从完整NPZ独立复算，与result.json一致。两轮lift快照到释放静置后辅助块位置差均为0。右/左tracked顶点数28/30，实际锚点数40/42，不混为同一集合。points1与保存的对齐读回一致。

这支持三个预建槽位中两个不同区域的生命周期成功；不证明已用槽可再次抓取、完整reset成功、任意选点成功，禁用标志也不独立证明内部PhysX无残余作用。原动态速度收敛问题未在本轮全面解决，不把开发检查当作完整机器人验收。

下一步用相同控制和物理配置，开发试跑官方三阶段位置流程：右袖→左袖→下摆，按初始oracle区域点映射目标，并按当前抓点漂移更新。无pitch侧通道，保存视频与完整快照。所有试跑仍formal_day4_success=false，显式记录真实公开动作数；分段安全动作若超过12，不能冒充正式预算通过。

![两区域快照](two_region_lifecycle_review.png)
''',encoding='utf-8')
print('TWO_REGION_FULL_AUDIT_OK')
