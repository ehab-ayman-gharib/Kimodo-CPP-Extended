import sys
from pathlib import Path
import bpy
import mathutils

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

BIPED_TO_MIXAMO = {
    'Bip001 Pelvis': 'mixamorig:Hips',
    'Bip001 Spine': 'mixamorig:Spine',
    'Bip001 Spine1': 'mixamorig:Spine1',
    'Bip001 Spine2': 'mixamorig:Spine2',
    'Bip001 Neck': 'mixamorig:Neck',
    'Bip001 Head': 'mixamorig:Head',
    'Bip001 L Clavicle': 'mixamorig:LeftShoulder',
    'Bip001 L UpperArm': 'mixamorig:LeftArm',
    'Bip001 L Forearm': 'mixamorig:LeftForeArm',
    'Bip001 L Hand': 'mixamorig:LeftHand',
    'Bip001 R Clavicle': 'mixamorig:RightShoulder',
    'Bip001 R UpperArm': 'mixamorig:RightArm',
    'Bip001 R Forearm': 'mixamorig:RightForeArm',
    'Bip001 R Hand': 'mixamorig:RightHand',
    'Bip001 L Thigh': 'mixamorig:LeftUpLeg',
    'Bip001 L Calf': 'mixamorig:LeftLeg',
    'Bip001 L Foot': 'mixamorig:LeftFoot',
    'Bip001 L Toe0': 'mixamorig:LeftToeBase',
    'Bip001 R Thigh': 'mixamorig:RightUpLeg',
    'Bip001 R Calf': 'mixamorig:RightLeg',
    'Bip001 R Foot': 'mixamorig:RightFoot',
    'Bip001 R Toe0': 'mixamorig:RightToeBase',
    # Fingers
    'Bip001 L Finger0': 'mixamorig:LeftHandThumb1', 'Bip001 L Finger01': 'mixamorig:LeftHandThumb2', 'Bip001 L Finger02': 'mixamorig:LeftHandThumb3',
    'Bip001 L Finger1': 'mixamorig:LeftHandIndex1', 'Bip001 L Finger11': 'mixamorig:LeftHandIndex2', 'Bip001 L Finger12': 'mixamorig:LeftHandIndex3',
    'Bip001 L Finger2': 'mixamorig:LeftHandMiddle1', 'Bip001 L Finger21': 'mixamorig:LeftHandMiddle2', 'Bip001 L Finger22': 'mixamorig:LeftHandMiddle3',
    'Bip001 L Finger3': 'mixamorig:LeftHandRing1', 'Bip001 L Finger31': 'mixamorig:LeftHandRing2', 'Bip001 L Finger32': 'mixamorig:LeftHandRing3',
    'Bip001 L Finger4': 'mixamorig:LeftHandPinky1', 'Bip001 L Finger41': 'mixamorig:LeftHandPinky2', 'Bip001 L Finger42': 'mixamorig:LeftHandPinky3',
    'Bip001 R Finger0': 'mixamorig:RightHandThumb1', 'Bip001 R Finger01': 'mixamorig:RightHandThumb2', 'Bip001 R Finger02': 'mixamorig:RightHandThumb3',
    'Bip001 R Finger1': 'mixamorig:RightHandIndex1', 'Bip001 R Finger11': 'mixamorig:RightHandIndex2', 'Bip001 R Finger12': 'mixamorig:RightHandIndex3',
    'Bip001 R Finger2': 'mixamorig:RightHandMiddle1', 'Bip001 R Finger21': 'mixamorig:RightHandMiddle2', 'Bip001 R Finger22': 'mixamorig:RightHandMiddle3',
    'Bip001 R Finger3': 'mixamorig:RightHandRing1', 'Bip001 R Finger31': 'mixamorig:RightHandRing2', 'Bip001 R Finger32': 'mixamorig:RightHandRing3',
    'Bip001 R Finger4': 'mixamorig:RightHandPinky1', 'Bip001 R Finger41': 'mixamorig:RightHandPinky2', 'Bip001 R Finger42': 'mixamorig:RightHandPinky3',
}

def get_biped_mixamo_name(b_name: str) -> str:
    if b_name in BIPED_TO_MIXAMO:
        return BIPED_TO_MIXAMO[b_name]
    # Handle custom biped prefixes like "BipTrump Pelvis", "BipHero Spine", "Bip01 L Arm"
    parts = b_name.split(' ', 1)
    if len(parts) == 2 and parts[0].lower().startswith('bip'):
        generic_bip = f"Bip001 {parts[1]}"
        if generic_bip in BIPED_TO_MIXAMO:
            return BIPED_TO_MIXAMO[generic_bip]
    return b_name

