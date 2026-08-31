import bpy
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

glb_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\top3d_thinking.glb"
fbx_path = r"E:\Kimodo-CPP\Remy.fbx"
output_fbx = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_constraint_bake.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_constraint_bake.glb"

# 1. Import Source GLB
bpy.ops.import_scene.gltf(filepath=glb_path)
src_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
src_arm.name = "Source_Armature"

# 2. Import Target FBX
bpy.ops.import_scene.fbx(filepath=fbx_path)
tgt_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != src_arm][0]
tgt_arm.name = "Target_Armature"

# Normalize transforms on target
bpy.context.view_layer.objects.active = tgt_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# SOMA to Mixamo Mapping
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

# Add constraints to Target PoseBones
bpy.context.view_layer.objects.active = tgt_arm
bpy.ops.object.mode_set(mode='POSE')

for s_name, t_name in BONE_MAPPING.items():
    pb_tgt = tgt_arm.pose.bones.get(t_name)
    if not pb_tgt:
        # Check without prefix
        for b in tgt_arm.pose.bones:
            if b.name.lower() == t_name.lower() or b.name.lower() == t_name.replace("mixamorig:", "").lower():
                pb_tgt = b
                break

    if pb_tgt and s_name in src_arm.data.bones:
        # Rotation constraint
        con_rot = pb_tgt.constraints.new('COPY_ROTATION')
        con_rot.target = src_arm
        con_rot.subtarget = s_name
        con_rot.target_space = 'WORLD'
        con_rot.owner_space = 'WORLD'

        # Location constraint on Hips
        if s_name == "Hips":
            con_loc = pb_tgt.constraints.new('COPY_LOCATION')
            con_loc.target = src_arm
            con_loc.subtarget = s_name
            con_loc.target_space = 'WORLD'
            con_loc.owner_space = 'WORLD'

# Frame range
action = src_arm.animation_data.action if src_arm.animation_data else None
start_frame = int(action.frame_range[0]) if action else 0
end_frame = int(action.frame_range[1]) if action else 150

print(f"Baking constraints from frame {start_frame} to {end_frame}...")

# Select all bones on target
bpy.ops.pose.select_all(action='SELECT')

# Native C++ bake action
bpy.ops.nla.bake(
    frame_start=start_frame,
    frame_end=end_frame,
    only_selected=False,
    visual_keying=True,
    clear_constraints=True,
    bake_types={'POSE'}
)

bpy.ops.object.mode_set(mode='OBJECT')

# Remove source armature and proxy mesh
for obj in list(bpy.data.objects):
    if "Source" in obj.name or "proxy" in obj.name.lower() or "canonical" in obj.name.lower() or "top3d" in obj.name.lower():
        bpy.data.objects.remove(obj, do_unlink=True)

# Export output
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

print(f"[SUCCESS] Native C++ Constraint Bake complete:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
