import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)

fbx_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_offset_retarget.fbx"
bpy.ops.import_scene.fbx(filepath=fbx_path)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

for f in [0, 105]:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    print(f"\n--- FRAME {f} EVALUATION ---")
    for bname in ["mixamorig:Head", "mixamorig:LeftHand", "mixamorig:RightHand", "mixamorig:LeftFoot", "mixamorig:RightFoot"]:
        pb = arm.pose.bones.get(bname)
        if pb:
            pos = (arm.matrix_world @ pb.matrix).to_translation()
            print(f"  {bname}: pos={pos}")
