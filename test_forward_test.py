import bpy
import numpy as np
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_forward_test.glb"

# 1. Load Remy
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Build SOMA Armature
SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]
SOMA30_OFFSETS = [[0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]]

arm_data = bpy.data.armatures.new("SOMA_Armature_Data")
soma_arm = bpy.data.objects.new("SOMA_Armature", arm_data)
bpy.context.collection.objects.link(soma_arm)
bpy.context.view_layer.objects.active = soma_arm
bpy.ops.object.mode_set(mode='EDIT')

abs_pos = [[0,0,0] for _ in range(len(SOMA30_NAMES))]
for i in range(len(SOMA30_NAMES)):
    p = SOMA30_PARENTS[i]
    off = SOMA30_OFFSETS[i]
    if p < 0:
        abs_pos[i] = [off[0], off[1], off[2]]
    else:
        abs_pos[i] = [abs_pos[p][0] + off[0], abs_pos[p][1] + off[1], abs_pos[p][2] + off[2]]

edit_bones = {}
for i, name in enumerate(SOMA30_NAMES):
    eb = arm_data.edit_bones.new(name)
    eb.head = abs_pos[i]
    eb.tail = [abs_pos[i][0], abs_pos[i][1] + 0.05, abs_pos[i][2]]
    edit_bones[name] = eb

for i, name in enumerate(SOMA30_NAMES):
    p = SOMA30_PARENTS[i]
    if p >= 0:
        edit_bones[name].parent = edit_bones[SOMA30_NAMES[p]]

bpy.ops.object.mode_set(mode='OBJECT')

# Load keyframes to SOMA Armature
item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)
num_frames = len(root_data) // 3
rot_data = rot_data.reshape((num_frames, len(SOMA30_NAMES), 4))
root_data = root_data.reshape((num_frames, 3))

bpy.context.view_layer.objects.active = soma_arm
bpy.ops.object.mode_set(mode='POSE')

root_start = root_data[0].copy()

for f in range(num_frames):
    # SOMA root positions: x, y, z
    # Since SOMA_Armature is constructed in SOMA coordinate space:
    # x is right, y is up, z is forward
    dx = root_data[f, 0] - root_start[0]
    dy = root_data[f, 1] - root_start[1]
    dz = root_data[f, 2] - root_start[2]
    
    soma_arm.pose.bones["Hips"].location = (dx, dy, dz)
    soma_arm.pose.bones["Hips"].keyframe_insert(data_path="location", frame=f)

    for j, name in enumerate(SOMA30_NAMES):
        pb = soma_arm.pose.bones[name]
        pb.rotation_mode = 'QUATERNION'
        qx, qy, qz, qw = rot_data[f, j]
        pb.rotation_quaternion = (qw, qx, qy, qz)
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# 3. Retarget SOMA -> Character Armature using Local Offset Constraints
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

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

for mix_name, soma_name in BONE_MAPPING.items():
    char_bone = None
    for pb in char_arm.pose.bones:
        if pb.name.lower() in (mix_name.lower(), mix_name.replace("mixamorig:", "").lower()):
            char_bone = pb
            break

    if char_bone and soma_name in soma_arm.pose.bones:
        con_rot = char_bone.constraints.new(type='COPY_ROTATION')
        con_rot.target = soma_arm
        con_rot.subtarget = soma_name
        con_rot.mix_mode = 'OFFSET'
        con_rot.target_space = 'LOCAL'
        con_rot.owner_space = 'LOCAL'

        if mix_name == "mixamorig:Hips":
            con_loc = char_bone.constraints.new(type='COPY_LOCATION')
            con_loc.target = soma_arm
            con_loc.subtarget = soma_name
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

# Remove temporary SOMA armature and orphaned actions
if soma_arm.animation_data and soma_arm.animation_data.action:
    bpy.data.actions.remove(soma_arm.animation_data.action, do_unlink=True)
bpy.data.objects.remove(soma_arm, do_unlink=True)

# Export
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_animations=True,
    export_current_frame=False
)
print(f"Exported forward test GLB: {output_glb}")
