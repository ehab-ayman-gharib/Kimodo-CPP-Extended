import bpy
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

glb_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\top3d_thinking.glb"
fbx_path = r"E:\Kimodo-CPP\Remy.fbx"
output_fbx = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_offset_retarget.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_offset_retarget.glb"

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

# Remove any extra mesh objects from source or helper (like Icosphere)
for o in list(bpy.data.objects):
    if o != tgt_arm and o.type == 'MESH':
        if "ico" in o.name.lower() or "proxy" in o.name.lower():
            bpy.data.objects.remove(o, do_unlink=True)

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

# Resolve bone names on target
bone_map = {}
for s_name, def_t_name in BONE_MAPPING.items():
    if s_name not in src_arm.data.bones:
        continue
    matched = None
    for c in [def_t_name, def_t_name.replace("mixamorig:", ""), s_name]:
        for b in tgt_arm.data.bones:
            if b.name.lower() == c.lower() or b.name.lower() == f"mixamorig:{c}".lower():
                matched = b.name
                break
        if matched:
            break
    if matched:
        bone_map[s_name] = matched

# 3. Create Alignment Helper Armature or Rest Rotation Matrices
# For each bone: R_src_rest = src_arm.data.bones[s].matrix_local.to_quaternion()
#                R_tgt_rest = tgt_arm.data.bones[t].matrix_local.to_quaternion()
# Target world rotation at frame f = (W_src(f) @ R_src_rest^-1) @ R_tgt_rest

# In Blender, we can implement this with Pose Bone Constraints using transformation offset!
# Or we can create an Alignment Bone hierarchy in Source Armature that has the EXACT rest orientation of the target bones!

# Let's test adding alignment bones to src_arm:
bpy.context.view_layer.objects.active = src_arm
bpy.ops.object.mode_set(mode='EDIT')

for s_name, t_name in bone_map.items():
    eb_src = src_arm.data.edit_bones.get(s_name)
    eb_tgt = tgt_arm.data.bones.get(t_name)
    if eb_src and eb_tgt:
        # Create an alignment bone at the same head/tail as eb_src, but with eb_tgt's matrix
        ab = src_arm.data.edit_bones.new(f"ALIGN_{t_name}")
        ab.head = eb_src.head
        ab.tail = eb_src.tail
        ab.matrix = eb_tgt.matrix_local.copy()
        ab.matrix.translation = eb_src.head
        ab.parent = eb_src

bpy.ops.object.mode_set(mode='OBJECT')

# Now on Target Armature, constrain each bone to ALIGN_<t_name> in WORLD space!
bpy.context.view_layer.objects.active = tgt_arm
bpy.ops.object.mode_set(mode='POSE')

for pb in tgt_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

for s_name, t_name in bone_map.items():
    pb_tgt = tgt_arm.pose.bones.get(t_name)
    align_bone_name = f"ALIGN_{t_name}"
    if pb_tgt and align_bone_name in src_arm.data.bones:
        con_rot = pb_tgt.constraints.new('COPY_ROTATION')
        con_rot.target = src_arm
        con_rot.subtarget = align_bone_name
        con_rot.target_space = 'WORLD'
        con_rot.owner_space = 'WORLD'

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

print(f"Baking alignment constraints from frame {start_frame} to {end_frame}...")
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(
    frame_start=start_frame,
    frame_end=end_frame,
    only_selected=False,
    visual_keying=True,
    clear_constraints=True,
    bake_types={'POSE'}
)

bpy.ops.object.mode_set(mode='OBJECT')

# Remove source armature
bpy.data.objects.remove(src_arm, do_unlink=True)

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

print(f"[SUCCESS] Exported with Alignment Bones:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
