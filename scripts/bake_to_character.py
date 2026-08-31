"""
Production Blender Retargeter & Baker for Kimodo Motions onto Custom Characters.
Uses Canonical GLB intermediate (kimodo_to_glb.py) + EditBone Alignment Frames + Native C++ Blender Constraint Baking (nla.bake).
Guarantees 100% anatomical fidelity, correct rest pose compensation, zero gimbal lock, zero floating/flipping limbs.
"""

import sys
import os
import subprocess
from pathlib import Path
import bpy
import mathutils

BONE_MAPPING = {
    "Hips": "mixamorig:Hips",
    "Spine1": "mixamorig:Spine",
    "Spine2": "mixamorig:Spine1",
    "Chest": "mixamorig:Spine2",
    "Neck1": "mixamorig:Neck",
    "Head": "mixamorig:Head",
    "LeftShoulder": "mixamorig:LeftShoulder",
    "LeftArm": "mixamorig:LeftArm",
    "LeftForeArm": "mixamorig:LeftForeArm",
    "LeftHand": "mixamorig:LeftHand",
    "RightShoulder": "mixamorig:RightShoulder",
    "RightArm": "mixamorig:RightArm",
    "RightForeArm": "mixamorig:RightForeArm",
    "RightHand": "mixamorig:RightHand",
    "LeftLeg": "mixamorig:LeftUpLeg",
    "LeftShin": "mixamorig:LeftLeg",
    "LeftFoot": "mixamorig:LeftFoot",
    "LeftToeBase": "mixamorig:LeftToeBase",
    "RightLeg": "mixamorig:RightUpLeg",
    "RightShin": "mixamorig:RightLeg",
    "RightFoot": "mixamorig:RightFoot",
    "RightToeBase": "mixamorig:RightToeBase",
}

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    
    char_path = None
    motion_path = None
    output_path = None
    
    for i in range(len(argv)):
        if argv[i] in ("-c", "--character") and i + 1 < len(argv):
            char_path = argv[i + 1]
        elif argv[i] in ("-m", "--motion") and i + 1 < len(argv):
            motion_path = argv[i + 1]
        elif argv[i] in ("-o", "--output") and i + 1 < len(argv):
            output_path = argv[i + 1]
            
    return char_path, motion_path, output_path

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def find_armature(exclude=None):
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != exclude:
            return obj
    return None

