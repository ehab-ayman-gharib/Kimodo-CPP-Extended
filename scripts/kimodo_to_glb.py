#!/usr/bin/env python3
"""Turn a kimodo motion clip into a .glb you can drag into Unreal Engine.

    python kimodo_to_glb.py path/to/clip
    python kimodo_to_glb.py path/to/clip -o walk.glb
    python kimodo_to_glb.py clips/*            (several at once)

A clip is the directory kimodo writes, holding:

    local_rotations_xyzw.f32     [frames, joints, 4] float32, local quaternions
    root_positions.f32           [frames, 3]         float32, pelvis in metres
    prompt.txt                   optional, only used to name the output

The result imports as a Skeletal Mesh plus an Anim Sequence in one step. Drag
it into the Content Browser and accept the defaults.

Requires nothing but Python 3.8 or newer. No Blender, no extra packages.

--- how it works, in case you need to change it -------------------------------

kimodo's axes are already glTF's axes: +X left, +Y up, +Z forward, right
handed, metres. So the numbers go straight in with no conversion, and Unreal's
glTF importer does the rest.

In kimodo's rest pose every joint orientation is the identity, so a bone's rest
transform is a pure translation by its parent-relative offset, and the animated
local quaternion is the node's rotation as-is. That makes the whole file almost
a transcription of the input.

A box is skinned rigidly to each bone. Without a mesh Unreal imports a bare
scene of transforms rather than a Skeletal Mesh, and there is nothing to
retarget from.
"""
import argparse
import json
import os
import struct
import sys

FLOAT = 5126
USHORT = 5123
TRIANGLES = 4

