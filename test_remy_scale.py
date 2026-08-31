import bpy
import mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Load Remy.fbx
bpy.ops.import_scene.fbx(filepath=r"E:\Kimodo-CPP\Remy.fbx")
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("Armature:", char_arm.name)
print("Armature scale:", char_arm.scale)
print("Armature matrix_world:\n", char_arm.matrix_world)

# 2. Load Motion GLB
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb")
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre and o.type == 'EMPTY'}
print("Hips motion pos at f=0:", motion_objs['Hips'].matrix_world.to_translation())

bpy.context.scene.frame_set(30)
bpy.context.view_layer.update()
print("Hips motion pos at f=30:", motion_objs['Hips'].matrix_world.to_translation())
