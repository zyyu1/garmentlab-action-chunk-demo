"""Read-only rigid contact diagnostics for robot links and attachment blocks.

Block-ground contact is the built-in positive control: the 3 cm blocks rest on
the ground. Zero events means the channel is not validated, not that no
contact exists. Particle-cloth contacts are outside this scope.
"""
import json
from pathlib import Path

class BlockContactRecorder:
    def __init__(self,world,out,phase):
        from pxr import PhysxSchema,UsdPhysics
        from omni.physx import get_physx_simulation_interface
        self.world=world;self.out=Path(out);self.phase=phase
        self.meta={'robot_bodies':[],'attachment_bodies':[],'callback_count':0,'event_count':0,
                   'counts':{},'errors':[],'subscription_created':False,
                   'scope':'Rigid contacts for robot links and attachment blocks; cloth particle contacts not certified'}
        self.path=self.out/'block_contacts.jsonl';self.path.touch()
        def apply(prim):
            api=PhysxSchema.PhysxContactReportAPI.Apply(prim)
            attr=api.CreateThresholdAttr(0.0)
            if float(attr.Get())!=0.:raise RuntimeError('Contact report threshold mismatch')
            return str(prim.GetPath())
        for prim in world.stage.Traverse():
            path=str(prim.GetPath())
            if path.startswith('/World/Franka/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
                try:self.meta['robot_bodies'].append(apply(prim))
                except Exception as exc:self.meta['errors'].append('robot '+path+': '+repr(exc))
        for prim in world.stage.Traverse():
            path=str(prim.GetPath())
            if path.startswith('/World/Attachment/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
                try:self.meta['attachment_bodies'].append(apply(prim))
                except Exception as exc:self.meta['errors'].append('attachment '+path+': '+repr(exc))
        if not self.meta['robot_bodies']:self.meta['errors'].append('No robot contact-report bodies')
        if not self.meta['attachment_bodies']:self.meta['errors'].append('No attachment contact-report bodies')
        def classify(actors):
            robot=any(a.startswith('/World/Franka/') for a in actors)
            block=any(a.startswith('/World/Attachment/') for a in actors)
            ground=any(a.startswith('/World/defaultGroundPlane') or a.startswith('/World/Room/') for a in actors)
            if robot and block:return 'robot_block'
            if robot and ground:return 'robot_ground'
            if block and ground:return 'block_ground'
            if robot:return 'robot_other'
            if block:return 'block_other'
            return 'other'
        def callback(headers,data):
            self.meta['callback_count']+=1
            try:
                from pxr import PhysicsSchemaTools
                for h in headers:
                    actors=[str(PhysicsSchemaTools.intToSdfPath(h.actor0)),str(PhysicsSchemaTools.intToSdfPath(h.actor1))]
                    if not any(a.startswith('/World/Franka/') or a.startswith('/World/Attachment/') for a in actors):
                        continue
                    points=[]
                    for j in range(h.contact_data_offset,h.contact_data_offset+h.num_contact_data):
                        c=data[j];points.append({'position':[float(v) for v in c.position],
                            'normal':[float(v) for v in c.normal],'impulse':[float(v) for v in c.impulse]})
                    category=classify(actors)
                    row={'step':int(world.current_time_step_index),'phase':phase(),'type':str(h.type),
                         'category':category,'actors':actors,
                         'colliders':[str(PhysicsSchemaTools.intToSdfPath(h.collider0)),str(PhysicsSchemaTools.intToSdfPath(h.collider1))],
                         'contacts':points}
                    with self.path.open('a',encoding='utf8') as f:f.write(json.dumps(row)+'\n')
                    self.meta['event_count']+=1
                    self.meta['counts'][category]=self.meta['counts'].get(category,0)+1
            except Exception as exc:
                if len(self.meta['errors'])<20:self.meta['errors'].append(repr(exc))
        self.callback=callback
        self.subscription=get_physx_simulation_interface().subscribe_contact_report_events(callback)
        self.meta['subscription_created']=self.subscription is not None
        if not self.meta['subscription_created']:raise RuntimeError('No contact subscription')
    def save(self):
        m=self.meta
        m['diagnosis']=('recording_failed' if m['errors'] else
                        'contact_events_recorded_review_categories' if m['event_count'] else
                        'configured_no_events_channel_not_independently_validated')
        m['unexpected_robot_block_contacts']=int(m['counts'].get('robot_block',0))
        m['positive_control_block_ground_events']=int(m['counts'].get('block_ground',0))
        (self.out/'block_contact_report.json').write_text(json.dumps(m,indent=2),encoding='utf8')
        return m
