import bpy
import numpy as np

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Load exported Remy_animated.fbx
bpy.ops.import_scene.fbx(filepath=r"E:\Kimodo-CPP\Remy_animated.fbx")
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("Exported Armature:", char_arm.name)

# 2. Load original animation.glb
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb")
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre and o.type == 'EMPTY'}

for f in [0, 30]:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    print(f"\n================ FRAME {f} ================")
    
    # Compare Hips, LeftArm, RightArm, LeftUpLeg, RightUpLeg
    pairs = [
        ("mixamorig:Hips", "Hips"),
        ("mixamorig:LeftArm", "LeftArm"),
        ("mixamorig:RightArm", "RightArm"),
        ("mixamorig:LeftUpLeg", "LeftLeg"),
        ("mixamorig:RightUpLeg", "RightLeg"),
    ]
    for mix_name, soma_name in pairs:
        pb = char_arm.pose.bones.get(mix_name)
        m_obj = motion_objs.get(soma_name)
        if pb and m_obj:
            pb_w = char_arm.matrix_world @ pb.matrix
            mo_w = m_obj.matrix_world
            print(f"[{mix_name} vs {soma_name}]")
            print(f"  Character world pos: {pb_w.to_translation()}")
            print(f"  Motion obj world pos: {mo_w.to_translation()}")
            print(f"  Character world rot: {pb_w.to_quaternion()}")
            print(f"  Motion obj world rot: {mo_w.to_quaternion()}")
