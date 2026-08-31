import bpy
import numpy as np
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_world_retarget.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_world_retarget.fbx"

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
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]

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

# Helper to multiply quaternions in (w, x, y, z)
def quat_mult(q1, q2):
    return (q1 @ q2)

# Helper to rotate vector by quaternion
def quat_rot(q, v):
    return (q @ mathutils.Vector(v))

# 3. Compute SOMA Global Rotations for all frames
# SOMA quaternions: (x, y, z, w) -> mathutils.Quaternion((w, x, y, z))
soma_global_quats = []
for f in range(num_frames):
    f_globals = [None] * len(SOMA30_NAMES)
    for j in range(len(SOMA30_NAMES)):
        qx, qy, qz, qw = rot_data[f, j]
        q_local = mathutils.Quaternion((qw, qx, qy, qz))
        p = SOMA30_PARENTS[j]
        if p < 0:
            f_globals[j] = q_local
        else:
            f_globals[j] = f_globals[p] @ q_local
    soma_global_quats.append(f_globals)

# 4. Map to Character Pose Bones
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Record rest matrix_local for each character bone
char_bones = {}
char_rest_mats = {}
for mix_name in BONE_MAPPING.keys():
    for pb in char_arm.pose.bones:
        if pb.name.lower() in (mix_name.lower(), mix_name.replace("mixamorig:", "").lower()):
            char_bones[mix_name] = pb
            char_rest_mats[mix_name] = pb.bone.matrix_local.copy()
            break

for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

hips_pb = char_bones.get("mixamorig:Hips")
hips_rest_loc = hips_pb.location.copy() if hips_pb else mathutils.Vector((0,0,0))
root_start_pos = root_data[0].copy()

# Coordinate system rotation to convert glTF Y-up to Blender Z-up
# 90 deg rotation around X
q_gltf_to_blender = mathutils.Euler((1.57079632679, 0, 0), 'XYZ').to_quaternion()
q_blender_to_gltf = q_gltf_to_blender.inverted()

for f in range(num_frames):
    bpy.context.scene.frame_set(f)

    # 1. Hips translation
    if hips_pb:
        dx = root_data[f, 0] - root_start_pos[0]
        dy = root_data[f, 1] - root_start_pos[1]
        dz = root_data[f, 2] - root_start_pos[2]
        
        # glTF: +X right, +Y up, +Z forward
        # Blender: +X right, +Y forward, +Z up
        hips_pb.location = mathutils.Vector((
            hips_rest_loc.x + dx,
            hips_rest_loc.y + dz,
            hips_rest_loc.z + dy
        ))
        hips_pb.keyframe_insert(data_path="location", frame=f)

    # 2. For each bone, set world orientation using delta from rest
    for mix_name, soma_idx in BONE_MAPPING.items():
        if mix_name not in char_bones:
            continue
        
        pb = char_bones[mix_name]
        
        # SOMA global rotation at current frame vs frame 0
        q_soma_curr = soma_global_quats[f][soma_idx]
        q_soma_rest = soma_global_quats[0][soma_idx]
        
        # Delta global rotation in SOMA body space
        q_delta_soma = q_soma_curr @ q_soma_rest.inverted()
        
        # Convert delta to Blender coordinate space
        q_delta_blender = q_gltf_to_blender @ q_delta_soma @ q_blender_to_gltf
        
        # Apply delta to bone's rest world orientation
        # Bone rest matrix in world space (armature space)
        bone_rest_mat = char_rest_mats[mix_name]
        bone_rest_rot = bone_rest_mat.to_quaternion()
        
        target_world_rot = q_delta_blender @ bone_rest_rot
        
        # If bone has parent, calculate local rotation relative to parent's current pose
        if pb.parent and pb.parent.name in char_bones:
            parent_pb = pb.parent
            parent_curr_rot = parent_pb.matrix.to_quaternion()
            local_rot = parent_curr_rot.inverted() @ target_world_rot
        else:
            local_rot = target_world_rot
            
        pb.rotation_quaternion = local_rot
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

print(f"\n[DONE] Saved World Retargeted Models:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}\n")
