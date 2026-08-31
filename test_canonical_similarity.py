import bpy
import numpy as np
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_canonical_test.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_canonical_test.fbx"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Read motion data
item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)
num_frames = len(root_data) // 3
rot_data = rot_data.reshape((num_frames, 30, 4))
root_data = root_data.reshape((num_frames, 3))

BONE_MAPPING = {
    "mixamorig:Hips": 0,
    "mixamorig:Spine": 1,
    "mixamorig:Spine1": 2,
    "mixamorig:Spine2": 3,
    "mixamorig:Neck": 4,
    "mixamorig:Head": 6,
    "mixamorig:LeftShoulder": 10,
    "mixamorig:LeftArm": 11,
    "mixamorig:LeftForeArm": 12,
    "mixamorig:LeftHand": 13,
    "mixamorig:RightShoulder": 16,
    "mixamorig:RightArm": 17,
    "mixamorig:RightForeArm": 18,
    "mixamorig:RightHand": 19,
    "mixamorig:LeftUpLeg": 22,
    "mixamorig:LeftLeg": 23,
    "mixamorig:LeftFoot": 24,
    "mixamorig:LeftToeBase": 25,
    "mixamorig:RightUpLeg": 26,
    "mixamorig:RightLeg": 27,
    "mixamorig:RightFoot": 28,
    "mixamorig:RightToeBase": 29,
}

# In SOMA (SMPL-X basis):
# Canonical rest orientation of each joint is identity (T-pose).
# In Mixamo:
# Each bone has a rest orientation matrix_local.to_quaternion() relative to parent.
# Therefore, the basis transformation from canonical SMPL-X delta to Mixamo local delta is:
# Q_mixamo_delta = R_rest^-1 @ Q_soma_delta @ R_rest

basis_transforms = {}
for mix_name, s_idx in BONE_MAPPING.items():
    if mix_name in char_arm.data.bones:
        b = char_arm.data.bones[mix_name]
        # Bone's rest orientation relative to parent in rest pose
        if b.parent:
            rest_local_mat = b.parent.matrix_local.inverted() @ b.matrix_local
        else:
            rest_local_mat = b.matrix_local
        r_rest = rest_local_mat.to_quaternion()
        basis_transforms[mix_name] = r_rest

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

hips_pb = char_arm.pose.bones.get("mixamorig:Hips")
hips_rest_loc = hips_pb.location.copy() if hips_pb else mathutils.Vector((0,0,0))
root_start = root_data[0].copy()

for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

print(f"Applying {num_frames} frames via Canonical Similarity Transform...")

for f in range(num_frames):
    # 1. Hips Translation Delta
    if hips_pb:
        dx = root_data[f, 0] - root_start[0]
        dy = root_data[f, 1] - root_start[1]
        dz = -(root_data[f, 2] - root_start[2])

        hips_pb.location = (
            hips_rest_loc[0] + dx,
            hips_rest_loc[1] + dy,
            hips_rest_loc[2] + dz
        )
        hips_pb.keyframe_insert(data_path="location", frame=f)

    # 2. Local Rotations transformed via R_rest^-1 @ Q_delta @ R_rest
    for mix_name, s_idx in BONE_MAPPING.items():
        pb = char_arm.pose.bones.get(mix_name)
        if pb and mix_name in basis_transforms:
            R = basis_transforms[mix_name]

            qx, qy, qz, qw = rot_data[f, s_idx]
            q_curr = mathutils.Quaternion((qw, qx, qy, qz))

            rx, ry, rz, rw = rot_data[0, s_idx]
            q_rest = mathutils.Quaternion((rw, rx, ry, rz))

            # Delta rotation
            q_delta = q_curr @ q_rest.inverted()

            # Dampen shoulder clavicle rotation slightly (0.4) to match Mixamo clavicle rigging
            if "shoulder" in mix_name.lower():
                q_delta = mathutils.Quaternion((1,0,0,0)).slerp(q_delta, 0.4)

            # Transform delta to Mixamo's local bone basis
            q_mixamo_local = R.inverted() @ q_delta @ R

            pb.rotation_quaternion = q_mixamo_local
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

print(f"[SUCCESS] Canonical Similarity Bake Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
