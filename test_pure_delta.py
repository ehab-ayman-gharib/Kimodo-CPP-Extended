import bpy
import numpy as np
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_pure_delta_test.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_pure_delta_test.fbx"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

# Apply scale and rotation so Armature object transform is clean
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Read raw binary motions
item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)

SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]

BONE_MAPPING = {
    "mixamorig:Hips": 0,          # Hips
    "mixamorig:Spine": 1,         # Spine1
    "mixamorig:Spine1": 2,        # Spine2
    "mixamorig:Spine2": 3,        # Chest
    "mixamorig:Neck": 4,          # Neck1
    "mixamorig:Head": 6,          # Head
    "mixamorig:LeftShoulder": 10,  # LeftShoulder
    "mixamorig:LeftArm": 11,       # LeftArm
    "mixamorig:LeftForeArm": 12,   # LeftForeArm
    "mixamorig:LeftHand": 13,      # LeftHand
    "mixamorig:RightShoulder": 16, # RightShoulder
    "mixamorig:RightArm": 17,      # RightArm
    "mixamorig:RightForeArm": 18,  # RightForeArm
    "mixamorig:RightHand": 19,     # RightHand
    "mixamorig:LeftUpLeg": 22,     # LeftLeg
    "mixamorig:LeftLeg": 23,       # LeftShin
    "mixamorig:LeftFoot": 24,      # LeftFoot
    "mixamorig:LeftToeBase": 25,   # LeftToeBase
    "mixamorig:RightUpLeg": 26,    # RightLeg
    "mixamorig:RightLeg": 27,      # RightShin
    "mixamorig:RightFoot": 28,     # RightFoot
    "mixamorig:RightToeBase": 29,  # RightToeBase
}

num_frames = len(root_data) // 3
rot_data = rot_data.reshape((num_frames, len(SOMA30_NAMES), 4))
root_data = root_data.reshape((num_frames, 3))

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

hips_pb = None
for pb in char_arm.pose.bones:
    if "hip" in pb.name.lower() or "pelvis" in pb.name.lower():
        hips_pb = pb
        break

hips_rest_loc = hips_pb.location.copy() if hips_pb else (0, 0, 0)
root_start = root_data[0].copy()

for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

for f in range(num_frames):
    # 1. Hips Translation Delta
    if hips_pb:
        dx = root_data[f, 0] - root_start[0]
        dy = root_data[f, 1] - root_start[1]
        dz = -(root_data[f, 2] - root_start[2]) # Forward travel in facing direction

        hips_pb.location = (
            hips_rest_loc[0] + dx,
            hips_rest_loc[1] + dy,
            hips_rest_loc[2] + dz
        )
        hips_pb.keyframe_insert(data_path="location", frame=f)

    # 2. Pure Delta Rotations
    for mix_name, s_idx in BONE_MAPPING.items():
        pb = None
        for b in char_arm.pose.bones:
            if b.name.lower() == mix_name.lower() or b.name.lower() == mix_name.replace("mixamorig:", "").lower():
                pb = b
                break

        if pb:
            # SOMA quaternion at current frame: (x, y, z, w) -> (w, x, y, z)
            qx, qy, qz, qw = rot_data[f, s_idx]
            q_curr = mathutils.Quaternion((qw, qx, qy, qz))

            # SOMA quaternion at frame 0 (rest pose)
            rx, ry, rz, rw = rot_data[0, s_idx]
            q_rest = mathutils.Quaternion((rw, rx, ry, rz))

            # Delta rotation relative to rest pose
            q_delta = q_curr @ q_rest.inverted()

            pb.rotation_quaternion = q_delta
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# Export GLB & FBX
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_animations=True,
    export_current_frame=False
)
bpy.ops.export_scene.fbx(
    filepath=output_fbx,
    bake_anim=True,
    bake_anim_use_all_bones=True
)

print(f"\n[SUCCESS] Pure Delta Bake Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}\n")
