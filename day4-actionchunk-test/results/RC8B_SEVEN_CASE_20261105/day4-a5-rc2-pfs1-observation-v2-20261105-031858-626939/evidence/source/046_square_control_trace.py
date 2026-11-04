"""Read-only command/state tracing; no additional physics steps or control writes."""
import json
import traceback
from pathlib import Path
import numpy as np

def numeric(value):
    if hasattr(value, 'detach'):value=value.detach().cpu().numpy()
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)

def action_dict(action):
    return {k:getattr(action,k,None) for k in
            ('joint_positions','joint_velocities','joint_efforts','joint_indices')}

class ControlTrace:
    def __init__(self,robot,world,out,phase):
        self.robot=robot;self.world=world;self.phase=phase
        self.file=(Path(out)/'control_trace.jsonl').open('w',encoding='utf-8')
        self.patches=[];self.sequence=0
        self.wrap(robot._controller,'forward',True)
        self.wrap(robot._articulation_controller,'apply_action')
        # Python entrypoints only: native USD/PhysX calls may bypass these hooks.
        for name in ('set_world_pose','set_local_pose','set_joint_positions'):
            if callable(getattr(robot._robot,name,None)):self.wrap(robot._robot,name)
        self.emit('trace_setup',{'scope':'Python controller calls and step state; native pose setters not fully covered'})

    def emit(self,event,data):
        self.sequence+=1
        row={'sequence':self.sequence,'physics_step':int(self.world.current_time_step_index),
             'phase':self.phase(),'event':event,**data}
        self.file.write(json.dumps(row,default=numeric)+'\n');self.file.flush()

    def wrap(self,obj,name,output_action=False):
        original=getattr(obj,name)
        def observed(*args,**kwargs):
            stack=[{'file':f.filename,'line':f.lineno,'function':f.name}
                   for f in traceback.extract_stack(limit=8)[:-1]]
            data={'method':name,'caller':stack}
            if name=='apply_action':
                a=args[0] if args else next(iter(kwargs.values()))
                data['submitted_action']=action_dict(a)
            else:data.update(args=args,kwargs=kwargs)
            self.emit('call',data)
            result=original(*args,**kwargs)
            if output_action:self.emit('controller_output',{'action':action_dict(result)})
            return result
        self.patches.append((obj,name,original))
        setattr(obj,name,observed)

    def state(self,when,logical_step):
        r=self.robot;ee,q=r.get_cur_ee_pos()
        self.emit('state',{'when':when,'step':int(logical_step),
            'joint_positions':r._robot.get_joint_positions(),
            'joint_velocities':r._robot.get_joint_velocities(),
            'ee_position':ee,'ee_quaternion_wxyz':q,
            'applied_action':action_dict(r._articulation_controller.get_applied_action())})

    def close(self):
        for obj,name,original in reversed(self.patches):setattr(obj,name,original)
        self.patches=[]
        self.file.close()
