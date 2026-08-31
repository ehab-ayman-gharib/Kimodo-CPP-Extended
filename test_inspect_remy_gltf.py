import bpy
import json

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r"E:\Kimodo-CPP\Remy.fbx")

# Export clean un-animated GLB of Remy
bpy.ops.export_scene.gltf(
    filepath=r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_rest.glb",
    export_format='GLB'
)

# Inspect glTF json
with open(r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_rest.glb", "rb") as f:
    header = f.read(12)
    chunk0_hdr = f.read(8)
    json_len = int.from_bytes(chunk0_hdr[:4], 'little')
    json_data = json.loads(f.read(json_len))

print("Nodes in Remy_rest.glb:")
for i, n in enumerate(json_data.get("nodes", [])):
    if "mixamorig" in n.get("name", "").lower():
        print(f"  Node {i}: name='{n.get('name')}', translation={n.get('translation')}, rotation={n.get('rotation')}, children={n.get('children')}")
