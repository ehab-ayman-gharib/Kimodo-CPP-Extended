import bpy
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Import Source GLB
glb_path = r"E:\Kimodo-CPP\demo-output\f70d7468257052d0\top3d_thinking.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)
src_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
src_arm.name = "Source_Armature"

# 2. Import Target FBX
fbx_path = r"E:\Kimodo-CPP\Remy.fbx"
bpy.ops.import_scene.fbx(filepath=fbx_path)
tgt_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != src_arm][0]
tgt_arm.name = "Target_Armature"

print(f"Source Armature: {src_arm.name}, Bones: {len(src_arm.data.bones)}")
for b in src_arm.data.bones[:10]:
    print(f"  Src bone: {b.name}, head={b.head_local}, tail={b.tail_local}")

print(f"\nTarget Armature: {tgt_arm.name}, Bones: {len(tgt_arm.data.bones)}")
for b in tgt_arm.data.bones[:10]:
    print(f"  Tgt bone: {b.name}, head={b.head_local}, tail={b.tail_local}")
