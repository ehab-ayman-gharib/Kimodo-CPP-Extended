import bpy
import numpy as np
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Load Remy
char_path = r"E:\Kimodo-CPP\Remy.fbx"
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. SOMA definition
SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]
SOMA30_OFFSETS = [[0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]]

abs_pos = [[0,0,0] for _ in range(len(SOMA30_NAMES))]
for i in range(len(SOMA30_NAMES)):
    p = SOMA30_PARENTS[i]
    off = SOMA30_OFFSETS[i]
    if p < 0:
        abs_pos[i] = [off[0], off[1], off[2]]
    else:
        abs_pos[i] = [abs_pos[p][0] + off[0], abs_pos[p][1] + off[1], abs_pos[p][2] + off[2]]

PRIMARY_CHILD = {}
for i, p in enumerate(SOMA30_PARENTS):
    if p >= 0 and p not in PRIMARY_CHILD:
        PRIMARY_CHILD[p] = i

arm_data = bpy.data.armatures.new("SOMA_Armature_Data")
soma_arm = bpy.data.objects.new("SOMA_Armature", arm_data)
bpy.context.collection.objects.link(soma_arm)
bpy.context.view_layer.objects.active = soma_arm
bpy.ops.object.mode_set(mode='EDIT')

for i, name in enumerate(SOMA30_NAMES):
    eb = arm_data.edit_bones.new(name)
    eb.head = abs_pos[i]
    if i in PRIMARY_CHILD:
        eb.tail = abs_pos[PRIMARY_CHILD[i]]
    else:
        p = SOMA30_PARENTS[i]
        if p >= 0:
            dir_v = [abs_pos[i][k] - abs_pos[p][k] for k in range(3)]
            eb.tail = [abs_pos[i][k] + dir_v[k] * 0.3 for k in range(3)]
        else:
            eb.tail = [abs_pos[i][0], abs_pos[i][1] + 0.1, abs_pos[i][2]]

for i, name in enumerate(SOMA30_NAMES):
    p = SOMA30_PARENTS[i]
    if p >= 0:
        arm_data.edit_bones[name].parent = arm_data.edit_bones[SOMA30_NAMES[p]]

bpy.ops.object.mode_set(mode='OBJECT')

print("--- REST MATRICES IN LOCAL SPACE ---")
for mix_name, soma_name in [("mixamorig:LeftArm", "LeftArm"), ("mixamorig:RightArm", "RightArm"), ("mixamorig:LeftUpLeg", "LeftLeg")]:
    m_bone = char_arm.data.bones[mix_name]
    s_bone = soma_arm.data.bones[soma_name]
    print(f"\n{mix_name} matrix_local:\n{m_bone.matrix_local.to_quaternion()}")
    print(f"{soma_name} matrix_local:\n{s_bone.matrix_local.to_quaternion()}")
