import bpy
import mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
motion_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb"
output_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_track_test.glb"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

# Apply scale and rotation to character armature so matrix_world is Identity (1.0 scale, no rotation offset)
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Import Motion
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=motion_path)
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre and o.type == 'EMPTY'}

# Joint aiming pairs: (character_bone_name, target_child_empty_name)
TRACK_PAIRS = [
    ("mixamorig:Spine", "Chest"),
    ("mixamorig:Spine1", "Chest"),
    ("mixamorig:Spine2", "Neck1"),
    ("mixamorig:Neck", "Head"),
    ("mixamorig:Head", "Head"),
    ("mixamorig:LeftShoulder", "LeftArm"),
    ("mixamorig:LeftArm", "LeftForeArm"),
    ("mixamorig:LeftForeArm", "LeftHand"),
    ("mixamorig:RightShoulder", "RightArm"),
    ("mixamorig:RightArm", "RightForeArm"),
    ("mixamorig:RightForeArm", "RightHand"),
    ("mixamorig:LeftUpLeg", "LeftShin"),
    ("mixamorig:LeftLeg", "LeftFoot"),
    ("mixamorig:LeftFoot", "LeftToeBase"),
    ("mixamorig:RightUpLeg", "RightShin"),
    ("mixamorig:RightLeg", "RightFoot"),
    ("mixamorig:RightFoot", "RightToeBase"),
]

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Root Hips Constraint
hips_bone = char_arm.pose.bones.get("mixamorig:Hips")
if hips_bone and "Hips" in motion_objs:
    # Copy location from Hips empty
    con_loc = hips_bone.constraints.new(type='COPY_LOCATION')
    con_loc.target = motion_objs["Hips"]
    con_loc.target_space = 'WORLD'
    con_loc.owner_space = 'WORLD'

# Damped Track Constraints for all limb/spine bones
for bname, target_name in TRACK_PAIRS:
    if bname in char_arm.pose.bones and target_name in motion_objs:
        pb = char_arm.pose.bones[bname]
        con = pb.constraints.new(type='DAMPED_TRACK')
        con.target = motion_objs[target_name]
        con.track_axis = 'TRACK_Y' # Primary bone axis in Blender is +Y
        con.target_space = 'WORLD'
        con.owner_space = 'WORLD'

# Find animation frame range
start_frame = 0
end_frame = 60
for o in motion_objs.values():
    if o.animation_data and o.animation_data.action:
        start_frame = int(o.animation_data.action.frame_range[0])
        end_frame = int(o.animation_data.action.frame_range[1])
        break

print(f"Baking frames {start_frame} to {end_frame}...")

# Select all pose bones
bpy.ops.pose.select_all(action='SELECT')

# Bake with visual keying and remove constraints
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

# Export GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_current_frame=False
)
print(f"Bake completed successfully: {output_path}")
