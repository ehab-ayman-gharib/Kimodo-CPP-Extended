import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)

glb_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\top3d_thinking.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)
src_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

bpy.context.scene.frame_set(105)
bpy.context.view_layer.update()

print("--- SOURCE ARMATURE POSE AT FRAME 105 IN BLENDER ---")
for pb in src_arm.pose.bones:
    if any(k in pb.name for k in ["Head", "LeftHand", "RightHand", "LeftForeArm", "RightForeArm"]):
        w_mat = src_arm.matrix_world @ pb.matrix
        print(f"  {pb.name}: pos={w_mat.to_translation()}, quat={w_mat.to_quaternion()}")
