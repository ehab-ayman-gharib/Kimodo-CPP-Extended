import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_similarity_test.glb")

arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("Imported Armature:", arm.name)

for f in [0, 15, 30]:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    print(f"\n--- FRAME {f} ---")
    for bname in ['mixamorig:Hips', 'mixamorig:LeftArm', 'mixamorig:RightArm', 'mixamorig:LeftUpLeg', 'mixamorig:RightUpLeg']:
        pb = arm.pose.bones.get(bname)
        if pb:
            pos = (arm.matrix_world @ pb.matrix).to_translation()
            rot = (arm.matrix_world @ pb.matrix).to_quaternion()
            print(f"  {bname}: pos={pos}, rot={rot}")
