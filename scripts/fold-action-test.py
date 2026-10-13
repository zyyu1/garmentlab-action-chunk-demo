from pathlib import Path
import os
import sys

root = Path("/root/autodl-tmp/garmentlab_workspace/GarmentLab")
os.chdir(root)
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "Env"))

garment = root / "Assets/Garments/Tops/NoCollar_LSleeve_FrontClose/TNLC_Dress057/TNLC_Dress057_obj.usd"
assert garment.is_file(), f"衣物文件不存在: {garment}"
assert (root / "Assets/Scene/FlatGrid.usd").is_file()

from Env.env.FoldEnv import FoldEnv, simulation_app

try:
    import numpy as np
    import imageio.v3 as iio
    from Env.Config.GarmentConfig import GarmentConfig
    from Env.Config.FrankaConfig import FrankaConfig

    output = Path("/root/autodl-tmp/fold-action-output")
    output.mkdir(parents=True, exist_ok=True)

    print("BUILD_SCENE", flush=True)
    config = GarmentConfig(
        usd_path=str(garment),
        visual_material_usd=None,
        pos=np.array([0, -0.95, 0.3]),
        ori=np.array([0, 0, 0]),
        particle_contact_offset=0.01,
    )
    env = FoldEnv(
        garment_config=[config],
        franka_config=FrankaConfig(
            ori=[np.array([0, 0, -np.pi / 2])]
        ),
    )

    print("RESET_START", flush=True)
    env.reset()
    print("RESET_OK", flush=True)


    # 给整个动作阶段设置总步数上限。
    original_step = env.world.step
    step_count = [0]

    def bounded_step(*args, **kwargs):
        step_count[0] += 1
        if step_count[0] > 15000:
            raise RuntimeError("动作阶段超过 15000 步，已停止")
        return original_step(*args, **kwargs)

    env.world.step = bounded_step

    def snapshot(name):
        for _ in range(10):
            env.step()
        frame = np.asarray(env.camera.get_rgb_graph())
        assert frame.size > 0, "相机图像为空"
        iio.imwrite(output / (name + ".png"), frame)
        print("SAVED " + name, flush=True)

    env.control.robot_reset()
    for _ in range(120):
        env.step()
    snapshot("00_before")

    sequence = [
        ("grasp", [0.35282, -0.26231, 0.02]),
        ("move",  [0.1, -0.26231, 0.22]),
        ("move",  [-0.12, -0.26231, 0.1]),
        ("release", None),
        ("grasp", [-0.377, -0.26231, 0.02]),
        ("move",  [0.0, -0.26231, 0.22]),
        ("move",  [0.07, -0.26231, 0.03]),
        ("release", None),
        ("grasp", [0.0, -0.65, 0.015]),
        ("move",  [0.0, -0.515, 0.22]),
        ("move",  [0.0, -0.25, 0.05]),
        ("release", None),
    ]

    for index, (action, position) in enumerate(sequence, 1):
        label = f"{index:02d}_{action}"
        print("ACTION_START " + label, flush=True)
        if action == "release":
            env.control.ungrasp([False])
        else:
            target_position = np.array(position)
            method = getattr(env.control, action)
            method([target_position], [None], [True])
            if not env.robots[0].reach(target_position, None):
                snapshot(label + "_not_reached")
                raise RuntimeError(label + ": 机械臂未到达目标位置")
        snapshot(label)
        print("ACTION_DONE " + label, flush=True)

    for step in range(120):
        env.step()
        if (step + 1) % 30 == 0:
            print(f"STEP={step + 1}", flush=True)

    rgb = np.asarray(env.camera.get_rgb_graph())
    assert rgb.ndim == 3 and rgb.shape[2] == 3 and rgb.size > 0, \
        f"相机图像异常: {rgb.shape}"
    assert np.isfinite(rgb).all(), "图像包含无效数值"
    iio.imwrite(output / "scene.png", rgb)

    vertices = np.asarray(
        env.garment[0].get_vertices_positions()
    ).reshape(-1, 3)
    assert len(vertices) > 0 and np.isfinite(vertices).all(), \
        "衣物顶点为空或包含无效数值"
    np.save(output / "garment_vertices.npy", vertices)

    print(f"RGB_SHAPE={rgb.shape}, VERTICES={len(vertices)}", flush=True)
    print("FOLD_ACTION_SEQUENCE_OK", flush=True)
except BaseException:
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    raise
finally:
    simulation_app.close()
