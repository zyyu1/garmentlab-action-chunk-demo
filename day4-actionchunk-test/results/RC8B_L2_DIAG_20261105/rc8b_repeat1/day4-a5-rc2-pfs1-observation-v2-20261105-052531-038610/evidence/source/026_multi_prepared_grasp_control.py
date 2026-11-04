"""Three precreated one-use slots, one active at a time. Development only.

Import after SimulationApp. No USD paths or particle indices enter public actions.
No episode reset or reuse of a previously released slot is claimed.
"""
import json
import os
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from pxr import UsdGeom, Gf, PhysxSchema, Vt
from Env.env.Control import AttachmentBlock
from hem_prepared_grasp_control import HemPreparedGraspControl
from multi_grasp_geometry import select_regions, choose_unused_region
from square_contact_reporting import (setup_early_contact_reporting,
    verify_early_contact_reporting, create_block_contact_force_view)

class SlotBlock(AttachmentBlock):
    def __init__(self,*args,slot_name,**kwargs):
        self.slot_name=slot_name
        super().__init__(*args,**kwargs)

    def create(self):
        self.cube_name='prepared_'+self.slot_name
        view=super().create()
        self.stage.DefinePrim('/World/AttachmentConstraints','Scope')
        self.attachment_path='/World/AttachmentConstraints/multi_'+self.slot_name
        if self.stage.GetPrimAtPath(self.attachment_path).IsValid():raise RuntimeError('Duplicate slot path')
        return view

