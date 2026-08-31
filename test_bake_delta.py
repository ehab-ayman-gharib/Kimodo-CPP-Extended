import bpy
import mathutils
import sys
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\upload_character.fbx"
motion_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb"
output_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_delta_test.glb"

BONE_MAPPING = {
    "Hips": "mixamorig:Hips",
    "Spine1": "mixamorig:Spine",
    "Spine2": "mixamorig:Spine1",
    "Chest": "mixamorig:Spine2",
    "Neck1": "mixamorig:Neck",
    "Head": "mixamorig:Head",
    "LeftShoulder": "mixamorig:LeftShoulder",
    "LeftArm": "mixamorig:LeftArm",
    "LeftForeArm": "mixamorig:LeftForeArm",
    "LeftHand": "mixamorig:LeftHand",
    "RightShoulder": "mixamorig:RightShoulder",
    "RightArm": "mixamorig:RightArm",
    "RightForeArm": "mixamorig:RightForeArm",
    "RightHand": "mixamorig:RightHand",
    "LeftLeg": "mixamorig:LeftUpLeg",
    "LeftShin": "mixamorig:LeftLeg",
    "LeftFoot": "mixamorig:LeftFoot",
    "LeftToeBase": "mixamorig:LeftToeBase",
    "RightLeg": "mixamorig:RightUpLeg",
    "RightShin": "mixamorig:RightLeg",
    "RightFoot": "mixamorig:RightFoot",
    "RightToeBase": "mixamorig:RightToeBase",
}

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

# 2. Import Motion
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=motion_path)
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre and o.type == 'EMPTY'}

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Determine frame range
start_frame = 0
end_frame = 60
for o in motion_objs.values():
    if o.animation_data and o.animation_data.action:
        start_frame = int(o.animation_data.action.frame_range[0])
        end_frame = int(o.animation_data.action.frame_range[1])
        break

print(f"Baking frames {start_frame} to {end_frame}...")

# Sample rest orientation at frame 0
bpy.context.scene.frame_set(start_frame)
bpy.context.view_layer.update()

# Record rest world matrices of character pose bones
bone_rest_world = {}
for kimodo_name, mixamo_name in BONE_MAPPING.items():
    char_bone = None
    for pb in char_arm.pose.bones:
        if pb.name.lower() in (mixamo_name.lower(), kimodo_name.lower()):
            char_bone = pb
            break
    if char_bone:
        bone_rest_world[kimodo_name] = (char_bone, char_arm.matrix_world @ char_bone.matrix)

# Record rest world matrices of motion empties
motion_rest_world = {}
for kimodo_name in BONE_MAPPING.keys():
    if kimodo_name in motion_objs:
        motion_rest_world[kimodo_name] = motion_objs[kimodo_name].matrix_world.copy()

# Compute height ratio for hips location scaling
char_hips_z = 1.0
if "Hips" in bone_rest_world:
    char_hips_z = bone_rest_world["Hips"][1].to_translation().z
motion_hips_z = 1.0
if "Hips" in motion_rest_world:
    motion_hips_z = motion_rest_world["Hips"].to_translation().z
scale_factor = (char_hips_z / motion_hips_z) if motion_hips_z != 0 else 1.0

print(f"Height scale factor: {scale_factor:.3f} (Char Hips Z: {char_hips_z:.2f}, Motion Hips Z: {motion_hips_z:.2f})")

# Ensure rotation mode is QUATERNION
for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

# Frame by frame delta transfer
for f in range(start_frame, end_frame + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()

    for kimodo_name, (char_bone, char_rest_mat) in bone_rest_world.items():
        if kimodo_name not in motion_objs or kimodo_name not in motion_rest_world:
            continue
        
        src_obj = motion_objs[kimodo_name]
        src_curr_mat = src_obj.matrix_world
        src_rest_mat = motion_rest_world[kimodo_name]

        # Delta rotation in world space
        # R_delta = R_curr * R_rest_inv
        r_curr = src_curr_mat.to_quaternion()
        r_rest = src_rest_mat.to_quaternion()
        r_delta = r_curr @ r_rest.inverted()

        # Apply delta to char rest rotation
        char_rest_rot = char_rest_mat.to_quaternion()
        new_rot_world = r_delta @ char_rest_rot

        # Convert new world rotation to pose space (relative to armature)
        arm_rot_inv = char_arm.matrix_world.to_quaternion().inverted()
        new_rot_pose = arm_rot_inv @ new_rot_world

        # Target matrix in pose space
        target_matrix = mathutils.Matrix.Translation(char_bone.matrix.to_translation()) @ new_rot_pose.to_matrix().to_4x4()
        
        # If hips, also translate
        if kimodo_name == "Hips":
            t_src_curr = src_curr_mat.to_translation()
            t_src_rest = src_rest_mat.to_translation()
            t_delta = (t_src_curr - t_src_rest) * scale_factor
            
            char_rest_trans = char_rest_mat.to_translation()
            new_trans_world = char_rest_trans + t_delta
            new_trans_pose = char_arm.matrix_world.inverted() @ new_trans_world
            target_matrix.translation = new_trans_pose

        # Set pose bone matrix
        char_bone.matrix = target_matrix
        char_bone.keyframe_insert(data_path="rotation_quaternion", frame=f)
        if kimodo_name == "Hips":
            char_bone.keyframe_insert(data_path="location", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# Delete motion empties
for o in motion_objs.values():
    bpy.data.objects.remove(o, do_unlink=True)

# Export
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_current_frame=False
)
print(f"Exported successfully to {output_path}")
