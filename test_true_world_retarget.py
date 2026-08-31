import bpy
import numpy as np
import mathutils
import math
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
motion_dir = Path(r"E:\Kimodo-CPP\demo-output\f70d7468257052d0")

bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]
SOMA30_OFFSETS = [[0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]]

BONE_MAPPING = {
    "mixamorig:Hips": 0,
    "mixamorig:Spine": 1,
    "mixamorig:Spine1": 2,
    "mixamorig:Spine2": 3,
    "mixamorig:Neck": 4,
    "mixamorig:Head": 6,
    "mixamorig:LeftShoulder": 10,
    "mixamorig:LeftArm": 11,
    "mixamorig:LeftForeArm": 12,
    "mixamorig:LeftHand": 13,
    "mixamorig:RightShoulder": 16,
    "mixamorig:RightArm": 17,
    "mixamorig:RightForeArm": 18,
    "mixamorig:RightHand": 19,
    "mixamorig:LeftUpLeg": 22,
    "mixamorig:LeftLeg": 23,
    "mixamorig:LeftFoot": 24,
    "mixamorig:LeftToeBase": 25,
    "mixamorig:RightUpLeg": 26,
    "mixamorig:RightLeg": 27,
    "mixamorig:RightFoot": 28,
    "mixamorig:RightToeBase": 29,
}

rot_data = np.fromfile(motion_dir / "local_rotations_xyzw.f32", dtype=np.float32).reshape((-1, 30, 4))
root_data = np.fromfile(motion_dir / "root_positions.f32", dtype=np.float32).reshape((-1, 3))
num_frames = len(root_data)

# Conversion matrix from SOMA Y-up to Blender Z-up
# X -> X, Y -> Z, Z -> -Y
C_mat = mathutils.Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
C_rot = C_mat.to_quaternion()

# Compute SOMA Rest World Rotations
soma_rest_world_rot = [mathutils.Quaternion((1,0,0,0)) for _ in range(30)]
for i in range(30):
    p = SOMA30_PARENTS[i]
    q_id = mathutils.Quaternion((1,0,0,0))
    if p < 0:
        soma_rest_world_rot[i] = C_rot @ q_id
    else:
        soma_rest_world_rot[i] = soma_rest_world_rot[p] @ q_id

# Record Character Rest World Rotations
char_rest_world_rot = {}
for mix_name, s_idx in BONE_MAPPING.items():
    if mix_name in char_arm.data.bones:
        b = char_arm.data.bones[mix_name]
        char_rest_world_rot[mix_name] = b.matrix_local.to_quaternion()

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

hips_pb = char_arm.pose.bones.get("mixamorig:Hips")
hips_rest_loc = hips_pb.location.copy() if hips_pb else mathutils.Vector((0,0,0))
root_start = root_data[0].copy()

# Test Frame 105
f = 105

# 1. Compute SOMA World Rotations at Frame f
soma_world_rot = [mathutils.Quaternion((1,0,0,0)) for _ in range(30)]
for i in range(30):
    p = SOMA30_PARENTS[i]
    q_curr = mathutils.Quaternion((rot_data[f, i, 3], rot_data[f, i, 0], rot_data[f, i, 1], rot_data[f, i, 2]))
    if p < 0:
        soma_world_rot[i] = C_rot @ q_curr
    else:
        soma_world_rot[i] = soma_world_rot[p] @ q_curr

# 2. Assign World Rotations to PoseBones in topological hierarchy order
for mix_name, s_idx in BONE_MAPPING.items():
    pb = char_arm.pose.bones.get(mix_name)
    if pb and mix_name in char_rest_world_rot:
        # True World Delta = W_soma(f) @ W_soma_rest^-1
        w_soma_curr = soma_world_rot[s_idx]
        w_soma_rest = soma_rest_world_rot[s_idx]
        delta_w = w_soma_curr @ w_soma_rest.inverted()
        
        # Target Character World Rotation = delta_w @ Char_rest_world_rot
        target_world_rot = delta_w @ char_rest_world_rot[mix_name]
        
        # Convert World Rotation into Parent-Relative PoseBone Quaternion
        if pb.parent:
            parent_world_rot = (char_arm.matrix_world @ pb.parent.matrix).to_quaternion()
            pb.rotation_quaternion = parent_world_rot.inverted() @ target_world_rot
        else:
            pb.rotation_quaternion = target_world_rot

bpy.context.view_layer.update()

print("\n--- TRUE WORLD ROTATION RETARGETED AT FRAME 105 ---")
for bname in ['mixamorig:Head', 'mixamorig:LeftHand', 'mixamorig:RightHand', 'mixamorig:LeftForeArm', 'mixamorig:RightForeArm']:
    pb = char_arm.pose.bones.get(bname)
    if pb:
        pos = (char_arm.matrix_world @ pb.matrix).to_translation()
        print(f"  {bname}: {pos}")
