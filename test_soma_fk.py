import bpy
import numpy as np
import mathutils
from pathlib import Path

motion_dir = Path(r"E:\Kimodo-CPP\demo-output\f70d7468257052d0")
rot_data = np.fromfile(motion_dir / "local_rotations_xyzw.f32", dtype=np.float32).reshape((-1, 30, 4))
root_data = np.fromfile(motion_dir / "root_positions.f32", dtype=np.float32).reshape((-1, 3))

SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]
SOMA30_OFFSETS = [[0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]]

# Compute Forward Kinematics in SOMA space
f = 105
world_mats = [mathutils.Matrix.Identity(4) for _ in range(30)]

for i in range(30):
    p = SOMA30_PARENTS[i]
    off = mathutils.Vector(SOMA30_OFFSETS[i])
    q = mathutils.Quaternion((rot_data[f, i, 3], rot_data[f, i, 0], rot_data[f, i, 1], rot_data[f, i, 2]))
    local_m = mathutils.Matrix.Translation(off) @ q.to_matrix().to_4x4()
    if p < 0:
        world_mats[i] = local_m
    else:
        world_mats[i] = world_mats[p] @ local_m

print("--- SOMA TRUE FK WORLD POSITIONS AT FRAME 105 ---")
for s_idx in [6, 11, 12, 13, 17, 18, 19]:
    pos = world_mats[s_idx].to_translation()
    print(f"  {SOMA30_NAMES[s_idx]}: X={pos.x:.3f}, Y(Up)={pos.y:.3f}, Z(Fwd)={pos.z:.3f}")
