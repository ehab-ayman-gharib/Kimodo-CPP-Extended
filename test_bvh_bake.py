import bpy
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
bvh_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\motion.bvh"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_bvh_bake.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_bvh_bake.fbx"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Import BVH
bpy.ops.import_anim.bvh(filepath=bvh_path, use_fps_scale=False, update_scene_fps=True, update_scene_duration=True)
bvh_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != char_arm][0]
bvh_arm.name = "BVH_Armature"

print(f"Imported BVH Armature: {bvh_arm.name} with {len(bvh_arm.pose.bones)} bones")

# 3. Retarget BVH -> Character
BONE_MAPPING = {
    "mixamorig:Hips": "Hips",
    "mixamorig:Spine": "Spine1",
    "mixamorig:Spine1": "Spine2",
    "mixamorig:Spine2": "Chest",
    "mixamorig:Neck": "Neck1",
    "mixamorig:Head": "Head",
    "mixamorig:LeftShoulder": "LeftShoulder",
    "mixamorig:LeftArm": "LeftArm",
    "mixamorig:LeftForeArm": "LeftForeArm",
    "mixamorig:LeftHand": "LeftHand",
    "mixamorig:RightShoulder": "RightShoulder",
    "mixamorig:RightArm": "RightArm",
    "mixamorig:RightForeArm": "RightForeArm",
    "mixamorig:RightHand": "RightHand",
    "mixamorig:LeftUpLeg": "LeftLeg",
    "mixamorig:LeftLeg": "LeftShin",
    "mixamorig:LeftFoot": "LeftFoot",
    "mixamorig:LeftToeBase": "LeftToeBase",
    "mixamorig:RightUpLeg": "RightLeg",
    "mixamorig:RightLeg": "RightShin",
    "mixamorig:RightFoot": "RightFoot",
    "mixamorig:RightToeBase": "RightToeBase",
}

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

for mix_name, bvh_name in BONE_MAPPING.items():
    pb = char_arm.pose.bones.get(mix_name)
    if pb and bvh_name in bvh_arm.pose.bones:
        con_rot = pb.constraints.new(type='COPY_ROTATION')
        con_rot.target = bvh_arm
        con_rot.subtarget = bvh_name
        con_rot.target_space = 'LOCAL'
        con_rot.owner_space = 'LOCAL'

        if mix_name == "mixamorig:Hips":
            con_loc = pb.constraints.new(type='COPY_LOCATION')
            con_loc.target = bvh_arm
            con_loc.subtarget = bvh_name
            con_loc.target_space = 'LOCAL'
            con_loc.owner_space = 'LOCAL'

# Find action frame range
action = bvh_arm.animation_data.action
start_frame = int(action.frame_range[0])
end_frame = int(action.frame_range[1])

print(f"Baking frames {start_frame} to {end_frame}...")

bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(
    frame_start=start_frame,
    frame_end=end_frame,
    step=1,
    only_selected=False,
    visual_keying=True,
    clear_constraints=True,
    clear_parents=False,
    use_current_action=False,
    bake_types={'POSE'}
)

bpy.ops.object.mode_set(mode='OBJECT')

# Remove BVH armature
if bvh_arm.animation_data and bvh_arm.animation_data.action:
    bpy.data.actions.remove(bvh_arm.animation_data.action, do_unlink=True)
bpy.data.objects.remove(bvh_arm, do_unlink=True)

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

print(f"[SUCCESS] BVH Retarget Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
