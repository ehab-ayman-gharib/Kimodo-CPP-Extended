"""Import a kimodo .glb into Unreal and put the motion on a real character.

Run this inside the editor. Open the Output Log, switch the input box at the
bottom from Cmd to Python, and paste:

    py "C:/path/to/unreal_retarget.py" "C:/path/to/walk_150.glb"

You end up with an Anim Sequence on the mannequin at

    /Game/Kimodo/Retargeted/A_<name>

Pass several .glb paths to do them in one go. Pass none and it converts every
.glb sitting next to this script.

To target a different character, add its Skeletal Mesh path last:

    py ".../unreal_retarget.py" ".../walk_150.glb" /Game/MyChars/SK_Hero

The box rig that comes out of the import is scaffolding. It is what the
retargeter reads the motion from. Once the bake is done you can ignore it, or
delete the /Game/Kimodo/Source folder.
"""
import math
import os
import sys

import unreal


ROOT = "/Game/Kimodo"
SRC_DIR = ROOT + "/Source"
RIG_DIR = ROOT + "/Rigs"
OUT_DIR = ROOT + "/Retargeted"

SRC_T = unreal.RetargetSourceOrTarget.SOURCE
TGT_T = unreal.RetargetSourceOrTarget.TARGET
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

# Characters to look for, best first. Anything with a UE mannequin skeleton
# works; these are just the ones that ship with the engine templates.
TARGET_GUESSES = [
    "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple",
    "/Game/Characters/Mannequins/Meshes/SKM_Manny",
    "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple",
    "/Game/Characters/Mannequins/Meshes/SKM_Quinn",
    "/Game/Mannequin/Character/Mesh/SK_Mannequin",
]

# One entry per kimodo skeleton, keyed by the root bone the import produces.
#
#   chains  what the retargeter treats as a limb: name, first bone, last bone
#   arms    target segment then source segment, for cancelling the rest-pose
#           difference. Parent first: the forearm correction is measured after
#           the upper arm has already moved.
#   feet    bones used to work out how tall the rest pose stands
#
# SMPL-X arrives with mannequin bone names because kimodo_to_glb.py renames it,
# so its chains read like the target's. SOMA uses Mixamo-style names. G1 is a
# robot: three single-axis joints per hip, a four-joint wrist, and no clavicle,
# neck or head at all, so four mannequin chains get no source and keep their
# rest pose.
SKELETONS = {
    "pelvis": {
        "label": "SMPL-X, 22 joints",
        "chains": [("Spine", "spine_01", "spine_03"), ("Neck", "neck_01", "neck_01"),
                   ("Head", "head", "head"),
                   ("LeftClavicle", "clavicle_l", "clavicle_l"),
                   ("LeftArm", "upperarm_l", "hand_l"),
                   ("LeftLeg", "thigh_l", "ball_l"),
                   ("RightClavicle", "clavicle_r", "clavicle_r"),
                   ("RightArm", "upperarm_r", "hand_r"),
                   ("RightLeg", "thigh_r", "ball_r")],
        "arms": [("upperarm_l", "lowerarm_l", "upperarm_l", "lowerarm_l"),
                 ("lowerarm_l", "hand_l", "lowerarm_l", "hand_l"),
                 ("upperarm_r", "lowerarm_r", "upperarm_r", "lowerarm_r"),
                 ("lowerarm_r", "hand_r", "lowerarm_r", "hand_r")],
        "feet": ["foot_l", "foot_r", "ball_l", "ball_r"],
    },
    "Hips": {
        "label": "SOMA, 30 joints",
        "chains": [("Spine", "Spine1", "Chest"), ("Neck", "Neck1", "Neck2"),
                   ("Head", "Head", "Head"),
                   ("LeftClavicle", "LeftShoulder", "LeftShoulder"),
                   ("LeftArm", "LeftArm", "LeftHand"),
                   ("LeftLeg", "LeftLeg", "LeftToeBase"),
                   ("RightClavicle", "RightShoulder", "RightShoulder"),
                   ("RightArm", "RightArm", "RightHand"),
                   ("RightLeg", "RightLeg", "RightToeBase")],
        "arms": [("upperarm_l", "lowerarm_l", "LeftArm", "LeftForeArm"),
                 ("lowerarm_l", "hand_l", "LeftForeArm", "LeftHand"),
                 ("upperarm_r", "lowerarm_r", "RightArm", "RightForeArm"),
                 ("lowerarm_r", "hand_r", "RightForeArm", "RightHand")],
        "feet": ["LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"],
    },
    "pelvis_skel": {
        "label": "Unitree G1, 34 joints",
        "chains": [("Spine", "waist_yaw_skel", "waist_pitch_skel"),
                   ("LeftArm", "left_shoulder_pitch_skel", "left_hand_roll_skel"),
                   ("LeftLeg", "left_hip_pitch_skel", "left_toe_base"),
                   ("RightArm", "right_shoulder_pitch_skel", "right_hand_roll_skel"),
                   ("RightLeg", "right_hip_pitch_skel", "right_toe_base")],
        "arms": [("upperarm_l", "lowerarm_l", "left_shoulder_pitch_skel", "left_elbow_skel"),
                 ("lowerarm_l", "hand_l", "left_elbow_skel", "left_hand_roll_skel"),
                 ("upperarm_r", "lowerarm_r", "right_shoulder_pitch_skel", "right_elbow_skel"),
                 ("lowerarm_r", "hand_r", "right_elbow_skel", "right_hand_roll_skel")],
        "feet": ["left_ankle_roll_skel", "right_ankle_roll_skel",
                 "left_toe_base", "right_toe_base"],
    },
}


