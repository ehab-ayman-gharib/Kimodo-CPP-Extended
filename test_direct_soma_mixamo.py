import bpy
import numpy as np
import mathutils
import math
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
motion_dir = Path(r"E:\Kimodo-CPP\demo-output\f70d7468257052d0")

# Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# SOMA 30 Names
SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]

# Mixamo mapping
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

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

hips_pb = char_arm.pose.bones.get("mixamorig:Hips")
hips_rest_loc = hips_pb.location.copy() if hips_pb else mathutils.Vector((0,0,0))
root_start = root_data[0].copy()

for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

# Frame 105 test
f = 105

# In SOMA/glTF coordinates:
# glTF to Blender: X -> X, Y -> Z, Z -> -Y
for mix_name, s_idx in BONE_MAPPING.items():
    pb = char_arm.pose.bones.get(mix_name)
    if pb:
        qx, qy, qz, qw = rot_data[f, s_idx]
        # In Blender WXYZ:
        q_soma = mathutils.Quaternion((qw, qx, qy, qz))
        pb.rotation_quaternion = q_soma

bpy.context.view_layer.update()

print("--- DIRECT SOMA LOCAL ROTATIONS ON MIXAMO AT FRAME 105 ---")
for bname in ['mixamorig:Head', 'mixamorig:LeftHand', 'mixamorig:RightHand', 'mixamorig:LeftForeArm', 'mixamorig:RightForeArm']:
    pb = char_arm.pose.bones.get(bname)
    if pb:
        pos = (char_arm.matrix_world @ pb.matrix).to_translation()
        print(f"  {bname}: pos={pos}, quat={pb.rotation_quaternion}")
