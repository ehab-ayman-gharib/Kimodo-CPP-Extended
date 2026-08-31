import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)

fbx_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\Remy_constraint_bake.fbx"
bpy.ops.import_scene.fbx(filepath=fbx_path)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

print("Imported objects in FBX:")
for o in bpy.data.objects:
    print(f"  Object: {o.name} ({o.type})")

bpy.context.scene.frame_set(105)
bpy.context.view_layer.update()

print("\n--- EVALUATING CONSTRAINT BAKE AT FRAME 105 ---")
for pb in arm.pose.bones:
    if any(k in pb.name for k in ["Head", "LeftHand", "RightHand", "LeftForeArm", "RightForeArm"]):
        w_mat = arm.matrix_world @ pb.matrix
        print(f"  {pb.name}: pos={w_mat.to_translation()}")