def log(msg):
    unreal.log("kimodo: " + msg)
    print(msg)


# ------------------------------------------------------------- quaternions
# unreal.Quat's operators vary between engine versions, so this is by hand.

def conj(q):
    return unreal.Quat(-q.x, -q.y, -q.z, q.w)


def qmul(a, b):
    return unreal.Quat(
        a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
        a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
        a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)


def norm(v):
    l = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) or 1.0
    return unreal.Vector(v.x / l, v.y / l, v.z / l)


def shortest_arc(a, b):
    d = a.x * b.x + a.y * b.y + a.z * b.z
    q = unreal.Quat(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z,
                    a.x * b.y - a.y * b.x, 1.0 + d)
    m = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w) or 1.0
    return unreal.Quat(q.x / m, q.y / m, q.z / m, q.w / m)


def rotv(q, v):
    cx = q.y * v.z - q.z * v.y
    cy = q.z * v.x - q.x * v.z
    cz = q.x * v.y - q.y * v.x
    dx = q.y * cz - q.z * cy
    dy = q.z * cx - q.x * cz
    dz = q.x * cy - q.y * cx
    return unreal.Vector(v.x + 2 * (q.w * cx + dx),
                         v.y + 2 * (q.w * cy + dy),
                         v.z + 2 * (q.w * cz + dz))


# ------------------------------------------------------------------ assets

def bone_names(seq):
    opts = unreal.AnimPoseEvaluationOptions()
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, 0.0, opts)
    return [str(b) for b in unreal.AnimPoseExtensions.get_bone_names(pose)]


def import_glb(glb):
    """Import and return (mesh, sequence, asset path). The glTF importer nests
    the result under <dest>/<file>/SkeletalMeshes/, so the path is found by
    looking rather than by guessing."""
    name = os.path.splitext(os.path.basename(glb))[0]
    dest = "%s/%s" % (SRC_DIR, name)
    if unreal.EditorAssetLibrary.does_directory_exist(dest):
        unreal.EditorAssetLibrary.delete_directory(dest)
    task = unreal.AssetImportTask()
    task.filename = glb
    task.destination_path = dest
    task.automated = True
    task.save = True
    task.replace_existing = True
    TOOLS.import_asset_tasks([task])

    mesh = seq = path = None
    for p in unreal.EditorAssetLibrary.list_assets(dest, True, False):
        obj = unreal.load_asset(p)
        if isinstance(obj, unreal.SkeletalMesh):
            mesh, path = obj, p.split(".")[0]
        elif isinstance(obj, unreal.AnimSequence):
            seq = obj
    if not mesh or not seq:
        raise RuntimeError("import of %s produced no skeletal mesh and animation" % glb)
    return mesh, seq, path


