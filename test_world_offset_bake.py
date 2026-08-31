import bpy
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
motion_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_world_offset_test.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_world_offset_test.fbx"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

# Apply scale and rotation so Armature object transform is clean
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Import Motion GLB
pre_objects = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=motion_path)
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre_objects}

# Find frame range
start_frame = 0
end_frame = 60
for o in motion_objs.values():
    if o.animation_data and o.animation_data.action:
        start_frame = int(o.animation_data.action.frame_range[0])
        end_frame = int(o.animation_data.action.frame_range[1])
        break

print(f"Motion frame range: {start_frame} to {end_frame}")

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

# 3. Add WORLD OFFSET constraints
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Go to frame 0 so rest alignment is captured
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()

for mix_name, soma_name in BONE_MAPPING.items():
    char_bone = None
    for pb in char_arm.pose.bones:
        if pb.name.lower() in (mix_name.lower(), mix_name.replace("mixamorig:", "").lower()):
            char_bone = pb
            break

    if char_bone and soma_name in motion_objs:
        src_obj = motion_objs[soma_name]

        # Copy Rotation in WORLD space with OFFSET
        con_rot = char_bone.constraints.new(type='COPY_ROTATION')
        con_rot.target = src_obj
        con_rot.mix_mode = 'OFFSET'
        con_rot.target_space = 'WORLD'
        con_rot.owner_space = 'WORLD'

        # For Hips, also copy Location in WORLD space with OFFSET
        if "hip" in mix_name.lower():
            con_loc = char_bone.constraints.new(type='COPY_LOCATION')
            con_loc.target = src_obj
            # We use target offset or delta
            con_loc.target_space = 'WORLD'
            con_loc.owner_space = 'WORLD'
            con_loc.use_offset = True

# 4. Bake Action
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

# Remove motion objects
for o in motion_objs.values():
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o, do_unlink=True)

# Export
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
