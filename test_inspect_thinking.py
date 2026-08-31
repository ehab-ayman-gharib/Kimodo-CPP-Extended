import bpy
import numpy as np
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

item_dir = Path(r"E:\Kimodo-CPP\demo-output\f70d7468257052d0")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32).reshape((-1, 30, 4))
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32).reshape((-1, 3))

# Let's inspect Frame 105
f = 105
print(f"--- SOMA ROTATIONS AT FRAME {f} ---")
SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]

for s_idx in [10, 11, 12, 13, 16, 17, 18, 19]:
    q_curr = mathutils.Quaternion((rot_data[f, s_idx, 3], rot_data[f, s_idx, 0], rot_data[f, s_idx, 1], rot_data[f, s_idx, 2]))
    q_rest = mathutils.Quaternion((rot_data[0, s_idx, 3], rot_data[0, s_idx, 0], rot_data[0, s_idx, 1], rot_data[0, s_idx, 2]))
    q_delta = q_curr @ q_rest.inverted()
    print(f"  {SOMA30_NAMES[s_idx]}: delta euler={np.degrees(q_delta.to_euler('XYZ'))}")
