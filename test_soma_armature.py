import bpy
import struct
import numpy as np
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

# SOMA 30 Definition
SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]
SOMA30_OFFSETS = [[0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]]

# 1. Create SOMA Armature
arm_data = bpy.data.armatures.new("SOMA_Armature_Data")
soma_arm = bpy.data.objects.new("SOMA_Armature", arm_data)
bpy.context.collection.objects.link(soma_arm)
bpy.context.view_layer.objects.active = soma_arm
bpy.ops.object.mode_set(mode='EDIT')

edit_bones = {}
# Compute absolute positions in rest pose
abs_pos = [[0,0,0] for _ in range(len(SOMA30_NAMES))]
for i in range(len(SOMA30_NAMES)):
    p = SOMA30_PARENTS[i]
    off = SOMA30_OFFSETS[i]
    if p < 0:
        abs_pos[i] = [off[0], off[1], off[2]]
    else:
        abs_pos[i] = [abs_pos[p][0] + off[0], abs_pos[p][1] + off[1], abs_pos[p][2] + off[2]]

for i, name in enumerate(SOMA30_NAMES):
    eb = arm_data.edit_bones.new(name)
    eb.head = abs_pos[i]
    # tail slightly offset along offset or child
    eb.tail = [abs_pos[i][0], abs_pos[i][1] + 0.05, abs_pos[i][2]]
    edit_bones[name] = eb

for i, name in enumerate(SOMA30_NAMES):
    p = SOMA30_PARENTS[i]
    if p >= 0:
        edit_bones[name].parent = edit_bones[SOMA30_NAMES[p]]

bpy.ops.object.mode_set(mode='OBJECT')

print(f"Created SOMA Armature with {len(soma_arm.pose.bones)} bones.")

# 2. Read raw binary motions
item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)

num_frames = len(root_data) // 3
joints = len(SOMA30_NAMES)
rot_data = rot_data.reshape((num_frames, joints, 4))
root_data = root_data.reshape((num_frames, 3))

print(f"Loaded {num_frames} frames from binary motion files.")

bpy.context.view_layer.objects.active = soma_arm
bpy.ops.object.mode_set(mode='POSE')

for f in range(num_frames):
    # Root position: SOMA is Y-up, in Blender Y-up means Y=up or Z=up
    rx, ry, rz = root_data[f]
    soma_arm.pose.bones["Hips"].location = (rx, ry, rz)
    soma_arm.pose.bones["Hips"].keyframe_insert(data_path="location", frame=f)

    for j, name in enumerate(SOMA30_NAMES):
        pb = soma_arm.pose.bones[name]
        pb.rotation_mode = 'QUATERNION'
        # Quaternion is (x, y, z, w) -> Blender expects (w, x, y, z)
        qx, qy, qz, qw = rot_data[f, j]
        pb.rotation_quaternion = (qw, qx, qy, qz)
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# Export SOMA armature to test GLB
bpy.ops.export_scene.gltf(
    filepath=r"E:\Kimodo-CPP\demo-output\5e15f54638196203\soma_armature_test.glb",
    export_format='GLB',
    export_animations=True
)
print("Saved soma_armature_test.glb successfully!")
