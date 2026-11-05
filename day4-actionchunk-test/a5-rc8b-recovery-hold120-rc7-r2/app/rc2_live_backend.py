"""Expose the live slot holding flag while a blocking grasp/release is in flight."""
from square_pose_backend import SquarePoseBackend


class LiveSquarePoseBackend(SquarePoseBackend):
    @property
    def _holding(self):
        control = getattr(self, '_live_slot_control', None)
        if control is None:
            return self._command_holding
        return bool(control.holding)

    @_holding.setter
    def _holding(self, value):
        # Retain the original command-level latch as a distinct diagnostic.
        self._command_holding = bool(value)

    def start(self):
        super().start()
        self._live_slot_control = self._env.control

    def _execute_single(self, action):
        super()._execute_single(action)
        if self._command_holding != self._holding:
            raise RuntimeError('Command returned before holding and slot state agreed')
