import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.resolve()))
import bpy
import mathutils

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

    # Check if target is a 3ds Max Biped rig. If so, delegate to convert_biped_to_standard
    arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    is_biped = any(any(b.name.lower().startswith('bip') and any(k in b.name.lower() for k in ['pelvis', 'spine', 'thigh', 'calf', 'upperarm', 'forearm']) for b in arm.data.bones) for arm in arm_objs)
    if is_biped:
        from convert_biped_to_standard import convert_biped
        convert_biped(in_path, out_path)
        sys.exit(0)

    # Remove non-character extra objects (like default cube, camera, lights, extra icospheres)
    for o in list(bpy.data.objects):
        if o.name in ['Camera', 'Light', 'Cube'] or 'ico' in o.name.lower():
            bpy.data.objects.remove(o, do_unlink=True)

    # Clear any corrupt/split FBX action tracks so preview displays the clean, pristine Rest Pose / T-Pose
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for o in bpy.data.objects:
        if o.animation_data:
            o.animation_data_clear()

    # Apply root rotation transforms so character stands upright in GLTF/GLB preview (only needed for FBX)
    if ext == ".fbx":
        for o in bpy.data.objects:
            o.select_set(True)
        arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
        if arm_objs:
            bpy.context.view_layer.objects.active = arm_objs[0]
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

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