class PreparedRegion(HemPreparedGraspControl):
    def __init__(self,env,label,pick,rest_local,rest_world):
        self.original=env.control;self.env=env;self.world=env.world
        self.robot=env.robots[0];self.garment=env.garment[0]
        self.label=label;self.pick_index=pick;self.holding=False;self.used=False
        self.constraint_removed=False;self.fold_angle=None
        self.fold_robot_rotation=None;self.fold_block_rotation=None
        self.attachlist=[None]
        self.local_offset=self.original.grasp_offset.detach().cpu().numpy().astype(float)
        self.rest_local=rest_local.copy()
        self.tracked=np.flatnonzero(np.linalg.norm(rest_world-rest_world[pick],axis=1)<.02)
        self.block=SlotBlock(self.world,self.robot,rest_world[pick],slot_name=label,
                             collision_group=self.original.collectionAPI_attach)
        self.block.attach(self.garment)
        stage=self.world.stage;prim=stage.GetPrimAtPath(self.block.attachment_path)
        overlap=float(os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP','nan'))
        if not np.isclose(overlap,.005):raise RuntimeError('Require 5 mm overlap')
        attr=prim.GetAttribute('physxAutoAttachment:deformableVertexOverlapOffset')
        if not attr.Set(overlap):raise RuntimeError('Attachment overlap edit failed')
        self.enabled=PhysxSchema.PhysxPhysicsAttachment.Get(stage,self.block.attachment_path).CreateAttachmentEnabledAttr()
        if not self.enabled.Set(False):raise RuntimeError('Could not pre-disable slot')
        self.anchor_ids=None;self.alignment_record=None;self.activation_record=None;self.output_directory=None
        self.max_single_anchor_gap_m=0.;self.reuse_count=0

    def initialize(self):
        super().initialize()
        prim=self.world.stage.GetPrimAtPath(self.block.attachment_path)
        p0=np.asarray(prim.GetAttribute('points0').Get(),dtype=float)
        p1=np.asarray(prim.GetAttribute('points1').Get(),dtype=float)
        if p0.ndim!=2 or p0.shape[1]!=3 or not len(p0) or p1.shape!=p0.shape:
            raise RuntimeError('Slot has no paired anchors after reset: '+self.label)
        sq=((p0[:,None,:]-self.rest_local[None,:,:])**2).sum(axis=2)
        ids=sq.argmin(axis=1)
        if len(np.unique(ids))!=len(ids) or np.max(sq[np.arange(len(ids)),ids])>1e-12:
            raise RuntimeError('Slot points0 cannot be mapped to unique rest vertices')
        self.anchor_ids=ids;self.original_points0=p0.copy()
        if self.attachment_enabled():raise RuntimeError('Slot unexpectedly enabled at startup')

    def align_disabled(self):
        if self.holding or self.attachment_enabled():raise RuntimeError('Alignment requires disabled slot')
        prim=self.world.stage.GetPrimAtPath(self.block.attachment_path)
        vertices=self.vertices();before_step=self.world.current_time_step_index
        pos,q=self.block.move_block_controller.get_world_poses()
        pos=pos.detach().cpu().numpy().reshape(-1,3)[0]
        q=q.detach().cpu().numpy().reshape(-1,4)[0]
        scale=np.asarray(self.world.stage.GetPrimAtPath(self.block.block_path).GetAttribute('xformOp:scale').Get(),dtype=float)
        if scale.shape!=(3,) or np.any(scale<=0):raise RuntimeError('Invalid block scale')
        desired=Rotation.from_quat(q[[1,2,3,0]]).inv().apply(vertices[self.anchor_ids]-pos)/scale
        attr=prim.GetAttribute('points1')
        if not attr.Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,row)) for row in desired])):
            raise RuntimeError('Slot points1 alignment failed')
        readback=np.asarray(attr.Get(),dtype=float)
        if not np.array_equal(readback,desired.astype(np.float32).astype(float)):
            raise RuntimeError('Slot points1 alignment readback mismatch')
        if not np.array_equal(np.asarray(prim.GetAttribute('points0').Get()),self.original_points0):
            raise RuntimeError('Slot points0 changed')
        if self.world.current_time_step_index!=before_step or not np.array_equal(self.vertices(),vertices):
            raise RuntimeError('Physics advanced during slot alignment')
        self.alignment_record={'slot':self.label,'step':int(before_step),'anchor_count':len(self.anchor_ids),
                               'anchor_ids':self.anchor_ids.tolist(),'points1_readback':readback.tolist()}

    def _drive(self,target,ori,follow=False,limit=1000):
        value=super()._drive(target,ori,follow,limit)
        if follow and not self.holding and not self.attachment_enabled():self.align_disabled()
        return value

    def _tick(self,target,ori,follow=False):
        first=self.attachment_enabled() and self.activation_record is None
        if first:
            if self.alignment_record is None:raise RuntimeError('Slot enabled before anchor alignment')
            before=self.vertices();step=int(self.world.current_time_step_index)
        value=super()._tick(target,ori,follow)
        if first:
            after=self.vertices();delta=np.linalg.norm(after-before,axis=1)
            prim=self.world.stage.GetPrimAtPath(self.block.attachment_path)
            self.activation_record={'slot':self.label,'step_before':step,'step_after':int(self.world.current_time_step_index),
                                    'max_displacement_m':float(delta.max()),
                                    'tracked_mean_displacement_m':float(delta[self.tracked].mean()),
                                    'count_over_5mm':int((delta>.005).sum())}
            if self.output_directory is not None:
                np.savez_compressed(Path(self.output_directory)/('activation_'+self.label+'.npz'),
                    before=before,after=after,anchor_ids=self.anchor_ids,tracked=self.tracked,
                    points0=np.asarray(prim.GetAttribute('points0').Get()),points1=np.asarray(prim.GetAttribute('points1').Get()))
        return value

    def ungrasp(self,flag,keep=None):
        if list(flag)!=[False] or (keep is not None and any(keep)):
            raise ValueError('Expected public OPEN/release')
        self.block.set_velocities(np.zeros(6))
        if not self.enabled.Set(False):raise RuntimeError('Slot release failed')
        self.holding=False;self.attachlist[0]=None
        # Keep constraint and block alive; no scene topology mutation during rollout.
        self.robot.open()

    def enable_regrasp(self):
        """Allow this released slot to be selected again after a safe release."""
        if self.holding or self.attachment_enabled():
            raise RuntimeError('Re-grasp requires a released, disabled slot: '+self.label)
        self.used=False;self.alignment_record=None;self.activation_record=None
        self.max_single_anchor_gap_m=0.;self.reuse_count+=1

    def prepare_episode_reset(self):
        """Force a released/disabled state before the scene is reset."""
        if self.holding or self.attachment_enabled():
            if self.enabled.Get() is True and not self.enabled.Set(False):
                raise RuntimeError('Episode reset could not disable '+self.label)
        self.block.set_velocities(np.zeros(6))
        self.holding=False;self.used=False;self.attachlist[0]=None
        self.alignment_record=None;self.activation_record=None
        self.max_single_anchor_gap_m=0.;self.reuse_count=0

    def after_scene_reset(self):
        """Re-validate the precreated block/constraint after world.reset()."""
        view=self.block.move_block_controller
        if view._physics_view is not None and not view.is_physics_handle_valid():
            view._physics_view=None
        self.block.initialize_physics()
        self.block.set_velocities(np.zeros(6))
        if self.attachment_enabled():
            raise RuntimeError('Slot enabled after scene reset: '+self.label)
        prim=self.world.stage.GetPrimAtPath(self.block.attachment_path)
        if not prim.IsValid() or self.anchor_ids is None or self.original_points0 is None:
            raise RuntimeError('Precreated slot missing after scene reset: '+self.label)
        p0=np.asarray(prim.GetAttribute('points0').Get(),dtype=float)
        if not np.array_equal(p0,self.original_points0):
            raise RuntimeError('Slot points0 changed after scene reset: '+self.label)

