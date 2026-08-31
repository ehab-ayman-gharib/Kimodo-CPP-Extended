import bpy
import mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
motion_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Import Motion
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=motion_path)
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre}

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Go to frame 0
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()

hips_pb = char_arm.pose.bones.get("mixamorig:Hips")
char_hips_rest_world = (char_arm.matrix_world @ hips_pb.matrix).to_translation().copy()
motion_hips_rest_world = motion_objs["Hips"].matrix_world.to_translation().copy()

print("Char Hips Rest World Pos:", char_hips_rest_world)
print("Motion Hips Rest World Pos:", motion_hips_rest_world)

for f in [0, 15, 30, 60]:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()

    curr_m_trans = motion_objs["Hips"].matrix_world.to_translation()
    delta_trans = curr_m_trans - motion_hips_rest_world

    # Target World Position: X is right/left, Y is forward/backward, Z is up/down
    target_world_pos = char_hips_rest_world + delta_trans
    
    # Set hips matrix translation in armature space
    mat = hips_pb.matrix.copy()
    mat.translation = target_world_pos
    hips_pb.matrix = mat
    bpy.context.view_layer.update()

    print(f"Frame {f}: delta_trans={delta_trans}, evaluated_pos={(char_arm.matrix_world @ hips_pb.matrix).to_translation()}")
