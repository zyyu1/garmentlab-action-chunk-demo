"""Measured-position hold variant; inherited sampling keeps the lift unchanged."""
import json
import numpy as np
from lift_hold_step_observer import LiftHoldStepObserver


class MeasuredHoldStepObserver(LiftHoldStepObserver):
    def start(self, target):
        self.lift_target = np.asarray(target, dtype=float).copy()
        self.hold_target = None
        super().start(target)

    def begin_hold(self, steps, target):
        target = np.asarray(target, dtype=float)
        if target.shape != (3,) or not np.isfinite(target).all():
            raise ValueError('Expected finite measured xyz')
        if not np.array_equal(target, self.frames[-1]['ee_position']):
            raise RuntimeError('Hold target differs from final measured EE position')
        self.hold_target = target.copy()
        self.target = target.copy()
        super().begin_hold(steps)

    def finish(self, completed):
        if self.finished:
            return self.summary
        # Parent saves lift_ee_target from self.target; preserve its true meaning.
        self.target = self.lift_target.copy()
        summary = super().finish(completed)
        summary['hold_target_policy'] = 'measured EE xyz at lift completion; ori=None unchanged'
        summary['hold_ee_target'] = None if self.hold_target is None else self.hold_target.tolist()
        path = self.output / 'frames.npz'
        if path.exists():
            with np.load(path, allow_pickle=False) as saved:
                arrays = {key: saved[key] for key in saved.files}
            arrays['hold_ee_target'] = np.asarray([] if self.hold_target is None else self.hold_target)
            np.savez_compressed(path, **arrays)
        (self.output / 'summary.json').write_text(
            json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
        return summary