class MultiPreparedGraspControl:
    enable_early_contact_reporting=False
    def __init__(self,env):
        if len(env.robots)!=1 or len(env.garment)!=1:raise ValueError('One robot and garment required')
        self.original=env.control;self.env=env;self.world=env.world;self.robot=env.robots[0]
        self.garment=env.garment[0];self.events=[];self.active_index=0
        mesh=UsdGeom.Mesh(self.world.stage.GetPrimAtPath(self.garment.garment_mesh_prim_path))
        local=np.asarray(mesh.GetPointsAttr().Get(),dtype=float)
        transform=UsdGeom.XformCache().GetLocalToWorldTransform(mesh.GetPrim())
        world=np.asarray([tuple(transform.Transform(Gf.Vec3d(*map(float,row)))) for row in local])
        self.regions=select_regions(world)
        self.slots=[PreparedRegion(env,label,pick,local,world) for label,pick in self.regions]
        for s in self.slots:s.output_directory=getattr(type(self),'output_directory',None)
        paths=[s.block.attachment_path for s in self.slots]+[s.block.block_path for s in self.slots]
        if len(set(paths))!=6:raise RuntimeError('Slot scene paths are not distinct')
        self.rest_world=world
        self.contact_report_early=None;self.contact_report_after_reset=None;self.contact_force_view=None
        if getattr(type(self),'enable_early_contact_reporting',False):
            stage=self.world.stage
            try:
                self.contact_report_early=setup_early_contact_reporting(
                    stage,[s.block.block_path for s in self.slots])
            except Exception as exc:
                self.contact_report_early={'error':repr(exc),'blocks':[],'robot_bodies':[],
                                           'ground_colliders':[],'applied_before_reset':False}
            view_info=create_block_contact_force_view(self.world)
            self.contact_force_view=view_info.pop('view',None)
            self.contact_report_early['force_view']=view_info
            output=getattr(type(self),'output_directory',None)
            if output is not None:
                (Path(output)/'contact_report_setup_early.json').write_text(
                    json.dumps(self.contact_report_early,indent=2,default=str),encoding='utf-8')

    def __getattr__(self,name):return getattr(self.original,name)
    @property
    def active(self):return self.slots[self.active_index]
    @property
    def holding(self):return any(s.holding for s in self.slots)
    @property
    def attachlist(self):return [self.active.block if self.holding else None]
    def attachment_enabled(self):return any(s.attachment_enabled() for s in self.slots)
    def vertices(self):return self.active.vertices()
    def status(self):
        return [{'slot':s.label,'pick_index':s.pick_index,'used':s.used,'holding':s.holding,
                 'enabled':s.attachment_enabled(),'constraint_exists':self.world.stage.GetPrimAtPath(s.block.attachment_path).IsValid()}
                for s in self.slots]
    def assert_exclusive(self):
        enabled=[i for i,s in enumerate(self.slots) if s.attachment_enabled()]
        held=[i for i,s in enumerate(self.slots) if s.holding]
        if enabled!=held or (held and held!=[self.active_index]):raise RuntimeError('Prepared slot state mismatch')
        if len(enabled)>1:raise RuntimeError('Multiple attachments active')
        if not all(x['constraint_exists'] for x in self.status()):raise RuntimeError('Precreated constraint disappeared')
        for s in self.slots:
            if s.anchor_ids is None:continue
            prim=self.world.stage.GetPrimAtPath(s.block.attachment_path)
            if not np.array_equal(np.asarray(prim.GetAttribute('points0').Get()),s.original_points0):
                raise RuntimeError('Precreated slot points0 changed')
            if s.alignment_record is not None and not np.array_equal(
                    np.asarray(prim.GetAttribute('points1').Get()),np.asarray(s.alignment_record['points1_readback'])):
                raise RuntimeError('Aligned slot points1 changed')
    def verify_contact_reporting(self):
        if getattr(type(self),'enable_early_contact_reporting',False):
            self.contact_report_after_reset=verify_early_contact_reporting(
                self.world.stage,self.contact_report_early)
            view_info={'valid':False,'error':'no force view'}
            if self.contact_force_view is not None:
                try:
                    valid=bool(self.contact_force_view.is_physics_handle_valid())
                    if not valid:self.contact_force_view.initialize()
                    valid=bool(self.contact_force_view.is_physics_handle_valid())
                    view_info={'valid':valid,'prim_paths':list(self.contact_force_view.prim_paths),
                               'count':int(self.contact_force_view.count),'error':None}
                except Exception as exc:
                    view_info={'valid':False,'error':repr(exc)}
            self.contact_report_after_reset['force_view']=view_info
            output=getattr(type(self),'output_directory',None)
            if output is not None:
                (Path(output)/'contact_report_after_reset.json').write_text(
                    json.dumps(self.contact_report_after_reset,indent=2,default=str),encoding='utf-8')
            print('CONTACT_REPORT_SETUP_AFTER_RESET',
                  json.dumps({'blocks_ok':self.contact_report_after_reset.get('blocks_ok'),
                              'robot_ok':self.contact_report_after_reset.get('robot_ok'),
                              'force_view':view_info},default=str),flush=True)
        return self.contact_report_after_reset

    def initialize(self):
        for s in self.slots:
            s.initialize()
            if np.min(np.linalg.norm(self.rest_world[s.anchor_ids]-self.rest_world[s.pick_index],axis=1))>.03:
                raise RuntimeError('Generated anchors outside selected region')
        self.assert_exclusive()
        self.verify_contact_reporting()
    def robot_goto_position(self,pos,ori,flag,max_limit=1000):
        self.assert_exclusive();self.active.robot_goto_position(pos,ori,flag,max_limit);self.assert_exclusive()
    def move(self,pos,ori,flag,max_limit=1000):self.robot_goto_position(pos,ori,flag,max_limit)
    def grasp(self,pos,ori,flag,assign_garment=None):
        self.assert_exclusive()
        if self.holding:raise RuntimeError('Release before another CLOSE')
        if len(pos)!=1 or len(ori)!=1 or list(flag)!=[True]:raise ValueError('Expected one active robot')
        self.active_index=choose_unused_region(self.vertices(),self.regions,[s.used for s in self.slots],pos[0])
        try:self.active.grasp(pos,ori,flag,assign_garment)
        finally:
            self.events.append({'event':'grasp_attempt','slot':self.active.label,'status':self.status(),
                                'alignment':self.active.alignment_record,'activation':self.active.activation_record})
        self.assert_exclusive()
    def ungrasp(self,flag,keep=None):
        self.assert_exclusive()
        if not self.holding:raise RuntimeError('No active grasp to release')
        self.active.ungrasp(flag,keep);self.assert_exclusive()
        self.events.append({'event':'release','slot':self.active.label,'status':self.status()})
    def prepare_episode_reset(self):
        for s in self.slots:s.prepare_episode_reset()
        self.active_index=0;self.events=[]
        if hasattr(self,'motion_records'):self.motion_records=[]

    def after_scene_reset(self):
        for s in self.slots:s.after_scene_reset()
        self.active_index=0

    def enable_regrasp(self):
        self.active.enable_regrasp()

    def robot_reset(self):
        if self.holding:raise RuntimeError('Release first; episode reset is not implemented')
        self.robot.open()
