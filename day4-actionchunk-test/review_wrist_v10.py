"""Review geometry inertia candidate and prepare one bounded drive-gain profile test."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parent
out=root/'results/day4-wrist-ik-execution-20261026-230420-185319'
prev=root/'results/day4-wrist-ik-execution-20261026-222519-595953'
r=json.loads((out/'result.json').read_text());a=json.loads((prev/'result.json').read_text())
e=json.loads((out/'effective_inertia.json').read_text())
c=json.loads((out/'runtime_config.json').read_text());ca=json.loads((prev/'runtime_config.json').read_text())
assert r['script_sha256']==hashlib.sha256((root/'day4-wrist-ik-execution-v10.py').read_bytes()).hexdigest()
assert e['verified'] and len(r['inertia_overrides'])==11
base=json.loads((root/'results/day4-franka-asset-audit-20261026-224552-466537/asset_provenance.json').read_text())['runtime_tensor_methods']['physics_tensor_view']['values']
old_i=np.asarray(base['get_inertias']['value']).reshape(12,3,3)
new_i=np.asarray(e['inertias']).reshape(12,3,3)
assert np.all(np.linalg.eigvalsh(new_i)>0)
assert np.allclose(e['masses'],base['get_masses']['value'],rtol=1e-5)
assert e['gains']==ca['runtime_getters']['controller']['get_gains']['value']
assert c['runtime_getters']['world']==ca['runtime_getters']['world']
for label,record in c['source_hashes'].items():
    assert record['sha256']==ca['source_hashes'][label]['sha256']
    assert record['sha256']==hashlib.sha256((out/(label+'_runtime.py')).read_bytes()).hexdigest()
states=[json.loads(s) for s in (out/'step_states.jsonl').read_text().splitlines()]
assert len(states)==sum(t.get('steps',len(t.get('trace',[]))) for t in r['targets'])
assert all(states[i]['after']==states[i+1]['before'] for i in range(len(states)-1))
dt=c['runtime_getters']['world']['get_physics_dt']['value']
assert np.allclose([x['after']['current_time']-x['before']['current_time'] for x in states],dt,rtol=1e-6)
t=r['targets'][-1];s=[x for x in t['trace'] if x['phase']=='settling']
assert len(s)==240 and not t['reached']
q=np.asarray([x['actual'] for x in s]);v=np.asarray([x['actual_velocity'] for x in s])
stats=[]
for j,name in enumerate(t['joint_names']):
    stats.append({'joint':name,'last60_position_range_rad':float(np.ptp(q[-60:,j])),
                  'last60_velocity_min_rad_s':float(v[-60:,j].min()),'last60_velocity_max_rad_s':float(v[-60:,j].max()),
                  'last60_difference_speed_max_rad_s':float(abs(np.diff(q[-60:,j])/dt).max())})
reduction=100*(1-t['final_joint_speed_rad_s']/a['targets'][-1]['final_joint_speed_rad_s'])
audit={'script_hash_matches':True,'runtime_source_hashes_match_v9':True,'mass_gain_dt_unchanged':True,
       'state_samples':len(states),'actual_inertia_eigenvalues':np.linalg.eigvalsh(new_i).tolist(),
       'inertia_trace_ratios_to_original':(np.trace(new_i,axis1=1,axis2=2)/np.trace(old_i,axis1=1,axis2=2)).tolist(),
       'final_speed_reduction_from_v9_percent':reduction,'joints':stats,'all_targets_reached':False}
(out/'v10_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
fig,axs=plt.subplots(2,1,figsize=(11,7))
for record,label in [(a,'v9: explicit inertia'),(r,'v10: geometry-derived inertia')]:
    trace=[x for x in record['targets'][-1]['trace'] if x['phase']=='settling']
    axs[0].plot(np.arange(1,len(trace)+1)*dt,[max(abs(v) for v in x['actual_velocity']) for x in trace],label=label)
axs[0].axhline(.05,color='red',ls=':',label='0.05 rad/s gate');axs[0].set_xlabel('Waypoint 27 settling time (s)');axs[0].set_ylabel('Max reported joint speed (rad/s)');axs[0].legend();axs[0].grid(alpha=.3)
idx=np.arange(12)
axs[1].plot(idx,np.trace(old_i,axis1=1,axis2=2),'o-',label='Original effective inertia trace')
axs[1].plot(idx,np.trace(new_i,axis1=1,axis2=2),'o-',label='v10 effective inertia trace')
axs[1].set_yscale('log');axs[1].set_xlabel('Tensor body row (not verified link-name order)');axs[1].set_ylabel('Inertia trace (kg m²)');axs[1].legend();axs[1].grid(alpha=.3)
fig.tight_layout();fig.savefig(out/'v10_inertia_and_velocity.png',dpi=170);plt.close(fig)
(out/'pilot_review.md').write_text(f'''# v10 几何惯量候选核对（2026-10-26）

运行脚本哈希及导出源码哈希通过。11项显式惯量覆盖在首次reset前完成，实时惯量全部正定、与旧值有明显差异，质量、驱动增益、dt保持一致。不是只改USD后假定生效。

实际主惯量：link行0约0.0116–0.0221、行1约0.00723–0.0273、行5约0.00976–0.0655 kg·m²；手指行10/11约2.4e-6–1.6e-5 kg·m²。数组顺序未由link名称验证，不能擅自把行号当作link编号。

第27点仍在240步保持后失败。末最大速度从v9的1.274502降至{t['final_joint_speed_rad_s']:.9f} rad/s，下降{reduction:.2f}%；位置误差{t['position_error_m']*1000:.6f} mm、姿态误差{t['rotation_error_rad']:.6f} rad。最后60帧joint6报告速度0.91714–0.91720 rad/s，位置范围仅1.43e-6 rad，最大差分速度约6.44e-5 rad/s。惯量候选没有解决剩余问题，不提高速度阈值，不声称fold成功或现实参数标定。

下一步停止惯量和迭代扫描，只做一组明确的驱动增益候选v11：在v10基础上首次reset前将7个臂关节USD stiffness/damping同时乘1e-6，保留两者比值、maxForce、手指、质量、几何惯量、迭代配置和控制条件；有效kp预期约572.958，kd约5.72958。这个有限增益配置是诊断候选，不是硬件标定。缩放量是明确记录的工程试验选择，不是由现有数据反推出的唯一解；使用同一原路径和门限判断，不进行自动多组搜索。

有效增益读回与预期不一致就停止，不执行路径。降低增益可能导致跟踪不足，应保留失败，不调整阈值。若仍失败，先复核结果并评估expert路径/抓取方式，避免无边界调参。

NVIDIA稳定性指导说明极硬驱动及过大驱动力可造成问题，并建议合理的驱动增益：
https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.0/dev_guide/guides/articulation_stability_guide.html

![对照](v10_inertia_and_velocity.png)
''',encoding='utf-8')
source=(root/'day4-wrist-ik-execution-v10.py').read_text(encoding='utf-8')
source=source.replace('ik-tail-execution-v10-geometry-inertia','ik-tail-execution-v11-finite-drive-gains')
paths=[f'/World/Franka/panda_link{j-1}/panda_joint{j}' for j in range(1,8)]
helper='\nARM_GAIN_PATHS='+repr(paths)+'''\nARM_GAIN_SCALE=1e-6

def request_finite_arm_gains(env):
    changes=[]
    for path in ARM_GAIN_PATHS:
        prim=env.world.stage.GetPrimAtPath(path)
        if not prim.IsValid():raise RuntimeError('Missing arm drive: '+path)
        record={'path':path,'scale':ARM_GAIN_SCALE,'attributes':{}}
        for name,expected in [('stiffness',1e7),('damping',1e5)]:
            attr=prim.GetAttribute('drive:angular:physics:'+name)
            before=float(attr.Get())
            if not np.isclose(before,expected,rtol=1e-6):raise RuntimeError('Unexpected drive gain: '+path+' '+name)
            if not attr.Set(before*ARM_GAIN_SCALE):raise RuntimeError('Gain edit failed')
            record['attributes'][name]={'before':before,'after':float(attr.Get())}
        changes.append(record)
    result['arm_gain_overrides']=changes
    (out/'arm_gain_overrides.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')

'''
source=source.replace('def request_geometry_inertia(env):',helper+'def request_geometry_inertia(env):')
needle='        request_geometry_inertia(env)'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n        request_finite_arm_gains(env)')
needle="    if gains!=BASELINE_GAINS:raise RuntimeError('Drive gains changed unexpectedly')"
replace="""    expected_gains=np.asarray(BASELINE_GAINS,dtype=float).copy()
    expected_gains[:,:7]*=ARM_GAIN_SCALE
    if not np.allclose(np.asarray(gains),expected_gains,rtol=1e-5,atol=1e-5):
        raise RuntimeError('Effective gains do not match scaled-arm / unchanged-finger expectation')
    record['expected_gains']=expected_gains.tolist()"""
assert source.count(needle)==1
source=source.replace(needle,replace)
source=source.replace('GEOMETRY_INERTIA_VERIFIED_MASSES_GAINS_UNCHANGED','GEOMETRY_INERTIA_MASS_AND_FINITE_ARM_GAINS_VERIFIED')
ast.parse(source,feature_version=(3,10))
old=ast.parse((root/'day4-wrist-ik-execution-v10.py').read_text(encoding='utf-8'));new=ast.parse(source)
for name in ('drive','drive_ik','submit_joint_targets','probe_step','request_geometry_inertia'):
    assert ast.dump(next(x for x in old.body if isinstance(x,ast.FunctionDef) and x.name==name))==ast.dump(next(x for x in new.body if isinstance(x,ast.FunctionDef) and x.name==name))
(root/'day4-wrist-ik-execution-v11.py').write_text(source,encoding='utf-8',newline='\n')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['day4-wrist-ik-execution-v11.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'wrist-ik-execution-v11-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
runner=(root/'run-wrist-ik-execution-v10.sh').read_text(encoding='utf-8').replace('v10','v11')
(root/'run-wrist-ik-execution-v11.sh').write_text(runner,encoding='utf-8',newline='\n')
print('V10_AUDIT_OK; V11_SYNTAX_AND_CONTROL_AST_OK; NOT_RUN_ON_GPU')