def find_target(explicit):
    if explicit:
        mesh = unreal.load_asset(explicit)
        if not mesh:
            raise RuntimeError("target mesh not found: %s" % explicit)
        return mesh, explicit
    for p in TARGET_GUESSES:
        mesh = unreal.load_asset(p)
        if mesh:
            return mesh, p
    # nothing standard: take any skeletal mesh whose skeleton is a mannequin
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for data in reg.get_assets_by_class("SkeletalMesh", True):
        p = str(data.package_name)
        if p.startswith(ROOT):
            continue
        mesh = unreal.load_asset(p)
        if not mesh:
            continue
        names = [str(b) for b in mesh.skeleton.get_reference_pose().get_bone_names()] \
            if hasattr(mesh.skeleton, "get_reference_pose") else []
        if "upperarm_l" in names and "thigh_l" in names:
            return mesh, p
    raise RuntimeError(
        "no mannequin-style character found. Add the Third Person template "
        "content, or pass a Skeletal Mesh path as the last argument.")


def make_rig(asset_name, mesh, root_bone=None, chains=None):
    path = "%s/%s" % (RIG_DIR, asset_name)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    rig = TOOLS.create_asset(asset_name, RIG_DIR, unreal.IKRigDefinition,
                             unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    if chains is None:
        # the target is a mannequin, so the engine can work its own chains out
        c.apply_auto_generated_retarget_definition()
    else:
        if not c.set_retarget_root(root_bone):
            raise RuntimeError("could not set %s as the retarget root" % root_bone)
        for name, start, end in chains:
            c.add_retarget_chain(name, start, end, "None")
        got = sorted(str(x.chain_name) for x in c.get_retarget_chains())
        want = sorted(n for n, _, _ in chains)
        if got != want:
            raise RuntimeError("chains did not stick: got %s, wanted %s" % (got, want))
    unreal.EditorAssetLibrary.save_asset(path)
    return rig


def chain_names(rig):
    return [str(x.chain_name) for x in
            unreal.IKRigController.get_controller(rig).get_retarget_chains()]


def build_retargeter(path, rig_src, rig_tgt, src_mesh, tgt_mesh):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    folder, leaf = path.rsplit("/", 1)
    ret = TOOLS.create_asset(leaf, folder, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(ret)
    # set_ik_rig has to come first. set_rotation_offset_for_retarget_pose_bone
    # dereferences GetAsset()->GetIKRig() with no null check and takes the whole
    # editor down; assign_ik_rig_to_all_ops does not fill that pointer in.
    rc.set_ik_rig(SRC_T, rig_src)
    rc.set_ik_rig(TGT_T, rig_tgt)
    rc.set_preview_mesh(SRC_T, src_mesh)
    rc.set_preview_mesh(TGT_T, tgt_mesh)
    rc.assign_ik_rig_to_all_ops(SRC_T, rig_src)
    rc.assign_ik_rig_to_all_ops(TGT_T, rig_tgt)
    for i in range(rc.get_num_retarget_ops()):
        try:
            rc.run_op_initial_setup(i)
        except Exception:
            pass

    have = set(chain_names(rig_src))
    mapped, blank = [], []
    for t in chain_names(rig_tgt):
        if t in have:
            rc.set_source_chain(t, t)
            mapped.append(t)
        else:
            rc.set_source_chain("None", t)
            blank.append(t)
    return ret, rc, mapped, blank


def fix_poses(rc, src_mesh, tgt_mesh, spec):
    """Stand the source on the floor, then cancel the rest-pose arm difference.

    kimodo puts the hips at the origin with the legs hanging below, so untouched
    the source rig is half underground and the retargeter has no vertical range
    left. The height comes from the rest pose, never the first animation frame:
    a clip that starts crouched would otherwise bake out standing upright.
    """
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a1 = sub.spawn_actor_from_class(unreal.SkeletalMeshActor,
                                    unreal.Vector(0, 500, 0), unreal.Rotator(0, 0, 0))
    a1.skeletal_mesh_component.set_skeletal_mesh_asset(src_mesh)
    a2 = sub.spawn_actor_from_class(unreal.SkeletalMeshActor,
                                    unreal.Vector(0, 800, 0), unreal.Rotator(0, 0, 0))
    a2.skeletal_mesh_component.set_skeletal_mesh_asset(tgt_mesh)
    sc, tc = a1.skeletal_mesh_component, a2.skeletal_mesh_component
    notes = []
    try:
        root = spec["root"]
        reach = sc.get_socket_location(root).z - min(
            sc.get_socket_location(b).z for b in spec["feet"])
        t_reach = tc.get_socket_location("pelvis").z - min(
            tc.get_socket_location(b).z for b in ("foot_l", "foot_r", "ball_l", "ball_r"))
        notes.append("reach %.0f cm to %.0f cm" % (reach, t_reach))

        try:
            rc.create_retarget_pose("KimodoStanding", SRC_T)
        except Exception:
            pass
        rc.set_current_retarget_pose("KimodoStanding", SRC_T)
        rc.set_root_offset_in_retarget_pose(unreal.Vector(0, 0, reach), SRC_T)

        try:
            rc.create_retarget_pose("KimodoAligned", TGT_T)
        except Exception:
            pass
        rc.set_current_retarget_pose("KimodoAligned", TGT_T)

        def gq(c, b):
            return c.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_WORLD).rotation

        def d(c, x, y):
            px, py = c.get_socket_location(x), c.get_socket_location(y)
            return norm(unreal.Vector(py.x - px.x, py.y - px.y, py.z - px.z))

        worst = 0.0
        carry = {}
        for t_from, t_to, s_from, s_to in spec["arms"]:
            want, have = d(sc, s_from, s_to), d(tc, t_from, t_to)
            parent = carry.get(t_from)
            if parent is not None:
                have = norm(rotv(parent, have))
            q = shortest_arc(have, want)
            g = gq(tc, t_from)
            if parent is not None:
                g = qmul(parent, g)
            rc.set_rotation_offset_for_retarget_pose_bone(
                t_from, qmul(qmul(conj(g), q), g), TGT_T)
            carry[t_to] = qmul(q, parent) if parent is not None else q
            worst = max(worst, math.degrees(2 * math.acos(min(1.0, abs(q.w)))))
        notes.append("arms corrected by up to %.0f deg" % worst)
    finally:
        sub.destroy_actor(a1)
        sub.destroy_actor(a2)
    return ", ".join(notes)


def bake(ret, seq_path, src_mesh, tgt_mesh, final):
    if unreal.EditorAssetLibrary.does_asset_exist(final):
        unreal.EditorAssetLibrary.delete_asset(final)
    res = unreal.IKRetargetBatchOperation().duplicate_and_retarget(
        [unreal.EditorAssetLibrary.find_asset_data(seq_path)],
        src_mesh, tgt_mesh, ret, search="_Anim", replace="_kimodo_baked")
    if not res:
        raise RuntimeError("the bake produced nothing")
    # Never delete by the package name duplicate_and_retarget hands back: it can
    # collide with the source asset and the cleanup destroys the input instead.
    unreal.EditorAssetLibrary.rename_asset(str(res[0].package_name), final)
    unreal.EditorAssetLibrary.save_asset(final)
    return unreal.load_asset(final)


def check(src_seq, out_seq, spec):
    """Did the motion survive? Compares limb directions against the source and
    reports where the character ended up. Exact agreement is impossible: the
    skeletons have different proportions, which is the point of retargeting."""
    opts = unreal.AnimPoseEvaluationOptions()
    pl = out_seq.get_play_length()

    def d(seq, t, a, b):
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, t, opts)
        pa = unreal.AnimPoseExtensions.get_bone_pose(pose, a, unreal.AnimPoseSpaces.WORLD).translation
        pb = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation
        v = (pb.x - pa.x, pb.y - pa.y, pb.z - pa.z)
        l = math.sqrt(sum(x * x for x in v)) or 1.0
        return tuple(x / l for x in v)

    worst, at = 1.0, ""
    for t_from, t_to, s_from, s_to in spec["arms"]:
        for f in (0.1, 0.35, 0.6, 0.85):
            v = sum(p * q for p, q in
                    zip(d(src_seq, pl * f, s_from, s_to), d(out_seq, pl * f, t_from, t_to)))
            if v < worst:
                worst, at = v, t_from

    def bone(seq, t, b):
        return unreal.AnimPoseExtensions.get_bone_pose(
            unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, t, opts),
            b, unreal.AnimPoseSpaces.WORLD).translation

    toe = min(bone(out_seq, pl * f, b).z
              for f in (0.1, 0.3, 0.5, 0.7, 0.9) for b in ("ball_l", "ball_r"))
    p0, p1 = bone(out_seq, 0.05, "pelvis"), bone(out_seq, pl - 0.05, "pelvis")
    return ("arms match %.3f (worst %s), pelvis %.0f cm, lowest toe %.0f cm, "
            "travelled %.0f cm over %.1f s"
            % (worst, at, p0.z, toe, math.hypot(p1.x - p0.x, p1.y - p0.y), pl))


