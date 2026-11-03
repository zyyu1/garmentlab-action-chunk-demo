"""Passive post-step video/state recorder; never advances physics itself."""
import hashlib
import inspect
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class EpisodeEvidence:
    def __init__(self, backend, output, sources, synthetic=False):
        self.b = backend
        self.out = Path(output) / 'evidence'
        self.out.mkdir()
        self.world = backend._env.world
        self.original_step = self.world.step
        self.original_execute = backend.execute
        self.writer = None
        self.frames = 0
        self.steps = 0
        self.actions = 0
        self.active_call = None
        self.errors = []
        self.samples = {}
        self.synthetic = synthetic
        self.stream = (self.out / 'timeline.jsonl').open('w', encoding='utf-8')
        self.sources = {}
        source_dir = self.out / 'source'
        source_dir.mkdir()
        for index, path in enumerate(sources):
            path = Path(path).resolve()
            name = '%03d_%s' % (index, path.name)
            (source_dir / name).write_bytes(path.read_bytes())
            self.sources[name] = {'original': str(path), 'sha256': digest(path)}
        self.emit('start', synthetic=synthetic)

    def emit(self, kind, **data):
        row = dict(kind=kind, utc=datetime.now(timezone.utc).isoformat(),
                   monotonic_ns=time.monotonic_ns(), sim_time_s=float(self.world.current_time),
                   observed_step=self.steps, call_id=self.active_call, **data)
        self.stream.write(json.dumps(row, allow_nan=False) + '\n')
        self.stream.flush()
        return row

    def state(self):
        b = self.b
        ee = np.asarray(b._env.robots[0].get_cur_ee_pos()[0], dtype=float)
        if not np.isfinite(ee).all():
            raise ValueError('Nonfinite EE state')
        return dict(holding=bool(b._holding), attached=b._env.control.attachlist != [None],
                    ee_m=ee.tolist(), backend_step=int(b._step_count['n']))

    def capture(self):
        import cv2
        # Render-only: no world.step, no settle and no control commands.
        self.world.render()
        rgb = np.asarray(self.b._env.camera.camera.get_rgb())
        if rgb.ndim != 3 or rgb.shape[2] < 3 or not np.isfinite(rgb).all():
            raise ValueError('Invalid camera RGB')
        rgb = rgb[:, :, :3]
        if np.issubdtype(rgb.dtype, np.floating):
            rgb = rgb * (255 if rgb.max() <= 1 else 1)
        rgb = np.ascontiguousarray(np.clip(rgb, 0, 255), dtype=np.uint8)
        if self.writer is None:
            self.size = (rgb.shape[1], rgb.shape[0])
            self.writer = cv2.VideoWriter(str(self.out / 'episode.mp4'),
                                         cv2.VideoWriter_fourcc(*'mp4v'), 30., self.size)
            if not self.writer.isOpened():
                raise RuntimeError('Video writer failed')
        if (rgb.shape[1], rgb.shape[0]) != self.size:
            raise ValueError('Camera dimensions changed')
        self.writer.write(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        self.emit('frame', frame_index=self.frames, **self.state())
        self.frames += 1

    def safe_capture(self):
        try:
            self.capture()
        except Exception as exc:
            self.errors.append(repr(exc))
            self.emit('capture_error', error=repr(exc))

    def install(self):
        def step(*args, **kwargs):
            value = self.original_step(*args, **kwargs)
            self.steps += 1
            try:
                self.emit('state', **self.state())
            except Exception as exc:
                self.errors.append(repr(exc))
                self.emit('state_error', error=repr(exc))
            if self.steps % 2 == 0:
                self.safe_capture()
            return value

        def execute(chunk):
            self.actions += 1
            self.active_call = self.actions
            self.emit('action_begin', targets=[np.asarray(a.target_pose).tolist() for a in chunk.actions],
                      commands=[int(a.gripper_command) for a in chunk.actions], horizon=len(chunk.actions))
            try:
                response = self.original_execute(chunk)
                self.emit('action_end', executed_steps=int(response['executed_steps']), **self.state())
                return response
            except BaseException as exc:
                self.emit('action_error', error=repr(exc))
                raise
            finally:
                self.active_call = None
        self.world.step = step
        self.b.execute = execute
        self.safe_capture()

    def sample(self, label):
        vertices = np.asarray(self.b._garment_world_positions(), dtype=float)
        if not np.isfinite(vertices).all():
            raise ValueError('Nonfinite cloth vertices')
        np.savez_compressed(self.out / (label + '.npz'), vertices=vertices)
        self.samples[label] = self.emit('sample', label=label, **self.state())
        self.safe_capture()

    def retention(self, retreat):
        """Caller supplies one explicit public retreat action; never hide it in OPEN."""
        self.sample('released')
        if self.state()['holding'] or self.state()['attached']:
            raise RuntimeError('Retention requires detached OPEN state')
        retreat()
        self.sample('retreated')
        dt = float(self.world.get_physics_dt())
        if not np.isfinite(dt) or dt <= 0:
            raise ValueError('Invalid physics dt')
        for label, seconds in [('hold_3s', 3.), ('hold_4s', 1.)]:
            for _ in range(int(np.ceil(seconds / dt))):
                self.world.step(render=True)
            self.sample(label)

    def finish(self, result):
        self.world.step = self.original_step
        self.b.execute = self.original_execute
        try:
            self.sample('terminal')
        except Exception as exc:
            self.errors.append(repr(exc))
        if self.writer is not None:
            self.writer.release()
        self.emit('finish', runner_passed=bool(result.get('passed')), errors=result.get('errors', []))
        self.stream.close()
        summary = dict(schema_version=1, synthetic=self.synthetic, frames=self.frames,
                       observed_steps=self.steps, execute_calls=self.actions, errors=self.errors,
                       sources=self.sources, samples=self.samples,
                       formal_day4_success=False, playback_fps=30,
                       time_authority='timeline.sim_time_s; video playback is not elapsed simulation time')
        (self.out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        manifest = {p.relative_to(self.out).as_posix(): digest(p)
                    for p in self.out.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        (self.out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        return summary


def attach_evidence(backend, output, runner, code_files):
    base = Path(runner).resolve().parent
    sources = [Path(__file__), Path(runner)]
    for name, expected in code_files.items():
        path = base / name
        if not path.is_file():
            path = base.parent.parent / name
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError('Source manifest mismatch: ' + name)
        sources.append(path)
    for obj in (type(backend), type(backend._env), type(backend._env.control),
                type(backend._env.robots[0])):
        sources.append(Path(inspect.getfile(obj)))
    recorder = EpisodeEvidence(backend, output, list(dict.fromkeys(sources)))
    recorder.install()
    return recorder
