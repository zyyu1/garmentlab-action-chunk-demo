"""Read old hem attempts before selecting one terminal-placement change."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from minimum_fold_geometry import support_summary,supported_material_target,material_to_ee_target

root=Path(__file__).resolve().parent;out=root/'minimum_hem_review';out.mkdir(exist_ok=True)
names=['day4-l1-hem-fold-20261026-052424-872450','day4-l1-hem-fold-20261026-055645-888101']
rows=[];fig,axes=plt.subplots(1,2,figsize=(11,5))
for ax,name in zip(axes,names):
    p=root/'results'/name
    with np.load(p/'fold_definition.npz') as f:plan={k:f[k].copy() for k in f.files}
    with np.load(p/'05_place.npz') as f:v=f['vertices'].copy();ee=f['ee_position'].copy()
    mask=plan['source_mask'];pick=int(plan['pick_index']);nominal=plan['target_reference']
    support=support_summary(v,mask,pick)
    try:
        chosen=supported_material_target(v,mask,pick,nominal,float(plan['fold_line_y']))
        chosen['ee_target_xyz']=material_to_ee_target(ee,v[pick],chosen['material_target_xyz']).tolist()
    except RuntimeError as exc:chosen={'selection_error':repr(exc)}
    rows.append({'run':name,'actual_material_pick_xyz':v[pick].tolist(),'actual_ee_xyz':ee.tolist(),
                 'nominal_mirror_material_xyz':nominal.tolist(),
                 'material_xy_error_to_nominal_m':float(np.linalg.norm(v[pick,:2]-nominal[:2])),
                 'material_3d_error_to_nominal_m':float(np.linalg.norm(v[pick]-nominal)),
                 'support':support,'candidate_selection':chosen})
    fixed=v[~mask];ax.scatter(fixed[:,0],fixed[:,1],s=2,c=fixed[:,2],cmap='Blues',alpha=.6)
    ax.scatter(*v[pick,:2],marker='x',s=60,color='red',label='Actual held material point')
    ax.scatter(*nominal[:2],marker='+',s=60,color='black',label='Nominal mirror goal')
    if 'material_target_xyz' in chosen:ax.scatter(*chosen['material_target_xyz'][:2],s=45,color='green',label='Nearby support goal')
    ax.set(xlim=(-.12,.12),ylim=(-.36,-.14),title=name.split('-')[-2],xlabel='x (m)',ylabel='y (m)');ax.set_aspect('equal');ax.legend(fontsize=7)
fig.suptitle('Existing hem place snapshots: target coverage is insufficient before release')
fig.tight_layout();fig.savefig(out/'hem_terminal_support_review.png',dpi=170);plt.close(fig)
(out/'hem_terminal_audit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
last=rows[-1];goal=last['candidate_selection']
(out/'review.md').write_text(f'''# 最低完成版：已有下摆终段审查

范围：仅单次下摆half-fold，退出三阶段整衣流程；参考配置固定为已验证多槽位抓取的原机器人/衣物配置。

复核hem-v9与低弧线hem-v11的05_place完整快照。低弧线中实际抓点{last['actual_material_pick_xyz']}，末端{last['actual_ee_xyz']}；名义镜像材料目标{last['nominal_mirror_material_xyz']}。材料XY误差{last['material_xy_error_to_nominal_m']*1000:.2f}mm，三维误差{last['material_3d_error_to_nominal_m']*1000:.2f}mm，不能直接把EE目标当成材料目标。

低弧线放置时源半片z中位约70mm、与固定半片最近投影的垂向间隔中位约46mm；约17.4%源点同时满足XY<10mm及0–30mm垂向间隔这一几何代理。抓点最近固定材料XY距离约24.75mm。已有最大边长比约1.934及回弹证据，支持终段仍未充分放松/铺下；不能由这些几何量声称已测到支撑力。

唯一候选改动：保持低弧线前缀不变，只替换释放前终段为材料相对邻近固定半片的支撑放置。在旧快照上，限制XY修正≤60mm、保持名义x，可找到邻近稳定点簇，目标{goal.get('material_target_xyz')}，对应EE目标{goal.get('ee_target_xyz')}。这是离线可行性检查，不是仿真结果。

实际运行时根据当前固定材料点重新选支撑区域，使用实际材料点—EE偏移换算目标，保持目标一段有界时间再完整OPEN、退让、静置。20mm中心间隔仅为几何clearance代理，不是未读回solidRestOffset的替代值，也不代表接触力确认。完整释放后的保持才是开发验证重点。

只运行一个这样的路径候选。若失败，再根据具体证据决定是否做用户允许的一组弯曲配置对照，不做参数网格。当前不冻结评价阈值，不将流程passed当成半折成功。

![放置支撑审查](hem_terminal_support_review.png)
''',encoding='utf-8')
print('MINIMUM_HEM_OFFLINE_REVIEW_OK')
