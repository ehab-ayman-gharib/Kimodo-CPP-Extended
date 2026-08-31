import bpy
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Load Character
char_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\upload_character.fbx"
bpy.ops.import_scene.fbx(filepath=char_path)

char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

# 2. Load Motion
motion_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb"
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=motion_path)
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre}

print(f"Char Armature: {char_arm.name}")
print(f"Motion Nodes: {list(motion_objs.keys())[:10]}")

# Let's inspect rest-pose matrices
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

for bname in ['mixamorig:Hips', 'mixamorig:LeftUpLeg', 'mixamorig:LeftArm']:
    if bname in char_arm.pose.bones:
        pb = char_arm.pose.bones[bname]
        print(f"Bone {bname} rest matrix:\n{pb.bone.matrix_local}")
