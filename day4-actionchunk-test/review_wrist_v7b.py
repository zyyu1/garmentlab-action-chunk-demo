"""Audit runtime evidence and prepare one targeted TGS velocity-iteration control."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
out=root/'results/day4-wrist-ik-execution-20261026-193733-229449'
r=json.loads((out/'result.json').read_text())
config=json.loads((out/'runtime_config.json').read_text())
states=[json.loads(x) for x in (out/'step_states.jsonl').read_text().splitlines()]
assert r['script_sha256']==hashlib.sha256((root/'day4-wrist-ik-execution-v7b.py').read_bytes()).hexdigest()
dt=config['runtime_getters']['world']['get_physics_dt']['value']
assert np.allclose([x['after']['current_time']-x['before']['current_time'] for x in states],dt,rtol=1e-6)
assert all(states[i]['after']==states[i+1]['before'] for i in range(len(states)-1))
v6=json.loads((root/'results/day4-wrist-ik-execution-20261026-192104-045218/result.json').read_text())
assert r['targets']==v6['targets']
for key,record in config['source_hashes'].items():
    assert record['sha256']==hashlib.sha256((out/(key+'_runtime.py')).read_bytes()).hexdigest()
assert len(states)==sum(t.get('steps',len(t.get('trace',[]))) for t in r['targets'])
tail=states[-60:]
q=np.asarray([x['after']['position'] for x in tail])
v=np.asarray([x['after']['velocity'] for x in tail])
fd=np.asarray([(np.asarray(x['after']['position'])-x['before']['position'])/dt for x in tail])
time=np.asarray([x['after']['current_time'] for x in tail]);time-=time[0]
fig,axs=plt.subplots(2,1,figsize=(10,7),sharex=True)
for ax,j in zip(axs,[4,6]):
    ax.plot(time,v[:,j],label='PhysX reported velocity')
    ax.plot(time,fd[:,j],label='Same-step position difference / measured dt')
    ax.set_title(f'panda_joint{j+1}');ax.set_ylabel('rad/s');ax.legend();ax.grid(alpha=.3)
axs[-1].set_xlabel('Time since start of final 60 samples (s)')
fig.suptitle('v7b: runtime dt = 1/60 s; sampled-state continuity verified')
fig.tight_layout();fig.savefig(out/'runtime_velocity_consistency.png',dpi=170);plt.close(fig)
audit={'script_hash_matches':True,'runtime_source_hashes_match':True,'targets_exactly_match_v6':True,
       'state_samples':len(states),'all_pre_post_times_match_dt':True,'adjacent_states_exactly_continuous':True,
       'physics_dt_seconds':dt,'position_iterations':64,'velocity_iterations':64,
       'joint5_last60_max_difference_speed_rad_s':float(abs(fd[:,4]).max()),
       'joint7_last60_max_difference_speed_rad_s':float(abs(fd[:,6]).max()),
       'reported_velocity_absence_of_rotation_not_proven':True}
(out/'v7b_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
(out/'pilot_review.md').write_text('''# v7b 运行配置与状态审查（2026-10-26）

运行脚本哈希、3份导出源码哈希通过；全部目标/轨迹与v6完全相同。1086条pre/post记录连续一致，每步实际时间增量匹配1/60秒；记录条数等于目标累计步数。位置与速度getter均调用实时PhysX张量接口并克隆；没有发现使用静态USD位置代替运动状态的证据，但这不等于SDK内部无问题。

机器人TGS position/velocity iterations=64/64，self-collisions=0。七个臂关节有效kp=572957824、kd=5729578、max effort=100000；组合USD角驱动stiffness=10000000、damping=100000。两套数值表示不同，不能直接把角度换算差异当成配置错误。部分link authored惯量约1e-6，未验证有效惯量/资产长度单位，不据此认定资产错误。dof_properties读取CUDA转换错误已显式记录，不影响已成功读取的字段。

最后60帧固定目标下，joint5位置差分速度约±0.0267 rad/s，而报告速度4.08–4.72 rad/s；joint7位置差分近零而报告速度2.81–3.63 rad/s。差异在实际dt下仍存在，但离散位置差分不解析步内求解过程，不足以断言哪个接口错误。

NVIDIA Isaac Sim 4.1官方物理限制说明：TGS超过4次速度迭代不再静默转为位置迭代，建议尝试零或很少速度迭代。这与本次64次配置及启动警告直接相关，作为下一次单变量实验依据，而非已确定根因：
https://docs.isaacsim.omniverse.nvidia.com/4.1.0/simulation_fundamentals.html

v8保留v7b全部配置和控制，完成第27点原插值后、开始保持前，仅通过运行时API将articulation velocity iteration count从64设为0。保存干预前后状态、迭代数、gains和dt，断言无仿真步进和状态瞬移，继续原速度门限与240步预算。该干预不是永久Backend修复；前缀应可精确比较，但干预后的执行步数和重新求出的后续IK允许改变，应明确记录。高增益、质量、材料、position iterations、轨迹及门限不变。不用大量配置扫描替代Day4主线。

如果通过，再核对28–30点及整条路径，再处理公共接口和带布料折叠；空载通过仍不等于Day4完成。如果失败，根据新轨迹评估此假设，不立即扩展参数扫描。

![运行状态核对](runtime_velocity_consistency.png)
''',encoding='utf-8')

source=(root/'day4-wrist-ik-execution-v7b.py').read_text(encoding='utf-8')
source=source.replace('ik-tail-execution-v7b-state-config-audit','ik-tail-execution-v8-tgs-velocity-zero')
helper='''
def apply_velocity_iteration_control():
    before=sampled_state()
    pos_count=int(robot._robot.get_solver_position_iteration_count())
    vel_count=int(robot._robot.get_solver_velocity_iteration_count())
    gains_before=audit_value(robot._articulation_controller.get_gains())
    dt_before=float(b._env.world.get_physics_dt())
    record={'phase':probe_phase,'probe_step':probe_step_count,'before':before,
            'before_position_iterations':pos_count,'before_velocity_iterations':vel_count,
            'gains_before':gains_before,'dt_before':dt_before}
    result['velocity_iteration_intervention']=record
    if (pos_count,vel_count)!=(64,64):raise RuntimeError('Unexpected solver counts before intervention')
    robot._robot.set_solver_velocity_iteration_count(0)
    after=sampled_state()
    record.update(after=after,after_position_iterations=int(robot._robot.get_solver_position_iteration_count()),
        after_velocity_iterations=int(robot._robot.get_solver_velocity_iteration_count()),
        gains_after=audit_value(robot._articulation_controller.get_gains()),dt_after=float(b._env.world.get_physics_dt()))
    if after!=before:raise RuntimeError('State changed during no-step solver configuration')
    if record['after_position_iterations']!=64 or record['after_velocity_iterations']!=0:
        raise RuntimeError('Solver configuration did not read back as requested')
    if record['gains_after']!=gains_before or record['dt_after']!=dt_before:
        raise RuntimeError('Unrequested gain or dt change')
    (out/'velocity_iteration_intervention.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    initial=out/'runtime_config.json'
    if initial.exists():initial.rename(out/'runtime_config_before_intervention.json')
    dump_runtime_audit()
    print('TGS_VELOCITY_ITERATION_INTERVENTION_OK 64 -> 0; POSITION_ITERATIONS 64',flush=True)

'''
source=source.replace('def drive_ik(target, quaternion, label):',helper+'def drive_ik(target, quaternion, label):')
needle='    full[ids]=goal;consecutive=0'
assert source.count(needle)==1
source=source.replace(needle,"    if label=='opposite_delayed_pitch_27':\n        apply_velocity_iteration_control()\n"+needle)
ast.parse(source,feature_version=(3,10))
old=ast.parse((root/'day4-wrist-ik-execution-v7b.py').read_text(encoding='utf-8'));new=ast.parse(source)
for name in ('drive','submit_joint_targets','probe_step','install_contact_reporting'):
    assert ast.dump(next(x for x in old.body if isinstance(x,ast.FunctionDef) and x.name==name))==ast.dump(next(x for x in new.body if isinstance(x,ast.FunctionDef) and x.name==name))
old_ik=next(x for x in old.body if isinstance(x,ast.FunctionDef) and x.name=='drive_ik')
new_ik=next(x for x in new.body if isinstance(x,ast.FunctionDef) and x.name=='drive_ik')
new_ik.body=[x for x in new_ik.body if not(isinstance(x,ast.If) and "apply_velocity_iteration_control" in ast.unparse(x))]
assert ast.dump(old_ik)==ast.dump(new_ik)
(root/'day4-wrist-ik-execution-v8.py').write_text(source,encoding='utf-8',newline='\n')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
          ['day4-wrist-ik-execution-v8.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'wrist-ik-execution-v8-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
runner=(root/'run-wrist-ik-execution-v7b.sh').read_text(encoding='utf-8').replace('v7b','v8')
(root/'run-wrist-ik-execution-v8.sh').write_text(runner,encoding='utf-8',newline='\n')
print('V7B_AUDIT_OK; V8_SINGLE_INTERVENTION_AST_OK; V8_NOT_RUN')
