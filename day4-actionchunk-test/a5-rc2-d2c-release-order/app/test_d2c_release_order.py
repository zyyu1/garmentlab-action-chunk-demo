"""Offline D2-C fixtures; no Isaac/GPU/cv2 required."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from a5_capture_diag import (hold_open_for_steps, preopen_while_attached,
                             registered_delay_steps)


class Slot:
    def __init__(self, enabled=False):
        self.enabled = enabled

    def attachment_enabled(self):
        return self.enabled


class Control:
    def __init__(self, enabled=False):
        self.slots = [Slot(enabled), Slot(False), Slot(False)]

    def robot_goto_position(self, *args, **kwargs):
        raise AssertionError('D2-C wait must not issue a control call')


class Robot:
    def get_cur_ee_pos(self):
        return np.array([0., 0., .2]), None


class World:
    def __init__(self, start=0):
        self.current_time_step_index = start
        self.current_time = start / 60
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
        self.assertEqual(world.current_time_step_index, 120)
        self.assertAlmostEqual(world.current_time, 2.0, places=12)
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


class ActiveRobot:
    def __init__(self, slot, world, steps=10, aperture_after=.08,
                 drop_attachment=False, drop_after=None):
        self.slot = slot
        self.world = world
        self.steps = steps
        self.aperture_after = aperture_after
        self.drop_attachment = drop_attachment
        self.drop_after = drop_after
        self.calls = 0

    def open(self):
        self.calls += 1
        for index in range(self.steps):
            self.world.step()
            if self.drop_after is not None and index + 1 == self.drop_after:
                self.slot.enabled = False
        self.slot.aperture = self.aperture_after
        if self.drop_attachment:
            self.slot.enabled = False


class Active:
    def __init__(self, holding=True, enabled=True, aperture=.02):
        self.holding = holding
        self.enabled = enabled
        self.aperture = aperture

    def attachment_enabled(self):
        return self.enabled


class PreopenControl:
    def __init__(self, active):
        self.active = active
        self.slots = [active]
        self.exclusive_calls = 0

    @property
    def holding(self):
        return any(slot.holding for slot in self.slots)

    def attachment_enabled(self):
        return any(slot.attachment_enabled() for slot in self.slots)

    def assert_exclusive(self):
        self.exclusive_calls += 1
        enabled = [i for i, slot in enumerate(self.slots)
                   if slot.attachment_enabled()]
        held = [i for i, slot in enumerate(self.slots) if slot.holding]
        if enabled != held:
            raise RuntimeError('Prepared slot state mismatch')


class Recorder:
    def __init__(self, active, steps=100):
        self.active = active
        self.steps = steps

    def state(self):
        return {'gripper_aperture_m': self.active.aperture}


def scene(holding=True, enabled=True, aperture=.02, steps=10,
          aperture_after=.08, drop_attachment=False, drop_after=None):
    world = World(start=100)
    active = Active(holding, enabled, aperture)
    active.robot = ActiveRobot(active, world, steps, aperture_after,
                               drop_attachment, drop_after)
    return active, world, Recorder(active), PreopenControl(active)


class ReleaseOrderTests(unittest.TestCase):
    def test_preopen_10_steps_while_attached(self):
        active, world, recorder, control = scene()
        record, original_open = preopen_while_attached(
            active, world, recorder, control)
        self.assertEqual(world.calls, 10)
        self.assertEqual(record['intervention'],
                         'open_while_attached_then_disable')
        self.assertEqual(record['preopen_start_step'], 100)
        self.assertEqual(record['preopen_end_step'], 110)
        self.assertEqual(record['preopen_steps'], 10)
        self.assertEqual(record['preopen_state_checks'], 10)
        self.assertEqual(control.exclusive_calls, 10)
        self.assertTrue(record['holding_before'])
        self.assertTrue(record['holding_after_preopen'])
        self.assertTrue(record['attachment_enabled_before'])
        self.assertTrue(record['attachment_enabled_after_preopen'])
        self.assertEqual(record['gripper_aperture_before_m'], .02)
        self.assertEqual(record['gripper_aperture_after_preopen_m'], .08)
        self.assertTrue(record['gripper_aperture_increased'])
        self.assertTrue(record['suppressed_second_open'])
        self.assertIs(original_open.__self__, active.robot)
        self.assertIs(original_open.__func__, ActiveRobot.open)

    def test_rejects_not_holding(self):
        active, world, recorder, control = scene(holding=False)
        with self.assertRaises(RuntimeError):
            preopen_while_attached(active, world, recorder, control)

    def test_rejects_already_detached(self):
        active, world, recorder, control = scene(enabled=False)
        with self.assertRaises(RuntimeError):
            preopen_while_attached(active, world, recorder, control)

    def test_rejects_wrong_open_steps(self):
        active, world, recorder, control = scene(steps=9)
        with self.assertRaises(RuntimeError):
            preopen_while_attached(active, world, recorder, control)

    def test_rejects_attachment_lost_during_open(self):
        active, world, recorder, control = scene(drop_attachment=True)
        with self.assertRaises(RuntimeError):
            preopen_while_attached(active, world, recorder, control)

    def test_rejects_attachment_lost_mid_open(self):
        active, world, recorder, control = scene(drop_after=5)
        with self.assertRaisesRegex(RuntimeError, 'preopen step 6'):
            preopen_while_attached(active, world, recorder, control)

    def test_rejects_aperture_not_increased(self):
        active, world, recorder, control = scene(aperture_after=.02)
        with self.assertRaises(RuntimeError):
            preopen_while_attached(active, world, recorder, control)

    def test_config_registers_release_order(self):
        path = Path(__file__).with_name('a5-rc2-d2c-release-order.json')
        config = json.loads(path.read_text())
        order = config['release_order']
        self.assertEqual(order['intervention'],
                         'open_while_attached_then_disable')
        self.assertEqual(order['preopen_steps'], 10)
        self.assertIs(order['open_while_attachment_enabled'], True)
        self.assertIs(order['suppress_redundant_second_open'], True)
        self.assertIs(order['attachment_disable_after_gripper_open'], True)
        self.assertIs(order['public_actions_unchanged'], True)
        self.assertIs(order['action_targets_unchanged'], True)
        self.assertEqual(order['wait_steps_after_release'], 120)
        self.assertEqual(config['delay']['steps'], 120)


if __name__ == '__main__':
    unittest.main()
