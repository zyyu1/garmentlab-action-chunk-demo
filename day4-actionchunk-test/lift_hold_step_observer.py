"""Read-only sampling after each explicit World.step during one aligned lift plus a fixed-target hold.

Does not sample internal PhysX substeps. Records geometric edge ratios, not
material stress. CSV rows flush each frame; raw frames save on normal/error exit.
"""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


class LiftHoldStepObserver:
    def __init__(self, backend, anchor_observer, output):
        self.b = backend
        self.observer = anchor_observer
        self.world = backend._env.world
        self.output = Path(output)/'lift_hold_trace'
        self.output.mkdir()
        self.phase = 'lift'
        self.hold_start_frame = -1
        self.expected_hold_steps = 0
        self.rows = []
        self.frames = []
        self.active = False
        self.finished = False
        self.csv_file = None
        self.original_step = None
        self.had_own_step = False
        self.edges = anchor_observer.edges.copy()
        self.rest_lengths = anchor_observer.rest_lengths.copy()
        self.ids = anchor_observer.anchor_ids.copy()
        self.edge_anchor_count = np.isin(self.edges, self.ids).sum(axis=1)
        self.local = self.edge_anchor_count > 0
        self.summary = {'capture_complete': False, 'scope': 'explicit World.step samples during lift and fixed-target hold; not internal substeps'}

    def start(self, target):
        if self.active or self.finished:
            raise RuntimeError('Lift tracing can start only once')
        self.target = np.asarray(target, dtype=float).copy()
        self.dt = float(self.world.get_physics_dt())
        if not np.isfinite(self.dt) or self.dt <= 0:
            raise RuntimeError('Invalid simulation dt')
        self.csv_file = (self.output/'steps.csv').open('w', newline='', encoding='utf-8')
        self.writer = None
        self.sample()
        self.original_step = self.world.step
        self.had_own_step = 'step' in vars(self.world)
        def observed_step(*args, **kwargs):
            value = self.original_step(*args, **kwargs)
            self.sample()
            return value
        self.world.step = observed_step
        self.active = True
        print('LIFT_HOLD_TRACE_STARTED', self.rows[0]['physics_step'], 'DT', self.dt, flush=True)

    def sample(self):
        c = self.b._env.control
        if not self.b._holding or not c.holding or not bool(c.enabled.Get()):
            raise RuntimeError('Lift sample requires a held cloth and active attachment')
        s = self.observer.live_state()
        if not np.array_equal(s['points0'], self.observer.original_points0) or not np.array_equal(s['points1'], self.observer.expected_points1):
            raise RuntimeError('Anchor arrays changed during traced lift')
        if self.rows and s['step'] != self.rows[-1]['physics_step'] + 1:
            raise RuntimeError('Non-consecutive World.step samples')
        ee, quat = c.robot.get_cur_ee_pos()
        ee, quat = np.asarray(ee, dtype=float).reshape(3), np.asarray(quat, dtype=float).reshape(4)
        if not np.isfinite(ee).all() or not np.isfinite(quat).all():
            raise RuntimeError('Nonfinite EE sample')
        if abs(np.linalg.norm(quat)-1) > 1e-4:
            raise RuntimeError('Invalid EE quaternion')
        q = s['quaternion']
        targets = Rotation.from_quat(q[[1,2,3,0]]).apply(s['points1']*s['scale']) + s['position']
        gap = np.linalg.norm(s['vertices'][self.ids]-targets, axis=1)*1000
        lengths = self.observer.edge_lengths(s['vertices'])
        ratios = lengths/self.rest_lengths
        if not self.frames:
            self.start_lengths = lengths.copy()
        ratio_to_start = lengths/self.start_lengths
        worst = int(ratios.argmax())
        local_indices = np.flatnonzero(self.local)
        local_worst = int(local_indices[np.argmax(ratios[self.local])])
        row = {'frame': len(self.rows), 'phase': self.phase, 'physics_step': s['step'],
               'elapsed_sim_seconds': len(self.rows)*self.dt,
               'world_sim_time': float(self.world.current_time),
               'tracked_mean_z_mm': float(s['vertices'][c.tracked,2].mean()*1000),
               'ee_x': float(ee[0]), 'ee_y': float(ee[1]), 'ee_z': float(ee[2]),
               'ee_target_error_mm': float(np.linalg.norm(ee-self.target)*1000),
               'block_follow_error_mm': float(np.linalg.norm(c.block_target()-s['position'])*1000),
               'paired_gap_mean_mm': float(gap.mean()), 'paired_gap_max_mm': float(gap.max()),
               'all_edge_ratio_p95': float(np.percentile(ratios,95)),
               'all_edge_ratio_p99': float(np.percentile(ratios,99)),
               'all_edge_ratio_max': float(ratios[worst]),
               'all_worst_edge_index': worst,
               'all_worst_edge_u': int(self.edges[worst,0]),
               'all_worst_edge_v': int(self.edges[worst,1]),
               'all_worst_edge_anchor_endpoints': int(self.edge_anchor_count[worst]),
               'anchor_edge_ratio_p95': float(np.percentile(ratios[self.local],95)),
               'anchor_edge_ratio_max': float(ratios[local_worst]),
               'anchor_worst_edge_index': local_worst,
               'anchor_worst_edge_u': int(self.edges[local_worst,0]),
               'anchor_worst_edge_v': int(self.edges[local_worst,1]),
               'all_edge_ratio_to_lift_start_max': float(ratio_to_start.max()),
               'anchor_edge_ratio_to_lift_start_max': float(ratio_to_start[self.local].max())}
        for count,label in [(0,'outside'),(1,'boundary'),(2,'internal')]:
            subset = ratios[self.edge_anchor_count==count]
            row[label+'_edge_ratio_max'] = float(subset.max()) if len(subset) else None
        if self.frames:
            prev = self.frames[-1]
            delta = np.linalg.norm(s['vertices']-prev['vertices'], axis=1)*1000
            row.update(max_vertex_displacement_mm=float(delta.max()),
                       worst_displacement_vertex=int(delta.argmax()),
                       ee_speed_m_s=float(np.linalg.norm(ee-prev['ee_position'])/self.dt),
                       block_speed_m_s=float(np.linalg.norm(s['position']-prev['block_position'])/self.dt))
        else:
            row.update(max_vertex_displacement_mm=0.0, worst_displacement_vertex=-1,
                       ee_speed_m_s=0.0, block_speed_m_s=0.0)
        frame = {'vertices': s['vertices'].copy(), 'block_position': s['position'].copy(),
                 'block_quaternion': s['quaternion'].copy(), 'block_scale': s['scale'].copy(), 'ee_position': ee.copy(),
                 'ee_quaternion': quat.copy(), 'anchor_targets': targets.copy()}
        if self.writer is None:
            self.writer = csv.DictWriter(self.csv_file, fieldnames=list(row))
            self.writer.writeheader()
        self.writer.writerow(row)
        self.csv_file.flush()
        self.rows.append(row)
        self.frames.append(frame)

    def begin_hold(self, steps):
        if not self.active or self.phase != 'lift' or not self.frames:
            raise RuntimeError('Hold must begin at the active lift trace boundary')
        if int(steps) <= 0:
            raise ValueError('Hold step count must be positive')
        self.expected_hold_steps = int(steps)
        self.hold_start_frame = len(self.frames)-1
        self.phase = 'hold'
        print('LIFT_HOLD_PHASE_BEGIN', self.rows[-1]['physics_step'],
              'STEPS', steps, 'SECONDS', steps*self.dt,
              'FIXED_EE_TARGET', self.target.tolist(), flush=True)

    def finish(self, completed):
        if self.finished:
            return self.summary
        if self.active:
            if self.had_own_step:
                self.world.step = self.original_step
            else:
                delattr(self.world, 'step')
            self.active = False
        if self.csv_file is not None:
            self.csv_file.close()
        self.finished = True
        if not self.frames:
            self.summary.update(capture_complete=False, error='No frames captured')
        else:
            arrays = {k:np.stack([f[k] for f in self.frames]) for k in self.frames[0]}
            arrays.update(phase_code=np.asarray([0 if r['phase']=='lift' else 1 for r in self.rows],dtype=np.int8),
                          hold_start_frame=np.asarray(self.hold_start_frame,dtype=np.int64),
                          expected_hold_steps=np.asarray(self.expected_hold_steps,dtype=np.int64),
                          physics_steps=np.asarray([r['physics_step'] for r in self.rows], dtype=np.int64),
                          elapsed_sim_seconds=np.asarray([r['elapsed_sim_seconds'] for r in self.rows]),
                          anchor_indices=self.ids, edges=self.edges,
                          edge_anchor_endpoint_count=self.edge_anchor_count,
                          rest_edge_lengths=self.rest_lengths, lift_start_edge_lengths=self.start_lengths,
                          lift_ee_target=self.target,
                          tracked_indices=self.b._env.control.tracked,
                          points0=self.observer.original_points0,
                          points1=self.observer.expected_points1)
            np.savez_compressed(self.output/'frames.npz', **arrays)
            peak = max(self.rows, key=lambda r:r['all_edge_ratio_max'])
            local_peak = max(self.rows, key=lambda r:r['anchor_edge_ratio_max'])
            phase_counts = {phase:sum(r['phase']==phase for r in self.rows) for phase in ('lift','hold')}
            self.summary.update(capture_complete=bool(completed and self.hold_start_frame>=0 and phase_counts['hold']==self.expected_hold_steps),
                 phase_counts=phase_counts, hold_start_shared_frame=self.hold_start_frame,
                 expected_hold_steps=self.expected_hold_steps,
                 hold_target_policy='same original lift EE target; measured pose may continue approaching it',
                 sample_count=len(self.rows),
                 physics_dt=self.dt, first_step=self.rows[0]['physics_step'], last_step=self.rows[-1]['physics_step'],
                 captured_world_steps=len(self.rows)-1, global_peak=peak, anchor_peak=local_peak,
                 edge_class_counts={str(i):int((self.edge_anchor_count==i).sum()) for i in [0,1,2]},
                 path=str(self.output), note='Geometric ratios only; no stress or self-intersection certification.')
        if self.rows:
            hold_rows = [row for row in self.rows if row['phase']=='hold']
            window = hold_rows[-30:]
            if window:
                self.summary['last_hold_window'] = {
                    'sample_count':len(window), 'nominal_duration_seconds':len(window)*self.dt,
                    'ee_speed_max_m_s':max(r['ee_speed_m_s'] for r in window),
                    'block_speed_max_m_s':max(r['block_speed_m_s'] for r in window),
                    'global_edge_ratio_min_of_maxima':min(r['all_edge_ratio_max'] for r in window),
                    'global_edge_ratio_max_of_maxima':max(r['all_edge_ratio_max'] for r in window),
                    'note':'Diagnostics only; no equilibrium or material-quality acceptance threshold.'}
        (self.output/'summary.json').write_text(json.dumps(self.summary, indent=2, allow_nan=False), encoding='utf-8')
        print('LIFT_HOLD_TRACE_SAVED', json.dumps(self.summary), flush=True)
        return self.summary
