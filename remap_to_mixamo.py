#!/usr/bin/env python3
"""
Converts Kimodo GLB animations to Mixamo bone hierarchy naming (mixamorig:*)
so they play directly on Mixamo character models in Unity/Unreal/Blender.
"""

import sys
import json
import struct
from pathlib import Path

# Mapping SOMA 30 joint names -> Mixamo standard bone names
SOMA_TO_MIXAMO = {
    "Hips": "mixamorig:Hips",
    "Spine1": "mixamorig:Spine",
    "Spine2": "mixamorig:Spine1",
    "Chest": "mixamorig:Spine2",
    "Neck1": "mixamorig:Neck",
    "Neck2": "mixamorig:Neck1",
    "Head": "mixamorig:Head",
    "Jaw": "mixamorig:Jaw",
    "LeftEye": "mixamorig:LeftEye",
    "RightEye": "mixamorig:RightEye",
    "LeftShoulder": "mixamorig:LeftShoulder",
    "LeftArm": "mixamorig:LeftArm",
    "LeftForeArm": "mixamorig:LeftForeArm",
    "LeftHand": "mixamorig:LeftHand",
    "LeftHandThumbEnd": "mixamorig:LeftHandThumb4",
    "LeftHandMiddleEnd": "mixamorig:LeftHandMiddle4",
    "RightShoulder": "mixamorig:RightShoulder",
    "RightArm": "mixamorig:RightArm",
    "RightForeArm": "mixamorig:RightForeArm",
    "RightHand": "mixamorig:RightHand",
    "RightHandThumbEnd": "mixamorig:RightHandThumb4",
    "RightHandMiddleEnd": "mixamorig:RightHandMiddle4",
    "LeftLeg": "mixamorig:LeftUpLeg",
    "LeftShin": "mixamorig:LeftLeg",
    "LeftFoot": "mixamorig:LeftFoot",
    "LeftToeBase": "mixamorig:LeftToeBase",
    "RightLeg": "mixamorig:RightUpLeg",
    "RightShin": "mixamorig:RightLeg",
    "RightFoot": "mixamorig:RightFoot",
    "RightToeBase": "mixamorig:RightToeBase"
}

# Mapping SMPL-X 22 joint names -> Mixamo standard bone names
SMPLX_TO_MIXAMO = {
    "pelvis": "mixamorig:Hips",
    "left_hip": "mixamorig:LeftUpLeg",
    "right_hip": "mixamorig:RightUpLeg",
    "spine1": "mixamorig:Spine",
    "left_knee": "mixamorig:LeftLeg",
    "right_knee": "mixamorig:RightLeg",
    "spine2": "mixamorig:Spine1",
    "left_ankle": "mixamorig:LeftFoot",
    "right_ankle": "mixamorig:RightFoot",
    "spine3": "mixamorig:Spine2",
    "left_foot": "mixamorig:LeftToeBase",
    "right_foot": "mixamorig:RightToeBase",
    "neck": "mixamorig:Neck",
    "left_collar": "mixamorig:LeftShoulder",
    "right_collar": "mixamorig:RightShoulder",
    "head": "mixamorig:Head",
    "left_shoulder": "mixamorig:LeftArm",
    "right_shoulder": "mixamorig:RightArm",
    "left_elbow": "mixamorig:LeftForeArm",
    "right_elbow": "mixamorig:RightForeArm",
    "left_wrist": "mixamorig:LeftHand",
    "right_wrist": "mixamorig:RightHand"
}

def remap_glb(input_path: Path, output_path: Path):
    data = input_path.read_bytes()
    if len(data) < 20:
        raise ValueError("File too small to be a valid GLB")

    magic, version, length, json_len, json_type = struct.unpack("<IIIII", data[:20])
    if magic != 0x46546C67 or json_type != 0x4E4F534A:
        raise ValueError("Invalid GLB header")

    json_bytes = data[20 : 20 + json_len]
    bin_offset = 20 + json_len
    bin_chunk_header = data[bin_offset : bin_offset + 8]
    bin_data = data[bin_offset + 8 :]

    gltf = json.loads(json_bytes.decode("utf-8"))

    # Remap node names
    for node in gltf.get("nodes", []):
        name = node.get("name", "")
        if name in SOMA_TO_MIXAMO:
            node["name"] = SOMA_TO_MIXAMO[name]
        elif name in SMPLX_TO_MIXAMO:
            node["name"] = SMPLX_TO_MIXAMO[name]
        elif not name.startswith("mixamorig:"):
            node["name"] = f"mixamorig:{name}"

    new_json_str = json.dumps(gltf, separators=(',', ':')).encode("utf-8")
    while len(new_json_str) % 4 != 0:
        new_json_str += b' '

    total_len = 12 + 8 + len(new_json_str) + 8 + len(bin_data)
    out = bytearray()
    out.extend(struct.pack("<I", 0x46546C67)) # glTF magic
    out.extend(struct.pack("<I", 2))          # version 2
    out.extend(struct.pack("<I", total_len))
    out.extend(struct.pack("<I", len(new_json_str)))
    out.extend(struct.pack("<I", 0x4E4F534A)) # JSON
    out.extend(new_json_str)
    out.extend(struct.pack("<I", len(bin_data)))
    out.extend(struct.pack("<I", 0x004E4942)) # BIN
    out.extend(bin_data)

    output_path.write_bytes(out)
    print(f"Successfully remapped: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remap_to_mixamo.py <input.glb> [output_mixamo.glb]")
        sys.exit(1)

    inp = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        out = Path(sys.argv[2])
    else:
        out = inp.parent / f"{inp.stem}_mixamo.glb"

    remap_glb(inp, out)
