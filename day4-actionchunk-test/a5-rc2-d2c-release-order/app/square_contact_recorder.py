"""Read-only robot rigid-body contact diagnostics; no collision edits."""
import json
from pathlib import Path

class ContactRecorder:
    def __init__(self,world,out,phase):
        from pxr import PhysxSchema,UsdPhysics,PhysicsSchemaTools
        from omni.physx import get_physx_simulation_interface
        self.world=world;self.out=Path(out);self.phase=phase
        self.meta={'bodies':[],'callback_count':0,'event_count':0,'errors':[],
                   'subscription_created':False,'scope':'Robot rigid contacts only; not cloth particle contact certification'}
        self.path=self.out/'contacts.jsonl';self.path.touch()
        for prim in world.stage.Traverse():
            if str(prim.GetPath()).startswith('/World/Franka/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
                api=PhysxSchema.PhysxContactReportAPI.Apply(prim)
                attr=api.CreateThresholdAttr(0.0)
                if float(attr.Get())!=0.:raise RuntimeError('Contact report threshold mismatch')
                self.meta['bodies'].append(str(prim.GetPath()))
        if not self.meta['bodies']:raise RuntimeError('No robot contact-report bodies')
        def callback(headers,data):
            self.meta['callback_count']+=1
            try:
                for h in headers:
                    actors=[str(PhysicsSchemaTools.intToSdfPath(h.actor0)),str(PhysicsSchemaTools.intToSdfPath(h.actor1))]
                    if not any(a.startswith('/World/Franka/') for a in actors):continue
                    points=[]
                    for j in range(h.contact_data_offset,h.contact_data_offset+h.num_contact_data):
                        c=data[j];points.append({'position':[float(v) for v in c.position],
                            'normal':[float(v) for v in c.normal],'impulse':[float(v) for v in c.impulse]})
                    row={'step':int(world.current_time_step_index),'phase':phase(),'type':str(h.type),'actors':actors,
                         'colliders':[str(PhysicsSchemaTools.intToSdfPath(h.collider0)),str(PhysicsSchemaTools.intToSdfPath(h.collider1))],
                         'contacts':points}
                    with self.path.open('a',encoding='utf8') as f:f.write(json.dumps(row)+'\n')
                    self.meta['event_count']+=1
            except Exception as exc:
                if len(self.meta['errors'])<20:self.meta['errors'].append(repr(exc))
        self.callback=callback
        self.subscription=get_physx_simulation_interface().subscribe_contact_report_events(callback)
        self.meta['subscription_created']=self.subscription is not None
        if not self.meta['subscription_created']:raise RuntimeError('No contact subscription')
    def save(self):
        m=self.meta
        m['diagnosis']=('recording_failed' if m['errors'] else
                        'contact_events_recorded_review_timing' if m['event_count'] else
                        'configured_no_events_channel_not_independently_validated')
        (self.out/'contact_report.json').write_text(json.dumps(m,indent=2),encoding='utf8')
        return m