def convert_biped(input_path: Path, output_path: Path):
    clear_scene()
    print(f"[Biped Converter] Loading: {input_path}")
    bpy.ops.import_scene.fbx(filepath=str(input_path))

    arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if not arm_objs:
        print("[Biped Converter] No armature found!")
        return False
    old_arm = arm_objs[0]

    # Clean legacy actions
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a, do_unlink=True)
    for o in bpy.data.objects:
        if o.animation_data:
            o.animation_data_clear()

    old_arm.data.pose_position = 'REST'
    bpy.context.view_layer.update()

    # Determine unit scale (3ds Max centimeter scale is 0.01)
    unit_scale = 0.01

    # Collect bone locations & hierarchy in normalized meter coordinates
    bone_heads = {}
    bone_tails = {}
    bone_parents = {}
    children_map = {}

    for b in old_arm.data.bones:
        m_name = get_biped_mixamo_name(b.name)
        # World position scaled to true meters
        h_w = old_arm.matrix_world @ b.head_local
        bone_heads[m_name] = h_w
        if b.parent:
            p_name = get_biped_mixamo_name(b.parent.name)
            bone_parents[m_name] = p_name
            children_map.setdefault(p_name, []).append(m_name)

    for m_name, h_pos in bone_heads.items():
        ch_list = children_map.get(m_name, [])
        if ch_list:
            # Find closest primary child (e.g. ForeArm for Arm, Hand for ForeArm)
            primary_ch = ch_list[0]
            for ch in ch_list:
                if any(k in ch for k in ['ForeArm', 'Hand', 'Leg', 'Foot', 'ToeBase', 'Head', 'Neck', 'Spine']):
                    primary_ch = ch
                    break
            t_pos = bone_heads[primary_ch]
            if (t_pos - h_pos).length > 0.005:
                bone_tails[m_name] = t_pos
            else:
                bone_tails[m_name] = h_pos + mathutils.Vector((0, 0, 0.10))
        else:
            bone_tails[m_name] = h_pos + mathutils.Vector((0, 0, 0.10))

    # Extract native bone rolls from original Biped armature
    bone_rolls = {}
    for b in old_arm.data.bones:
        m_name = BIPED_TO_MIXAMO.get(b.name, b.name)
        bone_rolls[m_name] = b.matrix_local.to_3x3()

    # Create new Standard Mixamo Armature in true meters
    new_arm_data = bpy.data.armatures.new("Standard_Mixamo_Armature")
    new_arm = bpy.data.objects.new("mixamorig", new_arm_data)
    bpy.context.collection.objects.link(new_arm)
    new_arm.matrix_world = mathutils.Matrix.Identity(4)

    bpy.context.view_layer.objects.active = new_arm
    bpy.ops.object.mode_set(mode='EDIT')

    for m_name, h_pos in bone_heads.items():
        eb = new_arm_data.edit_bones.new(m_name)
        eb.head = h_pos
        eb.tail = bone_tails[m_name]

    for m_name, p_name in bone_parents.items():
        eb = new_arm_data.edit_bones.get(m_name)
        p_eb = new_arm_data.edit_bones.get(p_name)
        if eb and p_eb:
            eb.parent = p_eb

    # Universal 3ds Max Biped to Mixamo basis transformation matrix
    # Maps Biped's (+X longitudinal, +Z up) to Mixamo's (+Y longitudinal, +Z forward)
    R_biped_to_mixamo = mathutils.Matrix([
        [ 0.0, -1.0,  0.0],
        [ 1.0,  0.0,  0.0],
        [ 0.0,  0.0,  1.0]
    ])

    for eb in new_arm_data.edit_bones:
        if eb.name in bone_rolls:
            # Transform native Biped local orientation matrix into standard Mixamo orientation
            m_mixamo_rot = bone_rolls[eb.name] @ R_biped_to_mixamo
            # The roll is aligned to the transformed upward normal
            up_vec = m_mixamo_rot @ mathutils.Vector((0, 0, 1))
            eb.align_roll(up_vec)
        else:
            eb.align_roll(mathutils.Vector((0, 1, 0)))

    bpy.ops.object.mode_set(mode='OBJECT')

    # Convert meshes into pure unscaled meter geometry
    char_meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    new_mesh_objs = []

    for m in char_meshes:
        new_m_data = m.data.copy()
        # Scale centimeters to meters
        for v in new_m_data.vertices:
            v.co = v.co * unit_scale

        new_m = bpy.data.objects.new(m.name, new_m_data)
        bpy.context.collection.objects.link(new_m)
        new_m.matrix_world = mathutils.Matrix.Identity(4)

        for mat in m.data.materials:
            new_m.data.materials.append(mat)

        # Map vertex groups
        for vg in m.vertex_groups:
            m_vg_name = get_biped_mixamo_name(vg.name)
            new_vg = new_m.vertex_groups.new(name=m_vg_name)
            for v_idx in range(len(m.data.vertices)):
                try:
                    new_vg.add([v_idx], vg.weight(v_idx), 'REPLACE')
                except RuntimeError:
                    pass

        mod = new_m.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = new_arm
        mod.use_vertex_groups = True
        new_m.parent = new_arm
        new_mesh_objs.append(new_m)

    # Remove all old objects
    for o in list(bpy.data.objects):
        if o not in new_mesh_objs and o != new_arm:
            bpy.data.objects.remove(o, do_unlink=True)

    # Fix materials to opaque
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == '.fbx':
        bpy.ops.export_scene.fbx(filepath=str(output_path), path_mode='COPY', embed_textures=True)
    else:
        bpy.ops.export_scene.gltf(filepath=str(output_path), export_format='GLB', export_animations=False)

    print(f"[Biped Converter] Successfully converted to standard Mixamo format: {output_path}")
    return True

if __name__ == '__main__':
    args = sys.argv
    if '--' in args:
        args = args[args.index('--') + 1:]
    if len(args) >= 2:
        in_p = Path(args[0]).resolve()
        out_p = Path(args[1]).resolve()
        convert_biped(in_p, out_p)
    else:
        print("Usage: blender -b -P convert_biped_to_standard.py -- <input_biped.fbx> <output.glb/fbx>")