# ------------------------------------------------------------------- main

def process(glb, tgt_mesh, rig_tgt):
    name = os.path.splitext(os.path.basename(glb))[0]
    src_mesh, src_seq, mesh_path = import_glb(glb)

    names = bone_names(src_seq)
    spec = None
    for root, s in SKELETONS.items():
        if root in names:
            spec = dict(s)
            spec["root"] = root
            break
    if spec is None:
        raise RuntimeError(
            "%s has %d bones starting with %s, which is not a kimodo skeleton"
            % (name, len(names), names[0]))
    missing = [b for _, a, z in spec["chains"] for b in (a, z) if b not in names]
    if missing:
        raise RuntimeError("%s is missing expected bones: %s" % (name, missing))

    rig_src = make_rig("IK_kimodo_" + name, src_mesh, spec["root"], spec["chains"])
    rtg = "%s/RTG_%s" % (RIG_DIR, name)
    ret, rc, mapped, blank = build_retargeter(rtg, rig_src, rig_tgt, src_mesh, tgt_mesh)
    notes = fix_poses(rc, src_mesh, tgt_mesh, spec)

    unreal.EditorAssetLibrary.make_directory(OUT_DIR)
    final = "%s/A_%s" % (OUT_DIR, name)
    out_seq = bake(ret, mesh_path + "_Anim", src_mesh, tgt_mesh, final)
    unreal.EditorAssetLibrary.save_asset(rtg)

    log("%s: %s" % (name, spec["label"]))
    log("    %d chains mapped%s" % (
        len(mapped), (", %d left at rest (%s)" % (len(blank), ", ".join(blank))) if blank else ""))
    log("    " + notes)
    log("    " + check(src_seq, out_seq, spec))
    log("    -> " + final)
    return final


