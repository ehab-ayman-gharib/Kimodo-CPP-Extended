import bpy
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

glb_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\top3d_thinking.glb"
fbx_path = r"E:\Kimodo-CPP\Remy.fbx"
output_fbx = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_perfect_retarget.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_perfect_retarget.glb"

# 1. Import Source Animated GLB
bpy.ops.import_scene.gltf(filepath=glb_path)
src_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
src_arm.name = "Source_Armature"

# 2. Import Target Character FBX
bpy.ops.import_scene.fbx(filepath=fbx_path)
tgt_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != src_arm][0]
tgt_arm.name = "Target_Armature"

# Normalize transforms
bpy.context.view_layer.objects.active = tgt_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# SOMA to Mixamo Name Mapping
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

# Measure Rest Orientations (Frame 0 or rest matrix)
src_rest_rot = {}
for s_name in BONE_MAPPING.keys():
    if s_name in src_arm.data.bones:
        src_rest_rot[s_name] = src_arm.data.bones[s_name].matrix_local.to_quaternion()

tgt_rest_rot = {}
for t_name in BONE_MAPPING.values():
    if t_name in tgt_arm.data.bones:
        tgt_rest_rot[t_name] = tgt_arm.data.bones[t_name].matrix_local.to_quaternion()

# Calculate scale ratio from Hips height
src_hips_h = src_arm.data.bones["Hips"].head_local.z
tgt_hips_h = tgt_arm.data.bones["mixamorig:Hips"].head_local.z
scale_ratio = tgt_hips_h / src_hips_h if src_hips_h > 1e-4 else 1.0
print(f"Hips height ratio: tgt={tgt_hips_h:.3f}, src={src_hips_h:.3f} => scale={scale_ratio:.3f}")

# Frame range
action = src_arm.animation_data.action if src_arm.animation_data else None
start_frame = int(src_arm.animation_data.action.frame_range[0]) if action else 0
end_frame = int(src_arm.animation_data.action.frame_range[1]) if action else 150

bpy.context.view_layer.objects.active = tgt_arm
bpy.ops.object.mode_set(mode='POSE')

for pb in tgt_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

tgt_hips_pb = tgt_arm.pose.bones.get("mixamorig:Hips")
tgt_hips_rest_loc = tgt_hips_pb.location.copy() if tgt_hips_pb else mathutils.Vector((0,0,0))

# Record src hips start location at frame 0
bpy.context.scene.frame_set(start_frame)
bpy.context.view_layer.update()
src_hips_pb = src_arm.pose.bones.get("Hips")
src_hips_start_loc = src_hips_pb.location.copy() if src_hips_pb else mathutils.Vector((0,0,0))

print(f"Retargeting {end_frame - start_frame + 1} frames...")

for f in range(start_frame, end_frame + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()

    # 1. Hips Root Translation
    if tgt_hips_pb and src_hips_pb:
        d_loc = src_hips_pb.location - src_hips_start_loc
        tgt_hips_pb.location = tgt_hips_rest_loc + d_loc * scale_ratio
        tgt_hips_pb.keyframe_insert(data_path="location", frame=f)

    # 2. Retarget Orientations via Delta from Rest
    for s_name, t_name in BONE_MAPPING.items():
        pb_src = src_arm.pose.bones.get(s_name)
        pb_tgt = tgt_arm.pose.bones.get(t_name)

        if pb_src and pb_tgt and s_name in src_rest_rot and t_name in tgt_rest_rot:
            # Source animated world rotation
            w_src = (src_arm.matrix_world @ pb_src.matrix).to_quaternion()
            # Source rest world rotation
            w_src_rest = src_rest_rot[s_name]

            # Delta in world space: delta = w_src @ w_src_rest^-1
            delta_w = w_src @ w_src_rest.inverted()

            # Target world rotation: w_tgt = delta_w @ w_tgt_rest
            w_tgt_target = delta_w @ tgt_rest_rot[t_name]

            # Convert to PoseBone parent-relative quaternion
            if pb_tgt.parent:
                w_parent = (tgt_arm.matrix_world @ pb_tgt.parent.matrix).to_quaternion()
                pb_tgt.rotation_quaternion = w_parent.inverted() @ w_tgt_target
            else:
                pb_tgt.rotation_quaternion = w_tgt_target

            pb_tgt.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# Remove source armature
bpy.data.objects.remove(src_arm, do_unlink=True)

# Export baked GLB & FBX
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

print(f"[SUCCESS] Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
