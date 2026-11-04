"""Offline D1-120 wait fixture; no Isaac/GPU/cv2 required."""
import unittest
from types import SimpleNamespace

import numpy as np

from a5_capture_diag import hold_open_for_steps, registered_delay_steps


class Slot:
    def __init__(self, enabled=False):
        self.enabled = enabled

    def attachment_enabled(self):
        return self.enabled


class Control:
    def __init__(self, enabled=False):
        self.slots = [Slot(enabled), Slot(False), Slot(False)]

    def robot_goto_position(self, *args, **kwargs):
        raise AssertionError('D1 wait must not issue a control call')


class Robot:
    def get_cur_ee_pos(self):
        return np.array([0., 0., .2]), None


class World:
    def __init__(self):
        self.current_time_step_index = 100
        self.current_time = 10.0
        self.calls = 0

    def step(self, render=False):
        self.calls += 1
        self.current_time_step_index += 1
        self.current_time += 1 / 60


class Backend:
    def __init__(self, holding=False, gripper_state=0):
        self._holding = holding
        self._gripper_state = gripper_state
        self._env = SimpleNamespace(robots=[Robot()])


class DelayTests(unittest.TestCase):
    def test_exactly_120_steps_and_no_control(self):
        backend, world, control = Backend(), World(), Control()
        meta = hold_open_for_steps(backend, world, control, 120)
        self.assertEqual(world.calls, 120)
        self.assertEqual(world.current_time_step_index, 220)
        self.assertAlmostEqual(world.current_time, 12.0, places=12)
        self.assertEqual(meta['requested_steps'], 120)
        self.assertEqual(meta['elapsed_steps'], 120)
        self.assertAlmostEqual(meta['elapsed_sim_time_s'], 2.0, places=12)
        self.assertEqual(meta['control_calls'], 0)
        self.assertEqual(meta['target_changes'], 0)
        self.assertFalse(meta['cloth_position_reset'])
        self.assertFalse(meta['cloth_velocity_reset'])
        self.assertTrue(meta['gripper_state_open'])
        self.assertFalse(meta['attachment_enabled'])

    def test_rejects_wrong_step_count(self):
        with self.assertRaises(ValueError):
            hold_open_for_steps(Backend(), World(), Control(), 119)

    def test_rejects_attachment(self):
        with self.assertRaises(RuntimeError):
            hold_open_for_steps(Backend(), World(), Control(enabled=True), 120)

    def test_rejects_closed_gripper(self):
        with self.assertRaises(RuntimeError):
            hold_open_for_steps(Backend(gripper_state=2), World(), Control(), 120)

    def test_config_registers_120(self):
        self.assertEqual(registered_delay_steps(), 120)


if __name__ == '__main__':
    unittest.main()
