import bpy
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

char_path = r"E:\Kimodo-CPP\Remy.fbx"
motion_path = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\animation.glb"
output_glb = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_true_align_test.glb"
output_fbx = r"E:\Kimodo-CPP\demo-output\5e15f54638196203\Remy_true_align_test.fbx"

# 1. Import Character
bpy.ops.import_scene.fbx(filepath=char_path)
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
char_arm.name = "Character_Armature"

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 2. Import Motion GLB
pre_objects = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=motion_path)
motion_objs = {o.name: o for o in bpy.data.objects if o not in pre_objects}

# Find frame range
start_frame = 0
end_frame = 60
for o in motion_objs.values():
    if o.animation_data and o.animation_data.action:
        start_frame = int(o.animation_data.action.frame_range[0])
        end_frame = int(o.animation_data.action.frame_range[1])
        break

BONE_MAPPING = {
    "mixamorig:Hips": "Hips",
    "mixamorig:Spine": "Spine1",
    "mixamorig:Spine1": "Spine2",
    "mixamorig:Spine2": "Chest",
    "mixamorig:Neck": "Neck1",
    "mixamorig:Head": "Head",
    "mixamorig:LeftShoulder": "LeftShoulder",
    "mixamorig:LeftArm": "LeftArm",
    "mixamorig:LeftForeArm": "LeftForeArm",
    "mixamorig:LeftHand": "LeftHand",
    "mixamorig:RightShoulder": "RightShoulder",
    "mixamorig:RightArm": "RightArm",
    "mixamorig:RightForeArm": "RightForeArm",
    "mixamorig:RightHand": "RightHand",
    "mixamorig:LeftUpLeg": "LeftLeg",
    "mixamorig:LeftLeg": "LeftShin",
    "mixamorig:LeftFoot": "LeftFoot",
    "mixamorig:LeftToeBase": "LeftToeBase",
    "mixamorig:RightUpLeg": "RightLeg",
    "mixamorig:RightLeg": "RightShin",
    "mixamorig:RightFoot": "RightFoot",
    "mixamorig:RightToeBase": "RightToeBase",
}

bpy.context.view_layer.objects.active = char_arm
bpy.ops.object.mode_set(mode='POSE')

# Go to frame 0 and record rest positions
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()

hips_pb = char_arm.pose.bones.get("mixamorig:Hips")
hips_rest_loc = hips_pb.location.copy() if hips_pb else (0, 0, 0)
motion_hips_rest = motion_objs["Hips"].matrix_world.to_translation().copy()

for pb in char_arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

# Frame by Frame Transfer
for f in range(start_frame, end_frame + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()

    # 1. Hips translation (direct 3D world delta)
    if hips_pb:
        curr_m_trans = motion_objs["Hips"].matrix_world.to_translation()
        delta_trans = curr_m_trans - motion_hips_rest
        hips_pb.location = hips_rest_loc + delta_trans
        hips_pb.keyframe_insert(data_path="location", frame=f)

    # 2. Bone Rotations (Local space delta relative to parent empty)
    for mix_name, soma_name in BONE_MAPPING.items():
        pb = None
        for b in char_arm.pose.bones:
            if b.name.lower() == mix_name.lower() or b.name.lower() == mix_name.replace("mixamorig:", "").lower():
                pb = b
                break

        if pb and soma_name in motion_objs:
            src_obj = motion_objs[soma_name]
            
            # Local rotation of empty at current frame
            # (In glTF empties, matrix_local is the animated local transform)
            q_local = src_obj.matrix_local.to_quaternion()
            
            pb.rotation_quaternion = q_local
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

bpy.ops.object.mode_set(mode='OBJECT')

# Remove motion objects
for o in motion_objs.values():
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o, do_unlink=True)

# Export
bpy.ops.export_scene.gltf(
    filepath=output_glb,
    export_format='GLB',
    export_animations=True,
    export_current_frame=False
)
bpy.ops.export_scene.fbx(
    filepath=output_fbx,
    bake_anim=True,
    bake_anim_use_all_bones=True
)

print(f"[SUCCESS] Exported:")
print(f"  GLB: {output_glb}")
print(f"  FBX: {output_fbx}")
