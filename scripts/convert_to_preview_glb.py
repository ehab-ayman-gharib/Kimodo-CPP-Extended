import sys
from pathlib import Path
import bpy

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    if len(argv) < 2:
        print("Usage: blender -b -P convert_to_preview_glb.py -- <input_model> <output_glb>")
        sys.exit(1)

    in_path = Path(argv[0]).resolve()
    out_path = Path(argv[1]).resolve()

    print(f"[Convert Preview] Loading input: {in_path}")
    print(f"[Convert Preview] Target output: {out_path}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = in_path.suffix.lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(in_path))
    elif ext in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=str(in_path))
    elif ext == ".obj":
        try:
            bpy.ops.wm.obj_import(filepath=str(in_path))
        except Exception:
            bpy.ops.import_scene.obj(filepath=str(in_path))

    # Fix transparency and ensure opaque textures
    for mat in bpy.data.materials:
        if mat and mat.node_tree:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                alpha_sock = bsdf.inputs.get('Alpha')
                if alpha_sock and alpha_sock.is_linked:
                    for link in list(alpha_sock.links):
                        mat.node_tree.links.remove(link)
                    alpha_sock.default_value = 1.0
            if hasattr(mat, 'blend_method'):
                mat.blend_method = 'OPAQUE'

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format='GLB',
        export_animations=False,
        export_current_frame=False,
        export_draco_mesh_compression_enable=False
    )
    print(f"[Convert Preview] Successfully exported preview GLB to {out_path}")
    sys.exit(0)

if __name__ == "__main__":
    main()
