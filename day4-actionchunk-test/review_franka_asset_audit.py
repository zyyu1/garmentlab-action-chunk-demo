"""Audit provenance/effective tensors and prepare isolated inertia-generation candidate."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
out=root/'results/day4-franka-asset-audit-20261026-224552-466537'
a=json.loads((out/'asset_provenance.json').read_text())
r=json.loads((out/'result.json').read_text())
c=json.loads((out/'runtime_config.json').read_text())
assert r['script_sha256']==hashlib.sha256((root/'day4-franka-asset-audit.py').read_bytes()).hexdigest()
assert r['asset_audit_completed'] and not r['wrist_path_executed'] and not r['targets']
assert r['asset_property_stack_errors']==0 and r['asset_property_stack_successes']==135
assert a['stage_meters_per_unit']==1 and a['stage_kilograms_per_unit']==1
raw=a['runtime_tensor_methods']['physics_tensor_view']['values']
assert all(raw[k]['status']=='ok' for k in ('get_masses','get_inertias','get_coms','get_link_transforms'))
masses=np.asarray(raw['get_masses']['value'])[0]
inertias=np.asarray(raw['get_inertias']['value'])[0].reshape(-1,3,3)
assert len(masses)==12 and np.all(np.linalg.eigvalsh(inertias)>0)
layers=sorted({x['layer'] for p in a['prims'] for v in p['attributes'].values() for x in v['property_stack']})
rigid=[];drives=[]
for p in a['prims']:
    attrs=p['attributes']
    if 'physics:diagonalInertia' in attrs and 'physics:mass' in attrs:
        di=np.asarray(attrs['physics:diagonalInertia']['composed_value'])
        mass=attrs['physics:mass']['composed_value']
        if np.all(di>0) and mass>0:
            candidates=[j for j,m in enumerate(masses) if np.isclose(m,mass,rtol=1e-5) and np.allclose(np.diag(inertias[j]),di,rtol=1e-5,atol=1e-14)]
            assert candidates
            rigid.append({'path':p['path'],'mass_kg':mass,'diagonal_inertia_kg_m2':di.tolist(),
                          'matching_tensor_rows':candidates,'principal_radii_of_gyration_m':np.sqrt(di/mass).tolist(),
                          'source':attrs['physics:diagonalInertia']['property_stack'][0]['layer']})
    if 'drive:angular:physics:stiffness' in attrs:
        drives.append({'path':p['path'],'stiffness_usd':attrs['drive:angular:physics:stiffness']['composed_value'],
                       'damping_usd':attrs['drive:angular:physics:damping']['composed_value'],
                       'source':attrs['drive:angular:physics:stiffness']['property_stack'][0]['layer']})
assert len(rigid)==11 and len(drives)==7
audit={'script_hash_matches':True,'property_stack_successes':135,'units_m_kg':[1.,1.],
       'source_layers':layers,'rigid_bodies_with_explicit_positive_inertia':rigid,'angular_drives':drives,
       'runtime_tensor_link_order_verified':False,'mapping_note':'Rows matched by mass AND inertia signatures; identical fingers remain ambiguous.',
       'root_cause_proven':False}
(out/'asset_audit_review.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
table='\n'.join(f"|{x['path'].rsplit('/',1)[-1]}|{x['mass_kg']:.6f}|{min(x['diagonal_inertia_kg_m2']):.3e} … {max(x['diagonal_inertia_kg_m2']):.3e}|" for x in rigid)
(out/'pilot_review.md').write_text(f'''# Franka资产来源与有效惯量审查（2026-10-26）

审计完成，135项属性来源成功、0项失败；运行脚本哈希匹配。此轮仅初始化，没有执行翻腕路径或折叠。

stage metersPerUnit=1，kilogramsPerUnit=1，根和已导出link缩放均为1。七个臂关节USD stiffness=1e7、damping=1e5、maxForce=1e5；来源均为加载的Isaac/4.0/Isaac/Robots/Franka/franka.usd引用层，未发现实验代码覆盖这些字段。有效增益kp约5.73e8、kd约5.73e6，与先前记录一致。

小惯量也来自同一资产引用层，实时PhysX get_inertias/get_masses读回成功，质量和惯量联合特征可与USD匹配。未导出显式link名称顺序；两根手指特征相同，不能唯一映射，故不将数组行号当成已验证link顺序。

|刚体|质量 kg|显式主惯量范围 kg·m²|
|---|---:|---:|
{table}

12个实时惯量矩阵均为正定。上述11个刚体的主惯量确实很小，另一个无非零显式惯量的link由引擎提供约4e-4对角值。小惯量的质量回转半径仅亚毫米到约1毫米，与米制机器人几何构成值得审查的尺度差异；这不是数学上不可能的证明，也不能独立确认根因。场景单位为米/千克，未发现简单根节点缩放错误证据。

下一步准备v10，保留v9 velocity iterations=0、position=64、质量、中心、增益和全部控制逻辑，仅在首次reset前将这11个正显式惯量覆盖为(0,0,0)，请求引擎使用碰撞几何计算惯量。依据USD MassAPI，零对角惯量被忽略；这不是把实际刚体惯量置零。初始化后必须读回有效惯量为正且与基线有变化、质量与增益保持一致，才执行原路径。保留全部读回，无法确认则停止，不放宽收敛门限。

自动几何惯量仍不是机器人实物标定；COM/主轴等其他已声明属性保持不变。不得把此候选直接当成Backend永久修复或Day4正式成功。

依据：https://openusd.org/release/api/class_usd_physics_mass_a_p_i.html （GetDiagonalInertiaAttr）
''',encoding='utf-8')

source=(root/'day4-wrist-ik-execution-v9.py').read_text(encoding='utf-8')
source=source.replace('ik-tail-execution-v9-pre-reset-velocity-zero','ik-tail-execution-v10-geometry-inertia')
expected={x['path']:x for x in rigid}
helper='\nEXPECTED_INERTIA_BODIES='+repr(expected)+'\nBASELINE_EFFECTIVE_MASSES='+repr(masses.tolist())+'\nBASELINE_EFFECTIVE_INERTIAS='+repr(inertias.reshape(12,9).tolist())+'\nBASELINE_GAINS='+repr(c['runtime_getters']['controller']['get_gains']['value'])+'''

def request_geometry_inertia(env):
    from pxr import Gf
    changes=[]
    for path,expected in EXPECTED_INERTIA_BODIES.items():
        prim=env.world.stage.GetPrimAtPath(path)
        if not prim.IsValid():raise RuntimeError('Missing inertia body: '+path)
        attr=prim.GetAttribute('physics:diagonalInertia')
        mass=prim.GetAttribute('physics:mass')
        before=[float(v) for v in attr.Get()]
        if not np.allclose(before,expected['diagonal_inertia_kg_m2'],rtol=1e-5,atol=1e-14):
            raise RuntimeError('Unexpected original inertia: '+path)
        if not np.isclose(float(mass.Get()),expected['mass_kg'],rtol=1e-5):raise RuntimeError('Unexpected mass: '+path)
        if not attr.Set(Gf.Vec3f(0.,0.,0.)):raise RuntimeError('Inertia override failed: '+path)
        changes.append({'path':path,'before':before,'after':[float(v) for v in attr.Get()],
                        'mass_before_and_after':float(mass.Get())})
    result['inertia_overrides']=changes
    (out/'inertia_overrides.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')

def verify_effective_inertia():
    raw=robot._robot._articulation_view._physics_view
    masses=array(raw.get_masses()).copy()
    inertia=array(raw.get_inertias()).copy()
    gains=audit_value(robot._articulation_controller.get_gains())
    record={'masses':masses.tolist(),'inertias':inertia.tolist(),'gains':gains}
    result['effective_inertia_verification']=record
    (out/'effective_inertia.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    if masses.shape!=(1,12) or inertia.shape!=(1,12,9):raise RuntimeError('Unexpected tensor shapes')
    if not np.allclose(masses[0],BASELINE_EFFECTIVE_MASSES,rtol=1e-5,atol=1e-7):raise RuntimeError('Mass changed unexpectedly')
    if gains!=BASELINE_GAINS:raise RuntimeError('Drive gains changed unexpectedly')
    if not np.isfinite(inertia).all() or not np.all(np.linalg.eigvalsh(inertia.reshape(12,3,3))>0):
        raise RuntimeError('Effective inertia is not finite positive definite')
    if np.allclose(inertia[0],BASELINE_EFFECTIVE_INERTIAS,rtol=1e-4,atol=1e-14):
        raise RuntimeError('Effective inertia unchanged; aborting path')
    record['verified']=True
    (out/'effective_inertia.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('GEOMETRY_INERTIA_VERIFIED_MASSES_GAINS_UNCHANGED',flush=True)

'''
source=source.replace('def start_with_pre_reset_velocity_zero():',helper+'def start_with_pre_reset_velocity_zero():')
needle='        value=original_reset(env,*args,**kwargs)'
assert source.count(needle)==1
source=source.replace(needle,'        request_geometry_inertia(env)\n'+needle)
needle='    start_with_pre_reset_velocity_zero();robot=b._env.robots[0]'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n    verify_effective_inertia()')
ast.parse(source,feature_version=(3,10))
before=ast.parse((root/'day4-wrist-ik-execution-v9.py').read_text(encoding='utf-8'));after=ast.parse(source)
for name in ('drive','drive_ik','submit_joint_targets','probe_step'):
    assert ast.dump(next(x for x in before.body if isinstance(x,ast.FunctionDef) and x.name==name))==ast.dump(next(x for x in after.body if isinstance(x,ast.FunctionDef) and x.name==name))
(root/'day4-wrist-ik-execution-v10.py').write_text(source,encoding='utf-8',newline='\n')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['day4-wrist-ik-execution-v10.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'wrist-ik-execution-v10-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
runner=(root/'run-wrist-ik-execution-v9.sh').read_text(encoding='utf-8').replace('v9','v10')
(root/'run-wrist-ik-execution-v10.sh').write_text(runner,encoding='utf-8',newline='\n')
print('ASSET_AUDIT_REVIEW_OK; V10_SYNTAX_AND_CONTROL_AST_OK; NOT_RUN_ON_GPU')
