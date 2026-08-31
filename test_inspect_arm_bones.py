import bpy
import mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

print("Mixamo LeftArm edit bone matrix:\n", char_arm.data.bones['mixamorig:LeftArm'].matrix_local)
print("Mixamo RightArm edit bone matrix:\n", char_arm.data.bones['mixamorig:RightArm'].matrix_local)
print("Mixamo LeftForeArm edit bone matrix:\n", char_arm.data.bones['mixamorig:LeftForeArm'].matrix_local)
print("Mixamo RightForeArm edit bone matrix:\n", char_arm.data.bones['mixamorig:RightForeArm'].matrix_local)