def main():
    args = [a for a in sys.argv[1:]]
    explicit = ""
    if args and args[-1].startswith("/Game/"):
        explicit = args.pop()
    globs = [a for a in args if a.lower().endswith(".glb")]
    if not globs:
        here = os.path.dirname(os.path.abspath(__file__))
        globs = sorted(os.path.join(here, f) for f in os.listdir(here)
                       if f.lower().endswith(".glb"))
        if not globs:
            raise SystemExit(
                "no .glb given, and none next to this script. Run "
                "kimodo_to_glb.py on a clip first, then pass the .glb path.")

    for d in (ROOT, SRC_DIR, RIG_DIR, OUT_DIR):
        unreal.EditorAssetLibrary.make_directory(d)
    tgt_mesh, tgt_path = find_target(explicit)
    log("target character: %s" % tgt_path)
    rig_tgt = make_rig("IK_target_auto", tgt_mesh)

    done, failed = [], []
    for g in globs:
        try:
            done.append(process(g, tgt_mesh, rig_tgt))
        except Exception as exc:
            failed.append("%s: %s" % (os.path.basename(g), exc))
            unreal.log_error("kimodo: %s" % failed[-1])
    log("")
    log("done: %d of %d" % (len(done), len(globs)))
    for f in failed:
        log("  failed  " + f)
    if done:
        log("  animations are in %s" % OUT_DIR)


main()
