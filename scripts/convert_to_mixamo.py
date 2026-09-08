import sys
import os
import argparse
import bpy
from mathutils import Matrix

def convert_rig(input_file, output_file, convention="Mixamo", prefix=""):
    print(f"Loading {input_file}...")
    bpy.ops.wm.read_factory_settings(use_empty=True)

    input_lower = input_file.lower()
    if input_lower.endswith(".glb") or input_lower.endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=input_file, import_pack_images=True)
    elif input_lower.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=input_file)
    else:
        raise ValueError(f"Unsupported input format: {input_file}")

    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    if not armatures:
        raise RuntimeError("No ARMATURE object found in the scene!")

    armature = armatures[0]
    print(f"Found armature: {armature.name} with {len(armature.data.bones)} bones")

    class BoneNode:
        def __init__(self, bpy_bone, parent=None):
            self.bpy_bone = bpy_bone
            self.name = bpy_bone.name
            self.parent = parent
            self.children = []
            parent_matrix = bpy_bone.parent.matrix_local if bpy_bone.parent else Matrix.Identity(4)
            local_matrix = parent_matrix.inverted() @ bpy_bone.matrix_local
            self.t = local_matrix.to_translation()
            self.head = bpy_bone.head

    def build_tree(bpy_bone, parent_node=None):
        node = BoneNode(bpy_bone, parent_node)
        for child in bpy_bone.children:
            child_node = build_tree(child, node)
            node.children.append(child_node)
        return node

    roots = [b for b in armature.data.bones if b.parent is None]
    if not roots:
        raise RuntimeError("Armature has no root bones!")

    root_nodes = [build_tree(r) for r in roots]
    all_nodes = []

    def get_all_nodes(node):
        all_nodes.append(node)
        for child in node.children:
            get_all_nodes(child)

    for r in root_nodes:
        get_all_nodes(r)

    def count_descendants(node):
        return sum(1 + count_descendants(c) for c in node.children)

    pelvis = None
    for node in all_nodes:
        if len(node.children) >= 3:
            pelvis = node
            break
    if not pelvis:
        pelvis = all_nodes[0]

    rename_map = {}

    def format_name(name):
        return f"{prefix}{name}" if prefix else name

    if convention == "UE5":
        rename_map[pelvis.name] = "pelvis"
    else:
        rename_map[pelvis.name] = format_name("Hips")

    pelvis_children = pelvis.children
    if pelvis_children:
        pelvis_children_sorted_by_size = sorted(pelvis_children, key=count_descendants, reverse=True)
        spine_root = pelvis_children_sorted_by_size[0]
        remaining_legs = pelvis_children_sorted_by_size[1:]

        legs_sorted_x = sorted(remaining_legs, key=lambda c: c.head.x, reverse=True)
        thigh_l = legs_sorted_x[0] if len(legs_sorted_x) > 0 else None
        thigh_r = legs_sorted_x[1] if len(legs_sorted_x) > 1 else None

        current_spine = spine_root
        spine_idx = 1
        chest_split = None
        while current_spine:
            if convention == "UE5":
                rename_map[current_spine.name] = f"spine_{spine_idx:02d}"
            else:
                rename_map[current_spine.name] = format_name("Spine" if spine_idx == 1 else f"Spine{spine_idx - 1}")

            if len(current_spine.children) >= 3:
                chest_split = current_spine
                break
            elif len(current_spine.children) == 1:
                current_spine = current_spine.children[0]
                spine_idx += 1
            else:
                break

        if chest_split:
            chest_children = chest_split.children
            chest_children_sorted_by_size = sorted(chest_children, key=count_descendants)
            neck_root = chest_children_sorted_by_size[0]
            remaining_arms = chest_children_sorted_by_size[1:]
            arms_sorted_x = sorted(remaining_arms, key=lambda c: c.head.x, reverse=True)
            clavicle_l = arms_sorted_x[0] if len(arms_sorted_x) > 0 else None
            clavicle_r = arms_sorted_x[1] if len(arms_sorted_x) > 1 else None

            current_neck = neck_root
            neck_idx = 1
            while current_neck:
                if len(current_neck.children) == 0:
                    rename_map[current_neck.name] = "head" if convention == "UE5" else format_name("Head")
                    break
                else:
                    if convention == "UE5":
                        rename_map[current_neck.name] = f"neck_{neck_idx:02d}"
                    else:
                        rename_map[current_neck.name] = format_name("Neck" if neck_idx == 1 else f"Neck{neck_idx - 1}")
                    current_neck = current_neck.children[0]
                    neck_idx += 1

            def rename_arm_chain(start_node, suffix):
                side_prefix = "Left" if suffix == "l" else "Right"
                if convention == "UE5":
                    rename_map[start_node.name] = f"clavicle_{suffix}"
                else:
                    rename_map[start_node.name] = format_name(f"{side_prefix}Shoulder")

                curr = start_node.children[0] if start_node.children else None
                if curr:
                    if convention == "UE5":
                        rename_map[curr.name] = f"upperarm_{suffix}"
                    else:
                        rename_map[curr.name] = format_name(f"{side_prefix}Arm")
                    curr = curr.children[0] if curr.children else None
                if curr:
                    if convention == "UE5":
                        rename_map[curr.name] = f"lowerarm_{suffix}"
                    else:
                        rename_map[curr.name] = format_name(f"{side_prefix}ForeArm")
                    curr = curr.children[0] if curr.children else None
                if curr:
                    if convention == "UE5":
                        rename_map[curr.name] = f"hand_{suffix}"
                    else:
                        rename_map[curr.name] = format_name(f"{side_prefix}Hand")
                    fingers = curr.children
                    if len(fingers) > 0:
                        thumb_node = min(fingers, key=lambda f: f.head.y)
                        other_fingers = [f for f in fingers if f != thumb_node]
                        if suffix == "l":
                            other_fingers_sorted = sorted(other_fingers, key=lambda f: f.head.x, reverse=True)
                        else:
                            other_fingers_sorted = sorted(other_fingers, key=lambda f: f.head.x, reverse=False)
                        fingers_sorted = [thumb_node] + other_fingers_sorted
                    else:
                        fingers_sorted = []

                    finger_names_ue5 = ["thumb", "index", "middle", "ring", "pinky"]
                    finger_names_mixamo = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
                    if len(fingers_sorted) == 3:
                        finger_names_ue5 = ["thumb", "index", "pinky"]
                        finger_names_mixamo = ["Thumb", "Index", "Pinky"]

                    for f_idx, finger in enumerate(fingers_sorted):
                        curr_finger = finger
                        joint_idx = 1
                        while curr_finger:
                            if convention == "UE5":
                                name_pfx = finger_names_ue5[f_idx] if f_idx < len(finger_names_ue5) else f"finger_{f_idx}"
                                rename_map[curr_finger.name] = f"{name_pfx}_{joint_idx:02d}_{suffix}"
                            else:
                                name_pfx = finger_names_mixamo[f_idx] if f_idx < len(finger_names_mixamo) else f"Finger{f_idx}"
                                rename_map[curr_finger.name] = format_name(f"{side_prefix}Hand{name_pfx}{joint_idx}")
                            curr_finger = curr_finger.children[0] if curr_finger.children else None
                            joint_idx += 1

            if clavicle_l:
                rename_arm_chain(clavicle_l, "l")
            if clavicle_r:
                rename_arm_chain(clavicle_r, "r")

        def rename_leg_chain(start_node, suffix):
            side_prefix = "Left" if suffix == "l" else "Right"
            if convention == "UE5":
                rename_map[start_node.name] = f"thigh_{suffix}"
            else:
                rename_map[start_node.name] = format_name(f"{side_prefix}UpLeg")

            curr = start_node.children[0] if start_node.children else None
            if curr:
                if convention == "UE5":
                    rename_map[curr.name] = f"calf_{suffix}"
                else:
                    rename_map[curr.name] = format_name(f"{side_prefix}Leg")
                curr = curr.children[0] if curr.children else None
            if curr:
                if convention == "UE5":
                    rename_map[curr.name] = f"foot_{suffix}"
                else:
                    rename_map[curr.name] = format_name(f"{side_prefix}Foot")
                curr = curr.children[0] if curr.children else None
            if curr:
                if convention == "UE5":
                    rename_map[curr.name] = f"ball_{suffix}"
                else:
                    rename_map[curr.name] = format_name(f"{side_prefix}ToeBase")

        if thigh_l:
            rename_leg_chain(thigh_l, "l")
        if thigh_r:
            rename_leg_chain(thigh_r, "r")

    print(f"Renaming {len(rename_map)} bones to {convention} naming...")
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    for orig, new in rename_map.items():
        if orig in armature.data.edit_bones:
            armature.data.edit_bones[orig].name = new

    if convention == "UE5" and "pelvis" in armature.data.edit_bones:
        root_bone = armature.data.edit_bones.new("root")
        root_bone.head = (0.0, 0.0, 0.0)
        root_bone.tail = (0.0, 0.0, 0.1)
        armature.data.edit_bones["pelvis"].parent = root_bone

    bpy.ops.object.mode_set(mode='OBJECT')

    # Rename corresponding vertex groups in meshes so weights match perfectly!
    renamed_groups = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for orig, new in rename_map.items():
                if orig in obj.vertex_groups:
                    obj.vertex_groups[orig].name = new
                    renamed_groups += 1

    print(f"Updated {renamed_groups} vertex group references on meshes.")

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    output_lower = output_file.lower()
    if output_lower.endswith(".glb") or output_lower.endswith(".gltf"):
        print(f"Exporting GLB to {output_file}...")
        bpy.ops.export_scene.gltf(filepath=output_file, export_format='GLB')
    elif output_lower.endswith(".fbx"):
        print(f"Exporting FBX to {output_file}...")
        bpy.ops.export_scene.fbx(
            filepath=output_file,
            use_selection=False,
            add_leaf_bones=False,
            path_mode='COPY',
            embed_textures=True,
            mesh_smooth_type="FACE"
        )
    else:
        raise ValueError(f"Unsupported output format: {output_file}")
    print("Mixamo conversion completed successfully!")

def main():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    if len(args) < 2:
        print("Usage: blender -b -P convert_to_mixamo.py -- <input_file> <output_file> [convention=Mixamo] [prefix=mixamorig:]")
        sys.exit(1)

    input_file = args[0]
    output_file = args[1]
    convention = args[2] if len(args) > 2 else "Mixamo"
    prefix = args[3] if len(args) > 3 else "mixamorig:"

    convert_rig(input_file, output_file, convention=convention, prefix=prefix)

if __name__ == "__main__":
    main()