SKELETONS = {
    "smplx22": {
        "names": ["pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2", "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot", "neck", "left_collar", "right_collar", "head", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
        "parents": [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19],
        "offsets": [
            (0, 0, 0),
            (0.052299, -0.093936, -0.027607),
            (-0.057193, -0.106548, -0.022218),
            (-0.001496, 0.11293, -0.024981),
            (0.058867, -0.416442, -0.006557),
            (-0.048074, -0.39756, -0.014061),
            (0.0069, 0.145636, -0.006859),
            (-0.041738, -0.437584, -0.029512),
            (0.014489, -0.446853, -0.01803),
            (-0.010334, 0.056082, 0.021116),
            (0.049294, -0.065279, 0.126259),
            (-0.040575, -0.065287, 0.127076),
            (-0.011026, 0.171365, -0.028827),
            (0.047725, 0.087643, -0.008375),
            (-0.046636, 0.086612, -0.014864),
            (0.024654, 0.175391, 0.024463),
            (0.126285, 0.05768, -0.013885),
            (-0.109342, 0.053674, -0.009118),
            (0.272907, -0.069853, -0.039094),
            (-0.292029, -0.03544, -0.024565),
            (0.276174, 0.021254, -0.002478),
            (-0.271878, -0.004835, -0.016445),
        ],
    },
    "soma30": {
        "names": ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"],
        "parents": [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28],
        "offsets": [
            (0, 0, 0),
            (-0.00013727, 0.0500376, -0.000537267),
            (-2e-09, 0.071253, -0.000298249),
            (-6e-09, 0.0755006, -0.00815971),
            (-0.00181676, 0.263113, -0.00553348),
            (-2.9e-08, 0.077094, 0.0230259),
            (-4.6e-08, 0.0612892, 0.0195371),
            (2.6369e-05, 0.00475592, 0.0309494),
            (0.0320638, 0.053802, 0.0758688),
            (-0.0322244, 0.0536187, 0.0755823),
            (0.0162165, 0.232372, 0.0511341),
            (0.149198, 2.2e-08, -0.0550233),
            (0.287393, 3e-09, -2.5879e-05),
            (0.27094, -7e-09, 2.609e-05),
            (0.122686, -0.0322018, 0.0483307),
            (0.19012, -0.00312878, -0.00033957),
            (-0.0138012, 0.231803, 0.0521416),
            (-0.150372, 1.17e-07, -0.055456),
            (-0.287366, 1.9e-08, -2.5971e-05),
            (-0.271336, -1e-09, 2.6127e-05),
            (-0.122642, -0.0321145, 0.0480404),
            (-0.190006, -0.00306616, -0.000315734),
            (0.100432, -0.0843453, 0.0259565),
            (-1e-08, -0.432218, -0.00802913),
            (1e-08, -0.421551, -0.0348152),
            (0, -0.0505947, 0.132315),
            (-0.100473, -0.0829526, 0.0262032),
            (1e-08, -0.433622, -0.00805556),
            (2e-08, -0.421174, -0.034784),
            (-3e-09, -0.0507961, 0.132842),
        ],
    },
    "g1skel34": {
        "names": ["pelvis_skel", "left_hip_pitch_skel", "left_hip_roll_skel", "left_hip_yaw_skel", "left_knee_skel", "left_ankle_pitch_skel", "left_ankle_roll_skel", "left_toe_base", "right_hip_pitch_skel", "right_hip_roll_skel", "right_hip_yaw_skel", "right_knee_skel", "right_ankle_pitch_skel", "right_ankle_roll_skel", "right_toe_base", "waist_yaw_skel", "waist_roll_skel", "waist_pitch_skel", "left_shoulder_pitch_skel", "left_shoulder_roll_skel", "left_shoulder_yaw_skel", "left_elbow_skel", "left_wrist_roll_skel", "left_wrist_pitch_skel", "left_wrist_yaw_skel", "left_hand_roll_skel", "right_shoulder_pitch_skel", "right_shoulder_roll_skel", "right_shoulder_yaw_skel", "right_elbow_skel", "right_wrist_roll_skel", "right_wrist_pitch_skel", "right_wrist_yaw_skel", "right_hand_roll_skel"],
        "parents": [-1, 0, 1, 2, 3, 4, 5, 6, 0, 8, 9, 10, 11, 12, 13, 0, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 17, 26, 27, 28, 29, 30, 31, 32],
        "offsets": [
            (0, 0, 0),
            (0.064452, -0.1027, 0),
            (0.052, -0.030465, 0),
            (0, -0.12412, 0.025001),
            (0.0021489, -0.17734, -0.078273),
            (-9.4445e-05, -0.30001, 0),
            (0, -0.017558, 0),
            (0, -0.035, 0.14),
            (-0.064452, -0.1027, 0),
            (-0.052, -0.030465, 0),
            (0, -0.12412, 0.025001),
            (-0.0021489, -0.17734, -0.078273),
            (9.4445e-05, -0.30001, 0),
            (0, -0.017558, 0),
            (0, -0.035, 0.14),
            (0, 0, 0),
            (0, 0.044, -0.0039635),
            (0, 0, 0),
            (0.10022, 0.24778, 0.0039563),
            (0.038, -0.013831, 0),
            (0.00624, -0.1032, 0),
            (0, -0.080518, 0.015783),
            (0.00188791, -0.01, 0.1),
            (0, 0, 0.038),
            (0, 0, 0.046),
            (0, 0, 0.1),
            (-0.10021, 0.24778, 0.0039563),
            (-0.038, -0.013831, 0),
            (-0.00624, -0.1032, 0),
            (0, -0.080518, 0.015783),
            (-0.00188791, -0.01, 0.1),
            (0, 0, 0.038),
            (0, 0, 0.046),
            (0, 0, 0.1),
        ],
    },
}

# SMPL-X only: the mannequin bone names, so Unreal's IK Retargeter can map this
# onto Manny or a MetaHuman without a hand-written chain list. SOMA and G1 have
# no mannequin equivalent (G1 splits every hip into three single-axis joints and
# has no clavicle, neck or head), so they keep their own names.
SMPLX_TO_UE = {
    "pelvis": "pelvis", "left_hip": "thigh_l", "right_hip": "thigh_r",
    "spine1": "spine_01", "left_knee": "calf_l", "right_knee": "calf_r",
    "spine2": "spine_02", "left_ankle": "foot_l", "right_ankle": "foot_r",
    "spine3": "spine_03", "left_foot": "ball_l", "right_foot": "ball_r",
    "neck": "neck_01", "left_collar": "clavicle_l", "right_collar": "clavicle_r",
    "head": "head", "left_shoulder": "upperarm_l", "right_shoulder": "upperarm_r",
    "left_elbow": "lowerarm_l", "right_elbow": "lowerarm_r",
    "left_wrist": "hand_l", "right_wrist": "hand_r",
}

STOP_WORDS = {"a", "an", "the", "person", "someone", "their", "them", "and",
              "with", "then", "while", "is", "are", "of", "in", "on"}


def fail(msg):
    sys.stderr.write("error: %s\n" % msg)
    raise SystemExit(1)


# ------------------------------------------------------------------- input

def read_f32(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) % 4:
        fail("%s is %d bytes, not a whole number of float32" % (path, len(data)))
    return struct.unpack("<%df" % (len(data) // 4), data)


def load_clip(path):
    rot_path = os.path.join(path, "local_rotations_xyzw.f32")
    root_path = os.path.join(path, "root_positions.f32")
    for p in (rot_path, root_path):
        if not os.path.isfile(p):
            fail("%s is not a kimodo clip directory: no %s" % (path, os.path.basename(p)))
    rots, roots = read_f32(rot_path), read_f32(root_path)
    if len(roots) % 3:
        fail("%s holds %d floats, not a multiple of 3" % (root_path, len(roots)))
    frames = len(roots) // 3
    if frames < 2:
        fail("%s has %d frames" % (path, frames))
    if len(rots) % (frames * 4):
        fail("rotation and root files disagree: %d floats over %d frames"
             % (len(rots), frames))
    joints = len(rots) // (frames * 4)

    match = [k for k, s in SKELETONS.items() if len(s["parents"]) == joints]
    if not match:
        fail("%d joints matches no known skeleton (expected %s)"
             % (joints, ", ".join("%d" % len(s["parents"]) for s in SKELETONS.values())))
    skel = SKELETONS[match[0]]

    # quaternions must be unit length; anything else means the file is not
    # what it claims to be, and the result would be silently distorted
    worst = 0.0
    for i in range(0, len(rots), 4):
        n = sum(rots[i + k] ** 2 for k in range(4)) ** 0.5
        worst = max(worst, abs(n - 1.0))
    if worst > 1e-3:
        fail("rotations are not unit quaternions (off by %.4f); wrong file?" % worst)

    return {"key": match[0], "skel": skel, "frames": frames, "joints": joints,
            "rots": rots, "roots": roots, "worst_norm": worst}


def clip_name(path, clip):
    leaf = os.path.basename(os.path.normpath(path))
    prompt_path = os.path.join(path, "prompt.txt")
    if not leaf.strip("0123456789abcdef") and os.path.isfile(prompt_path):
        leaf = ""  # a bare hex id says nothing, prefer the prompt
    if not leaf and os.path.isfile(prompt_path):
        with open(prompt_path, encoding="utf-8", errors="replace") as fh:
            words = [w for w in "".join(
                c if c.isalnum() else " " for c in fh.read()).split()
                if w.lower() not in STOP_WORDS]
        leaf = "_".join(words[:4]).lower()
    if not leaf:
        leaf = "kimodo_clip"
    name = "".join(c if (c.isalnum() or c == "_") else "_" for c in leaf)
    if name[:1].isdigit():
        name = "A_" + name
    if not name.endswith("_%d" % clip["frames"]):
        name += "_%d" % clip["frames"]
    return name


# --------------------------------------------------------------- geometry

def rest_positions(skel):
    """Rest world position of each joint. Rest orientations are the identity,
    so this is just the offsets accumulated down the hierarchy."""
    pos = []
    for j, p in enumerate(skel["parents"]):
        o = skel["offsets"][j]
        pos.append(o if p < 0 else tuple(pos[p][k] + o[k] for k in range(3)))
    return pos


def bone_boxes(skel, rest):
    """One thin box per joint, rigidly weighted to that joint.

    The box runs from the joint to its first child. Joints with no child get a
    stub continuing the direction they came in on, so leaves stay visible.
    """
    children = {}
    for j, p in enumerate(skel["parents"]):
        if p >= 0:
            children.setdefault(p, []).append(j)

    verts, joints_attr, weights, idx = [], [], [], []
    for j in range(len(skel["parents"])):
        head = rest[j]
        kids = children.get(j)
        if kids:
            tail = rest[kids[0]]
        else:
            p = skel["parents"][j]
            back = [head[k] - rest[p][k] for k in range(3)] if p >= 0 else [0.0, 0.05, 0.0]
            length = sum(v * v for v in back) ** 0.5
            if length < 1e-6:
                back, length = [0.0, 0.05, 0.0], 0.05
            tail = tuple(head[k] + back[k] / length * min(0.09, length * 0.5) for k in range(3))

        axis = [tail[k] - head[k] for k in range(3)]
        length = sum(v * v for v in axis) ** 0.5
        if length < 1e-6:
            axis, length = [0.0, 0.03, 0.0], 0.03
        z = [v / length for v in axis]
        helper = [0.0, 0.0, 1.0] if abs(z[2]) < 0.9 else [1.0, 0.0, 0.0]
        x = [z[1] * helper[2] - z[2] * helper[1],
             z[2] * helper[0] - z[0] * helper[2],
             z[0] * helper[1] - z[1] * helper[0]]
        xl = sum(v * v for v in x) ** 0.5 or 1.0
        x = [v / xl for v in x]
        y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]]
        half = max(0.008, min(0.02, length * 0.12))

        base = len(verts)
        for end in (head, tail):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append(tuple(end[k] + x[k] * sx * half + y[k] * sy * half
                                   for k in range(3)))
                joints_attr.append((j, 0, 0, 0))
                weights.append((1.0, 0.0, 0.0, 0.0))
        quads = [(0, 1, 2, 3), (7, 6, 5, 4)]
        for i in range(4):
            quads.append((i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i))
        for a, b, c, d in quads:
            idx += [base + a, base + b, base + c, base + a, base + c, base + d]
    return verts, joints_attr, weights, idx


# ------------------------------------------------------------------- glTF

class Buffer:
    """Collects binary blobs and hands back accessor indices."""

    def __init__(self):
        self.blob = bytearray()
        self.views = []
        self.accessors = []

    def _view(self, data, target=None):
        while len(self.blob) % 4:
            self.blob.append(0)
        view = {"buffer": 0, "byteOffset": len(self.blob), "byteLength": len(data)}
        if target is not None:
            view["target"] = target
        self.blob += data
        self.views.append(view)
        return len(self.views) - 1

    def add(self, values, kind, ctype, target=None, minmax=False):
        ncomp = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[kind]
        fmt = {FLOAT: "f", USHORT: "H"}[ctype]
        flat = []
        for v in values:
            flat.extend(v if isinstance(v, (tuple, list)) else (v,))
        data = struct.pack("<%d%s" % (len(flat), fmt), *flat)
        acc = {"bufferView": self._view(data, target), "componentType": ctype,
               "count": len(values), "type": kind}
        if minmax:
            cols = list(zip(*[v if isinstance(v, (tuple, list)) else (v,) for v in values]))
            acc["min"] = [min(c) for c in cols]
            acc["max"] = [max(c) for c in cols]
        self.accessors.append(acc)
        return len(self.accessors) - 1


def build_glb(clip, name, fps, bone_names):
    skel = clip["skel"]
    parents = skel["parents"]
    J, T = clip["joints"], clip["frames"]
    rest = rest_positions(skel)
    buf = Buffer()

    nodes = []
    for j in range(J):
        node = {"name": bone_names[j], "translation": list(skel["offsets"][j])}
        kids = [k for k, p in enumerate(parents) if p == j]
        if kids:
            node["children"] = kids
        nodes.append(node)

    verts, jattr, weights, idx = bone_boxes(skel, rest)
    a_pos = buf.add(verts, "VEC3", FLOAT, target=34962, minmax=True)
    a_joint = buf.add(jattr, "VEC4", USHORT, target=34962)
    a_weight = buf.add(weights, "VEC4", FLOAT, target=34962)
    a_index = buf.add(idx, "SCALAR", USHORT, target=34963)

    # Rest orientations are the identity, so a bone's inverse bind matrix is
    # just a translation by minus its rest position. glTF matrices are column
    # major, hence the translation sitting in the last four slots.
    ibm = [(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -p[0], -p[1], -p[2], 1) for p in rest]
    a_ibm = buf.add(ibm, "MAT4", FLOAT)

    mesh_node = len(nodes)
    nodes.append({"name": name + "_proxy", "mesh": 0, "skin": 0})

    times = [i / float(fps) for i in range(T)]
    a_time = buf.add(times, "SCALAR", FLOAT, minmax=True)
    samplers, channels = [], []
    for j in range(J):
        quats = [tuple(clip["rots"][(t * J + j) * 4 + k] for k in range(4)) for t in range(T)]
        samplers.append({"input": a_time, "output": buf.add(quats, "VEC4", FLOAT),
                         "interpolation": "LINEAR"})
        channels.append({"sampler": len(samplers) - 1,
                         "target": {"node": j, "path": "rotation"}})
    root_pos = [tuple(clip["roots"][t * 3 + k] for k in range(3)) for t in range(T)]
    samplers.append({"input": a_time, "output": buf.add(root_pos, "VEC3", FLOAT),
                     "interpolation": "LINEAR"})
    channels.append({"sampler": len(samplers) - 1, "target": {"node": 0, "path": "translation"}})

    gltf = {
        "asset": {"version": "2.0", "generator": "kimodo_to_glb.py"},
        "scene": 0,
        "scenes": [{"nodes": [0, mesh_node]}],
        "nodes": nodes,
        "materials": [{"name": "kimodo_proxy", "pbrMetallicRoughness": {
            "baseColorFactor": [0.62, 0.64, 0.67, 1.0],
            "metallicFactor": 0.0, "roughnessFactor": 0.8}}],
        "meshes": [{"name": name, "primitives": [{
            "attributes": {"POSITION": a_pos, "JOINTS_0": a_joint, "WEIGHTS_0": a_weight},
            "indices": a_index, "material": 0, "mode": TRIANGLES}]}],
        "skins": [{"name": name + "_skin", "joints": list(range(J)),
                   "inverseBindMatrices": a_ibm, "skeleton": 0}],
        "animations": [{"name": name, "samplers": samplers, "channels": channels}],
        "bufferViews": buf.views,
        "accessors": buf.accessors,
        "buffers": [{"byteLength": len(buf.blob)}],
    }

    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)
    bin_blob = bytes(buf.blob) + b"\0" * (-len(buf.blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(bin_blob)
    out = bytearray()
    out += struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<I4s", len(js), b"JSON") + js
    out += struct.pack("<I4s", len(bin_blob), b"BIN\0") + bin_blob
    return bytes(out), len(verts), len(idx) // 3


# -------------------------------------------------------------- self check

def self_check(clip, glb):
    """Decode what was just written and compare it against forward kinematics
    on the raw input.

    The hierarchy, the bone offsets, the quaternions and the root track are all
    read back out of the file, not reused from memory, so this catches a
    shuffled parent list, a wrong axis, a quaternion written in the wrong
    component order, and a bad accessor offset. It also checks the skin's
    inverse bind matrices against the rest pose, because a wrong one skins the
    mesh into a knot while the skeleton itself still animates correctly.
    """
    if struct.unpack_from("<4sII", glb, 0) != (b"glTF", 2, len(glb)):
        return "container header does not describe this file"
    jlen, = struct.unpack_from("<I", glb, 12)
    doc = json.loads(glb[20:20 + jlen].decode("utf-8"))
    blob = glb[20 + jlen + 8:]

    def read(acc_i):
        a = doc["accessors"][acc_i]
        v = doc["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        f = {FLOAT: "f", USHORT: "H"}[a["componentType"]]
        w = struct.calcsize("<" + f)
        off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        return [struct.unpack_from("<%d%s" % (n, f), blob, off + i * n * w)
                for i in range(a["count"])]

    J, T = clip["joints"], clip["frames"]
    joints = doc["skins"][0]["joints"]
    if joints != list(range(J)):
        return "skin joints are not the first %d nodes" % J

    # hierarchy and offsets as the file states them
    file_parents = [-1] * J
    for i in joints:
        for c in doc["nodes"][i].get("children", []):
            if c < J:
                file_parents[c] = i
    file_offsets = [tuple(doc["nodes"][i].get("translation", [0.0, 0.0, 0.0])) for i in joints]
    if file_parents != list(clip["skel"]["parents"]):
        return "hierarchy in the file does not match the skeleton"

    chan = {}
    anim = doc["animations"][0]
    for c in anim["channels"]:
        chan[(c["target"]["node"], c["target"]["path"])] = anim["samplers"][c["sampler"]]
    missing = [j for j in range(J) if (j, "rotation") not in chan]
    if missing or (0, "translation") not in chan:
        return "missing animation channels for %s" % (missing or "the root")

    def qmul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz)

    def rot(q, v):
        x, y, z, w = q
        cx, cy, cz = y * v[2] - z * v[1], z * v[0] - x * v[2], x * v[1] - y * v[0]
        dx, dy, dz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
        return (v[0] + 2 * (w * cx + dx), v[1] + 2 * (w * cy + dy), v[2] + 2 * (w * cz + dz))

    def fk(parents, offsets, getq, root):
        gq, pos = [None] * J, [None] * J
        for j in range(J):
            p = parents[j]
            if p < 0:
                gq[j], pos[j] = getq(j), root
            else:
                gq[j] = qmul(gq[p], getq(j))
                r = rot(gq[p], offsets[j])
                pos[j] = (pos[p][0] + r[0], pos[p][1] + r[1], pos[p][2] + r[2])
        return pos

    src_parents = list(clip["skel"]["parents"])
    src_offsets = [tuple(o) for o in clip["skel"]["offsets"]]
    file_q = {j: read(chan[(j, "rotation")]["output"]) for j in range(J)}
    file_root = read(chan[(0, "translation")]["output"])
    times = read(chan[(0, "translation")]["input"])
    if len(file_root) != T or len(times) != T:
        return "animation has %d samples for %d frames" % (len(file_root), T)

    worst = 0.0
    for t in sorted({0, T // 3, T // 2, T - 1}):
        want = fk(src_parents, src_offsets,
                  lambda j: tuple(clip["rots"][(t * J + j) * 4 + k] for k in range(4)),
                  tuple(clip["roots"][t * 3 + k] for k in range(3)))
        got = fk(file_parents, file_offsets, lambda j: file_q[j][t], file_root[t])
        for a, b in zip(want, got):
            worst = max(worst, max(abs(a[k] - b[k]) for k in range(3)))

    # inverse bind matrices must undo the rest pose
    rest = rest_positions(clip["skel"])
    for j, m in enumerate(read(doc["skins"][0]["inverseBindMatrices"])):
        for k in range(3):
            worst = max(worst, abs(m[12 + k] + rest[j][k]))

    # every skin weight must reference a real joint and sum to one
    prim = doc["meshes"][0]["primitives"][0]
    for (a, _, _, _), (w, _, _, _) in zip(read(prim["attributes"]["JOINTS_0"]),
                                          read(prim["attributes"]["WEIGHTS_0"])):
        if a >= J or abs(w - 1.0) > 1e-6:
            return "bad skin weight: joint %d weight %.4f" % (a, w)
    return worst


# -------------------------------------------------------------------- main

def convert(path, out_path, fps, names_mode):
    clip = load_clip(path)
    skel = clip["skel"]
    if names_mode == "ue" and clip["key"] == "smplx22":
        bone_names = [SMPLX_TO_UE[n] for n in skel["names"]]
        naming = "UE mannequin"
    else:
        bone_names = list(skel["names"])
        naming = "native"

    name = os.path.splitext(os.path.basename(out_path))[0]
    glb, nverts, ntris = build_glb(clip, name, fps, bone_names)
    err = self_check(clip, glb)
    if not isinstance(err, float) or err > 1e-5:
        fail("self check failed on %s: %s" % (path, err))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(glb)
    print("%s\n    %s, %d joints, %s names, %d frames @ %d fps (%.1fs)"
          % (out_path, clip["key"], clip["joints"], naming, clip["frames"], fps,
             clip["frames"] / float(fps)))
    print("    proxy mesh %d verts / %d tris, %.1f KB, check %.2e m"
          % (nverts, ntris, len(glb) / 1024.0, err))
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="Convert a kimodo motion clip into a .glb for Unreal Engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Drag the .glb into Unreal's Content Browser and accept the defaults.")
    ap.add_argument("clips", nargs="+", help="kimodo clip directory")
    ap.add_argument("-o", "--output", default="",
                    help="output .glb (single clip only; default is next to this script)")
    ap.add_argument("--outdir", default="", help="directory for the outputs")
    ap.add_argument("--fps", type=float, default=30.0, help="frame rate (default 30)")
    ap.add_argument("--names", choices=["ue", "native"], default="ue",
                    help="SMPL-X bone naming: 'ue' matches the mannequin so the IK "
                         "Retargeter can map it; 'native' keeps kimodo's names. "
                         "SOMA and G1 always keep their own.")
    args = ap.parse_args()

    if args.output and len(args.clips) > 1:
        fail("-o takes a single clip; use --outdir for several")
    if args.fps <= 0:
        fail("--fps must be positive")

    ok = 0
    for path in args.clips:
        if not os.path.isdir(path):
            sys.stderr.write("skipping %s: not a directory\n" % path)
            continue
        if args.output:
            out = args.output
        else:
            clip = load_clip(path)
            base = clip_name(path, clip) + ".glb"
            out = os.path.join(args.outdir or os.path.dirname(os.path.abspath(__file__)), base)
        convert(path, out, args.fps, args.names)
        ok += 1
    if not ok:
        fail("nothing converted")


if __name__ == "__main__":
    main()

