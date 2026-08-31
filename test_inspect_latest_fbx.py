import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r"E:\Kimodo-CPP\Remy_animated.fbx")

arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
print("Armature matrix_world:\n", arm.matrix_world)

for f in [0, 15, 30, 60]:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    pb = arm.pose.bones['mixamorig:Hips']
    pos_local = pb.location
    pos_world = (arm.matrix_world @ pb.matrix).to_translation()
    print(f"Frame {f}: local_loc={pos_local}, world_pos={pos_world}")
