import bpy
import numpy as np
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_clean_retarget.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_clean_retarget.fbx"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Mixamo_Armature"

# Apply scale and rotation to character armature
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Read raw binary motions
item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)

SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]

BONE_MAPPING = {
    "mixamorig:Hips": 0, # Hips
    "mixamorig:Spine": 1, # Spine1
    "mixamorig:Spine1": 2, # Spine2
    "mixamorig:Spine2": 3, # Chest
    "mixamorig:Neck": 4, # Neck1
    "mixamorig:Head": 6, # Head
    "mixamorig:LeftShoulder": 10, # LeftShoulder
    "mixamorig:LeftArm": 11, # LeftArm
    "mixamorig:LeftForeArm": 12, # LeftForeArm
    "mixamorig:LeftHand": 13, # LeftHand
    "mixamorig:RightShoulder": 16, # RightShoulder
    "mixamorig:RightArm": 17, # RightArm
    "mixamorig:RightForeArm": 18, # RightForeArm
    "mixamorig:RightHand": 19, # RightHand
    "mixamorig:LeftUpLeg": 22, # LeftLeg
    "mixamorig:LeftLeg": 23, # LeftShin
    "mixamorig:LeftFoot": 24, # LeftFoot
    "mixamorig:LeftToeBase": 25, # LeftToeBase
    "mixamorig:RightUpLeg": 26, # RightLeg
    "mixamorig:RightLeg": 27, # RightShin
    "mixamorig:RightFoot": 28, # RightFoot
    "mixamorig:RightToeBase": 29, # RightToeBase
}

num_frames = len(root_data) // 3
rot_data = rot_data.reshape((num_frames, len(SOMA30_NAMES), 4))
root_data = root_data.reshape((num_frames, 3))

print(f"Applying {num_frames} frames directly to Mixamo Armature...")

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Record rest location of Hips
hips_pb = char_arm.pose.bones.get("mixamorig:Hips")
hips_rest_loc = hips_pb.location.copy() if hips_pb else (0, 0, 0)
root_start_pos = root_data[0].copy()

# Set rotation mode
for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

for f in range(num_frames):
    bpy.context.scene.frame_set(f)

    # 1. Hips Root Translation (delta offset)
    if hips_pb:
        # SOMA root positions: x, y, z where Y is up
        delta_x = root_data[f, 0] - root_start_pos[0]
        delta_y = root_data[f, 1] - root_start_pos[1]
        delta_z = root_data[f, 2] - root_start_pos[2]

        # In Blender, Z is UP, Y is Forward/Back
        hips_pb.location = (
            hips_rest_loc[0] + delta_x,
            hips_rest_loc[1] - delta_z, # Z-motion in glTF is -Y in Blender
            hips_rest_loc[2] + delta_y  # Y-motion in glTF is +Z in Blender
        )
        hips_pb.keyframe_insert(data_path="location", frame=f)

    # 2. Bone Rotations
    for mix_name, soma_idx in BONE_MAPPING.items():
        if mix_name in char_arm.pose.bones:
            pb = char_arm.pose.bones[mix_name]
            qx, qy, qz, qw = rot_data[f, soma_idx]
            
            # glTF Y-up to Blender Z-up coordinate conversion for quaternions:
            # (qx, qy, qz, qw) in glTF -> (qw, qx, -qz, qy) in Blender
            pb.rotation_quaternion = (qw, qx, -qz, qy)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# Export GLB (for Lens Studio)
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_animations=True,
    export_current_frame=False
)

# Export FBX (for Unity)
bpy.ops.export_scene.fbx(
    filepath=output_fbx,
    bake_anim=True,
    bake_anim_use_all_bones=True
)

print(f"\n[SUCCESS] Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}\n")
