import bpy
import numpy as np
import mathutils
from pathlib import Path

item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
rot_data = rot_data.reshape((-1, 30, 4))

print("\n--- FOREARM & HAND DELTAS AT FRAME 30 ---")
for s_idx, name in [(12, "LeftForeArm"), (13, "LeftHand"), (18, "RightForeArm"), (19, "RightHand")]:
    q0 = mathutils.Quaternion((rot_data[0, s_idx, 3], rot_data[0, s_idx, 0], rot_data[0, s_idx, 1], rot_data[0, s_idx, 2]))
    q30 = mathutils.Quaternion((rot_data[30, s_idx, 3], rot_data[30, s_idx, 0], rot_data[30, s_idx, 1], rot_data[30, s_idx, 2]))
    delta = q30 @ q0.inverted()
    print(f"{name}: delta={delta}, euler_deg={np.degrees(delta.to_euler('XYZ'))}")
