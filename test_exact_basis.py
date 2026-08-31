import bpy
import numpy as np
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_exact_basis_test.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_exact_basis_test.fbx"

# 1. Load Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. SOMA Skeleton Definition
SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]

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

# Duplicate Character Armature to serve as the exact Reference Rig!
# Since it has the 100% exact bone rolls, rest poses, and hierarchies of the character:
soma_arm = char_arm.copy()
soma_arm.data = char_arm.data.copy()
soma_arm.name = "Reference_Drive_Armature"
bpy.context.collection.objects.link(soma_arm)

# Read motion streams
item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)
num_frames = len(root_data) // 3
rot_data = rot_data.reshape((num_frames, len(SOMA30_NAMES), 4))
root_data = root_data.reshape((num_frames, 3))

# Animate Reference Rig directly
bpy.context.view_layer.objects.active = soma_arm
bpy.ops.object.mode_set(mode='POSE')

root_start = root_data[0].copy()
hips_pb = None
for pb in soma_arm.pose.bones:
    if "hip" in pb.name.lower() or "pelvis" in pb.name.lower():
        hips_pb = pb
        break

hips_rest_loc = hips_pb.location.copy() if hips_pb else (0, 0, 0)

for pb in soma_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

# Map SOMA name to index
name_to_idx = {name: i for i, name in enumerate(SOMA30_NAMES)}

for f in range(num_frames):
    dx = root_data[f, 0] - root_start[0]
    dy = root_data[f, 1] - root_start[1]
    dz = -(root_data[f, 2] - root_start[2])
    
    if hips_pb:
        # In Mixamo/FBX standard space: Y is up, -Z is forward
        hips_pb.location = (
            hips_rest_loc[0] + dx,
            hips_rest_loc[1] + dy,
            hips_rest_loc[2] + dz
        )
        hips_pb.keyframe_insert(data_path="location", frame=f)

    for mix_name, soma_name in BONE_MAPPING.items():
        pb = soma_arm.pose.bones.get(mix_name)
        if pb and soma_name in name_to_idx:
            s_idx = name_to_idx[soma_name]
            qx, qy, qz, qw = rot_data[f, s_idx]
            pb.rotation_quaternion = (qw, qx, qy, qz)
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# 3. Retarget Reference -> Character Armature
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

for mix_name in BONE_MAPPING.keys():
    pb = char_arm.pose.bones.get(mix_name)
    if pb and mix_name in soma_arm.pose.bones:
        con_rot = pb.constraints.new(type='COPY_ROTATION')
        con_rot.target = soma_arm
        con_rot.subtarget = mix_name
        con_rot.target_space = 'LOCAL'
        con_rot.owner_space = 'LOCAL'

        if "hip" in mix_name.lower():
            con_loc = pb.constraints.new(type='COPY_LOCATION')
            con_loc.target = soma_arm
            con_loc.subtarget = mix_name
            con_loc.target_space = 'LOCAL'
            con_loc.owner_space = 'LOCAL'

# Select all and Bake Action
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(
    frame_start=0,
    frame_end=num_frames - 1,
    step=1,
    only_selected=False,
    visual_keying=True,
    clear_constraints=True,
    clear_parents=False,
    use_current_action=False,
    bake_types={'POSE'}
)

bpy.ops.object.mode_set(mode='OBJECT')

# Remove duplicate reference rig
if soma_arm.animation_data and soma_arm.animation_data.action:
    bpy.data.actions.remove(soma_arm.animation_data.action, do_unlink=True)
bpy.data.objects.remove(soma_arm, do_unlink=True)

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

print(f"[SUCCESS] Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