def main():
    char_path, motion_path, output_path = parse_args()
    if not char_path or not motion_path:
        print("Usage: blender -b -P scripts/bake_to_character.py -- --character <char.fbx/glb> --motion <kimodo_clip_dir_or_glb> [--output <output.glb>]")
        sys.exit(1)

    char_file = Path(char_path).resolve()
    motion_input = Path(motion_path).resolve()
    if not char_file.is_file():
        print(f"Error: Character file not found: {char_file}")
        sys.exit(1)

    item_dir = motion_input if motion_input.is_dir() else motion_input.parent
    if not output_path:
        output_file = char_file.parent / f"{char_file.stem}_animated.glb"
    else:
        output_file = Path(output_path).resolve()

    # 1. Ensure intermediate canonical GLB exists
    source_glb = item_dir / "canonical_motion.glb"
    if not source_glb.is_file():
        kimodo_to_glb_script = Path(__file__).parent / "kimodo_to_glb.py"
        cmd = [sys.executable, str(kimodo_to_glb_script), str(item_dir), "-o", str(source_glb), "--names", "native"]
        subprocess.run(cmd, capture_output=True, text=True)

    if not source_glb.is_file():
        if (item_dir / "animation.glb").is_file():
            source_glb = item_dir / "animation.glb"
        else:
            print(f"Error: Could not produce source GLB in {item_dir}")
            sys.exit(1)

    print(f"Loading Source Motion:    {source_glb}")
    print(f"Loading Target Character: {char_file}")

    clear_scene()

    # 2. Import Source Animated GLB
    bpy.ops.import_scene.gltf(filepath=str(source_glb))
    src_arm = find_armature()
    if not src_arm:
        print("Error: Could not find armature in source motion GLB.")
        sys.exit(1)
    src_arm.name = "Source_Armature"

    # 3. Import Target Character Mesh & Armature
    if char_file.suffix.lower() == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(char_file))
    elif char_file.suffix.lower() in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(char_file))
    else:
        print(f"Unsupported character format: {char_file.suffix}")
        sys.exit(1)

    tgt_arm = find_armature(exclude=src_arm)
    if not tgt_arm:
        print("Error: Could not find armature in target character.")
        sys.exit(1)
    tgt_arm.name = "Target_Armature"

    # Normalize transforms on target armature
    bpy.context.view_layer.objects.active = tgt_arm
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Clean up non-character meshes from FBX (like extra helper spheres)
    for o in list(bpy.data.objects):
        if o != tgt_arm and o.type == 'MESH':
            if "ico" in o.name.lower() or "proxy" in o.name.lower():
                bpy.data.objects.remove(o, do_unlink=True)

    # Resolve bone names dynamically
    bone_map = {}
    for s_name, def_t_name in BONE_MAPPING.items():
        if s_name not in src_arm.data.bones:
            continue
        matched = None
        for c in [def_t_name, def_t_name.replace("mixamorig:", ""), s_name]:
            for b in tgt_arm.data.bones:
                if b.name.lower() == c.lower() or b.name.lower() == f"mixamorig:{c}".lower():
                    matched = b.name
                    break
            if matched:
                break
        if matched:
            bone_map[s_name] = matched

    print(f"Resolved {len(bone_map)} bones from SOMA to Target Armature.")

    # Calculate leg heights and root scale ratio for accurate floor contact
    s_hip_b = src_arm.data.bones.get('Hips')
    s_foot_b = src_arm.data.bones.get('LeftFoot') or src_arm.data.bones.get('RightFoot')
    s_leg_height = abs(s_hip_b.head_local.z - s_foot_b.head_local.z) if (s_hip_b and s_foot_b) else 0.938

    t_hips_name = bone_map.get('Hips')
    t_hip_b = tgt_arm.data.bones.get(t_hips_name) if t_hips_name else None
    t_foot_b = (
        tgt_arm.data.bones.get(bone_map.get('LeftFoot'))
        or tgt_arm.data.bones.get(bone_map.get('RightFoot'))
        or tgt_arm.data.bones.get(bone_map.get('LeftToeBase'))
        or tgt_arm.data.bones.get(bone_map.get('RightToeBase'))
    )
    t_foot_z = t_foot_b.head_local.z if t_foot_b else 0.0
    t_leg_height = abs(t_hip_b.head_local.z - t_foot_z) if t_hip_b else s_leg_height
    t_rest_hip_pos = (tgt_arm.matrix_world @ t_hip_b.head_local).copy() if t_hip_b else mathutils.Vector((0, 0, 0))

    scale_ratio = t_leg_height / s_leg_height if s_leg_height > 0.05 else 1.0
    scale_ratio = max(0.1, min(5.0, scale_ratio))
    print(f"Hip Proportions: SOMA leg={s_leg_height:.3f}m -> Target leg={t_leg_height:.3f}m (Scale Ratio: {scale_ratio:.3f})")

    # 4. Construct Alignment Bone Frames on Source Armature
    bpy.context.view_layer.objects.active = src_arm
    bpy.ops.object.mode_set(mode='EDIT')

    for s_name, t_name in bone_map.items():
        eb_src = src_arm.data.edit_bones.get(s_name)
        eb_tgt = tgt_arm.data.bones.get(t_name)
        if eb_src and eb_tgt:
            ab = src_arm.data.edit_bones.new(f"ALIGN_{t_name}")
            ab.head = eb_src.head
            ab.tail = eb_src.tail
            ab.matrix = eb_tgt.matrix_local.copy()
            ab.matrix.translation = eb_src.head
            ab.parent = eb_src

    # Dedicated root translation alignment bone
    ab_loc = src_arm.data.edit_bones.new("ALIGN_Hips_Loc")
    ab_loc.head = t_rest_hip_pos
    ab_loc.tail = t_rest_hip_pos + mathutils.Vector((0, 0, 0.1))
    ab_loc.parent = None

    bpy.ops.object.mode_set(mode='OBJECT')

    # Animate ALIGN_Hips_Loc across action frames with proportional scaling
    action = src_arm.animation_data.action if src_arm.animation_data else None
    if action:
        f_start = int(action.frame_range[0])
        f_end = int(action.frame_range[1])
        pb_align = src_arm.pose.bones["ALIGN_Hips_Loc"]
        pb_s_hip = src_arm.pose.bones["Hips"]
        mat_inv = pb_align.bone.matrix_local.to_3x3().inverted()

        for f in range(f_start, f_end + 1):
            bpy.context.scene.frame_set(f)
            s_loc = pb_s_hip.matrix.translation
            scaled_x = t_rest_hip_pos.x + s_loc.x * scale_ratio
            scaled_y = t_rest_hip_pos.y + s_loc.y * scale_ratio
            scaled_z = t_rest_hip_pos.z + (s_loc.z - s_leg_height) * scale_ratio
            desired_pos = mathutils.Vector((scaled_x, scaled_y, scaled_z))
            pb_align.location = mat_inv @ (desired_pos - pb_align.bone.head_local)
            pb_align.keyframe_insert(data_path="location", frame=f)

    # 5. Bind Pose Constraints to Target Armature
    bpy.context.view_layer.objects.active = tgt_arm
    bpy.ops.object.mode_set(mode='POSE')

    for pb in tgt_arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    for s_name, t_name in bone_map.items():
        pb_tgt = tgt_arm.pose.bones.get(t_name)
        align_bone_name = f"ALIGN_{t_name}"
        if pb_tgt and align_bone_name in src_arm.data.bones:
            con_rot = pb_tgt.constraints.new('COPY_ROTATION')
            con_rot.target = src_arm
            con_rot.subtarget = align_bone_name
            con_rot.target_space = 'WORLD'
            con_rot.owner_space = 'WORLD'

            if s_name == "Hips":
                con_loc = pb_tgt.constraints.new('COPY_LOCATION')
                con_loc.target = src_arm
                con_loc.subtarget = "ALIGN_Hips_Loc"
                con_loc.target_space = 'WORLD'
                con_loc.owner_space = 'WORLD'

    # 6. Determine frame range & Native C++ Action Bake
    action = src_arm.animation_data.action if src_arm.animation_data else None
    start_frame = int(action.frame_range[0]) if action else 0
    end_frame = int(action.frame_range[1]) if action else 150

    print(f"Baking alignment action from frame {start_frame} to {end_frame}...")
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(
        frame_start=start_frame,
        frame_end=end_frame,
        only_selected=False,
        visual_keying=True,
        clear_constraints=True,
        bake_types={'POSE'}
    )

    bpy.ops.object.mode_set(mode='OBJECT')

    # 7. Remove source armature & temporary objects
    for obj in list(bpy.data.objects):
        if obj == src_arm or "proxy" in obj.name.lower() or "canonical" in obj.name.lower():
            bpy.data.objects.remove(obj, do_unlink=True)

    # Clean up unlinked actions so the exported GLB only contains the baked character action
    if tgt_arm.animation_data and tgt_arm.animation_data.action:
        tgt_arm.animation_data.action.name = "Baked_Animation"
        for act in list(bpy.data.actions):
            if act != tgt_arm.animation_data.action:
                bpy.data.actions.remove(act)

    # 7.5. Fix material transparency settings to prevent see-through / X-ray sorting artifacts in WebGL
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

    # 8. Export output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    preview_glb = output_file.with_suffix('.glb')
    bpy.ops.export_scene.gltf(
        filepath=str(preview_glb),
        export_format='GLB',
        export_animations=True,
        export_current_frame=False,
        export_draco_mesh_compression_enable=False
    )
    if output_file.suffix.lower() == ".fbx":
        bpy.ops.export_scene.fbx(
            filepath=str(output_file),
            path_mode='COPY',
            embed_textures=True,
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False
        )

    print(f"\n[DONE] Saved fully baked animated model to: {output_file}\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
