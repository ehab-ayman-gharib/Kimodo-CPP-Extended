#!/usr/bin/env python3
"""
Web GUI Launcher for Kimodo.cpp (Python-based standalone server).
Supports text-to-motion generation, 3D skeleton preview, standard GLB / Mixamo GLB downloads,
and Custom Character Retargeting (.fbx / .glb) with Live 3D Mesh Dual-Viewport.
"""

import sys
import os
import json
import time
import shutil
import struct
import base64
import secrets
import threading
import subprocess
import http.server
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone

PORT = 8094
ROOT_DIR = Path(__file__).parent.resolve()
DEMO_DIR = ROOT_DIR / "demo"
OUTPUT_DIR = ROOT_DIR / "demo-output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Skeleton definitions
SKELETONS = {
    "smplx22": {
        "names": ["pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2", "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot", "neck", "left_collar", "right_collar", "head", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
        "parents": [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19],
        "offsets": [
            [0, 0, 0], [0.052299, -0.093936, -0.027607], [-0.057193, -0.106548, -0.022218], [-0.001496, 0.11293, -0.024981], [0.058867, -0.416442, -0.006557], [-0.048074, -0.39756, -0.014061], [0.0069, 0.145636, -0.006859], [-0.041738, -0.437584, -0.029512], [0.014489, -0.446853, -0.01803], [-0.010334, 0.056082, 0.021116], [0.049294, -0.065279, 0.126259], [-0.040575, -0.065287, 0.127076], [-0.011026, 0.171365, -0.028827], [0.047725, 0.087643, -0.008375], [-0.046636, 0.086612, -0.014864], [0.024654, 0.175391, 0.024463], [0.126285, 0.05768, -0.013885], [-0.109342, 0.053674, -0.009118], [0.272907, -0.069853, -0.039094], [-0.292029, -0.03544, -0.024565], [0.276174, 0.021254, -0.002478], [-0.271878, -0.004835, -0.016445]
        ]
    },
    "soma30": {
        "names": ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"],
        "parents": [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28],
        "offsets": [
            [0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]
        ]
    },
    "g1skel34": {
        "names": ["pelvis_skel", "left_hip_pitch_skel", "left_hip_roll_skel", "left_hip_yaw_skel", "left_knee_skel", "left_ankle_pitch_skel", "left_ankle_roll_skel", "left_toe_base", "right_hip_pitch_skel", "right_hip_roll_skel", "right_hip_yaw_skel", "right_knee_skel", "right_ankle_pitch_skel", "right_ankle_roll_skel", "right_toe_base", "waist_yaw_skel", "waist_roll_skel", "waist_pitch_skel", "left_shoulder_pitch_skel", "left_shoulder_roll_skel", "left_shoulder_yaw_skel", "left_elbow_skel", "left_wrist_roll_skel", "left_wrist_pitch_skel", "left_wrist_yaw_skel", "left_hand_roll_skel", "right_shoulder_pitch_skel", "right_shoulder_roll_skel", "right_shoulder_yaw_skel", "right_elbow_skel", "right_wrist_roll_skel", "right_wrist_pitch_skel", "right_wrist_yaw_skel", "right_hand_roll_skel"],
        "parents": [-1, 0, 1, 2, 3, 4, 5, 6, 0, 8, 9, 10, 11, 12, 13, 0, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 17, 26, 27, 28, 29, 30, 31, 32],
        "offsets": [
            [0, 0, 0], [0.064452, -0.1027, 0], [0.052, -0.030465, 0], [0, -0.12412, 0.025001], [0.0021489, -0.17734, -0.078273], [-9.4445e-05, -0.30001, 0], [0, -0.017558, 0], [0, -0.035, 0.14], [-0.064452, -0.1027, 0], [-0.052, -0.030465, 0], [0, -0.12412, 0.025001], [-0.0021489, -0.17734, -0.078273], [9.4445e-05, -0.30001, 0], [0, -0.017558, 0], [0, -0.035, 0.14], [0, 0, 0], [0, 0.044, -0.0039635], [0, 0, 0], [0.10022, 0.24778, 0.0039563], [0.038, -0.013831, 0], [0.00624, -0.1032, 0], [0, -0.080518, 0.015783], [0.00188791, -0.01, 0.1], [0, 0, 0.038], [0, 0, 0.046], [0, 0, 0.1], [-0.10021, 0.24778, 0.0039563], [-0.038, -0.013831, 0], [-0.00624, -0.1032, 0], [0, -0.080518, 0.015783], [-0.00188791, -0.01, 0.1], [0, 0, 0.038], [0, 0, 0.046], [0, 0, 0.1]
        ]
    }
}

MODELS = {
    "soma-rp-v1.1": {
        "id": "soma-rp-v1.1",
        "label": "SOMA RP v1.1",
        "skeleton": "SOMA (30 joints)",
        "skeleton_key": "soma30",
        "upstream": "nvidia/Kimodo-SOMA-RP-v1.1",
        "license": "NVIDIA Open Model License",
        "commercial": True,
        "path": ROOT_DIR / "models/kimodo-soma-rp-v1.1-f32.gguf"
    },
    "soma-seed-v1.1": {
        "id": "soma-seed-v1.1",
        "label": "SOMA SEED v1.1",
        "skeleton": "SOMA (30 joints)",
        "skeleton_key": "soma30",
        "upstream": "nvidia/Kimodo-SOMA-SEED-v1.1",
        "license": "NVIDIA Open Model License",
        "commercial": True,
        "path": ROOT_DIR / "models/kimodo-soma-seed-v1.1-f32.gguf"
    },
    "g1-rp-v1": {
        "id": "g1-rp-v1",
        "label": "G1 RP v1",
        "skeleton": "Unitree G1 (34 joints)",
        "skeleton_key": "g1skel34",
        "upstream": "nvidia/Kimodo-G1-RP-v1",
        "license": "NVIDIA Open Model License",
        "commercial": True,
        "path": ROOT_DIR / "models/kimodo-g1-rp-v1-f32.gguf"
    },
    "g1-seed-v1": {
        "id": "g1-seed-v1",
        "label": "G1 SEED v1",
        "skeleton": "Unitree G1 (34 joints)",
        "skeleton_key": "g1skel34",
        "upstream": "nvidia/Kimodo-G1-SEED-v1",
        "license": "NVIDIA Open Model License",
        "commercial": True,
        "path": ROOT_DIR / "models/kimodo-g1-seed-v1-f32.gguf"
    },
    "smplx-rp-v1": {
        "id": "smplx-rp-v1",
        "label": "SMPL-X RP v1",
        "skeleton": "SMPL-X (22 joints)",
        "skeleton_key": "smplx22",
        "upstream": "nvidia/Kimodo-SMPLX-RP-v1",
        "license": "NVIDIA Internal Scientific R&D License",
        "commercial": False,
        "path": ROOT_DIR / "models/kimodo-smplx-rp-v1-f32.gguf"
    }
}

def export_skeleton_glb(dir_path: Path, skeleton_key: str):
    skel = SKELETONS.get(skeleton_key)
    if not skel:
        return
    rot_file = dir_path / "local_rotations_xyzw.f32"
    root_file = dir_path / "root_positions.f32"
    if not rot_file.is_file() or not root_file.is_file():
        return

    rots = rot_file.read_bytes()
    roots = root_file.read_bytes()
    num_frames = len(roots) // 12
    num_joints = len(skel["names"])

    nodes = []
    for j in range(num_joints):
        node = {
            "name": skel["names"][j],
            "translation": skel["offsets"][j]
        }
        kids = [k for k, p in enumerate(skel["parents"]) if p == j]
        if kids:
            node["children"] = kids
        nodes.append(node)

    times = bytearray()
    for f in range(num_frames):
        times.extend(struct.pack("<f", f / 30.0))

    bin_data = bytearray()
    time_offset = len(bin_data)
    bin_data.extend(times)

    while len(bin_data) % 4 != 0:
        bin_data.append(0)
    root_offset = len(bin_data)
    bin_data.extend(roots)

    while len(bin_data) % 4 != 0:
        bin_data.append(0)
    rot_offset = len(bin_data)
    bin_data.extend(rots)

    buffer_views = [
        {"buffer": 0, "byteOffset": time_offset, "byteLength": len(times)},
        {"buffer": 0, "byteOffset": root_offset, "byteLength": len(roots)},
        {"buffer": 0, "byteOffset": rot_offset, "byteLength": len(rots)}
    ]

    accessors = [
        {"bufferView": 0, "componentType": 5126, "count": num_frames, "type": "SCALAR", "min": [0.0], "max": [(num_frames - 1) / 30.0]},
        {"bufferView": 1, "componentType": 5126, "count": num_frames, "type": "VEC3"},
        {"bufferView": 2, "componentType": 5126, "count": num_frames * num_joints, "type": "VEC4"}
    ]

    samplers = [
        {"input": 0, "output": 1, "interpolation": "LINEAR"},
        {"input": 0, "output": 2, "interpolation": "LINEAR"}
    ]

    channels = [
        {"sampler": 0, "target": {"node": 0, "path": "translation"}}
    ]
    for j in range(num_joints):
        channels.append({
            "sampler": 1,
            "target": {"node": j, "path": "rotation"}
        })

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "kimodo-cpp-gui"},
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
        "animations": [{
            "name": "kimodo_motion",
            "samplers": samplers,
            "channels": channels
        }],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "buffers": [{"byteLength": len(bin_data)}]
    }

    json_str = json.dumps(gltf_dict).encode('utf-8')
    while len(json_str) % 4 != 0:
        json_str += b' '
    while len(bin_data) % 4 != 0:
        bin_data += b'\x00'

    total_len = 12 + 8 + len(json_str) + 8 + len(bin_data)
    glb = bytearray()
    glb.extend(struct.pack("<I", 0x46546C67)) # MAGIC: glTF
    glb.extend(struct.pack("<I", 2))          # VERSION: 2
    glb.extend(struct.pack("<I", total_len))
    glb.extend(struct.pack("<I", len(json_str)))
    glb.extend(struct.pack("<I", 0x4E4F534A)) # JSON
    glb.extend(json_str)
    glb.extend(struct.pack("<I", len(bin_data)))
    glb.extend(struct.pack("<I", 0x004E4942)) # BIN
    glb.extend(bin_data)

    (dir_path / "animation.glb").write_bytes(glb)

# Generation Queue Manager
task_queue = []
task_lock = threading.Lock()
gallery_items = {}

def load_gallery():
    for f in OUTPUT_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            aid = data.get("id")
            if aid:
                gallery_items[aid] = data
        except Exception:
            pass

load_gallery()

def worker_loop():
    bin_path = ROOT_DIR / "build/Release/kmd-generate.exe"
    text_bundle = ROOT_DIR / "generated/llm2vec-text-bundle"
    dll_dir1 = ROOT_DIR / "build/bin/Release"
    dll_dir2 = ROOT_DIR / "build/Release"
    env = os.environ.copy()
    env["PATH"] = f"{dll_dir1};{dll_dir2};" + env.get("PATH", "")

    while True:
        item = None
        with task_lock:
            if task_queue:
                item = task_queue.pop(0)
        if not item:
            time.sleep(0.5)
            continue

        item["status"] = "running"
        json_path = OUTPUT_DIR / f"{item['id']}.json"
        json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")

        item_dir = OUTPUT_DIR / item["id"]
        item_dir.mkdir(parents=True, exist_ok=True)
        (item_dir / "prompt.txt").write_text(item["prompt"], encoding="utf-8")

        model_info = MODELS.get(item["model"])
        if not model_info or not model_info["path"].is_file():
            item["status"] = "failed"
            item["error"] = f"Model {item['model']} not found at {model_info['path'] if model_info else 'unknown'}"
            json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")
            continue

        segments = item.get("segments") or [{"prompt": item["prompt"], "frames": item["frames"]}]
        cmd = [
            str(bin_path),
            str(model_info["path"]),
            str(text_bundle),
            "--sequence",
            str(item.get("transition_frames", 10)),
            str(item.get("diffusion_steps", 20)),
            str(item.get("seed", 42)),
            str(item_dir),
        ]
        for idx, seg in enumerate(segments):
            seg_file = item_dir / f"segment-{idx+1:02d}.txt"
            seg_file.write_text(seg["prompt"], encoding="utf-8")
            cmd.extend([str(seg["frames"]), str(seg_file)])

        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if proc.returncode != 0:
                item["status"] = "failed"
                item["error"] = proc.stderr or proc.stdout or "Process returned error"
            else:
                export_skeleton_glb(item_dir, model_info["skeleton_key"])
                item["status"] = "ready"
                item["progress"] = ""
        except Exception as ex:
            item["status"] = "failed"
            item["error"] = str(ex)

        json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")

threading.Thread(target=worker_loop, daemon=True).start()

def find_blender():
    candidates = [
        Path(r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    import shutil
    p = shutil.which("blender")
    return p if p else "blender"

class KimodoHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        url = parsed.path
        if url == "/" or url == "/index.html":
            data = (DEMO_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
        elif url == "/models.js":
            data = (DEMO_DIR / "models.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
        elif url == "/localai.png":
            p = DEMO_DIR / "assets/localai.png"
            if p.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(p.read_bytes())
            else:
                self.send_error(404)
        elif url.startswith("/assets/"):
            rel_path = url[len("/assets/"):]
            p = DEMO_DIR / "assets" / rel_path
            if p.is_file():
                self.send_response(200)
                if p.suffix == ".js":
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                elif p.suffix == ".png":
                    self.send_header("Content-Type", "image/png")
                elif p.suffix == ".css":
                    self.send_header("Content-Type", "text/css; charset=utf-8")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(p.read_bytes())
                return
            self.send_error(404)
        elif url == "/api/models":
            res = []
            for m in MODELS.values():
                skel = SKELETONS.get(m["skeleton_key"], {})
                avail = m["path"].is_file()
                res.append({
                    "id": m["id"],
                    "label": m["label"],
                    "skeleton": m["skeleton"],
                    "skeleton_key": m["skeleton_key"],
                    "upstream": m["upstream"],
                    "license": m["license"],
                    "commercial": m["commercial"],
                    "available": avail,
                    "reason": "" if avail else f"GGUF not found at {m['path'].name}",
                    "parents": skel.get("parents", []),
                    "offsets": skel.get("offsets", []),
                })
            res.sort(key=lambda x: x["id"])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif url == "/api/output_files":
            res = []
            for item_dir in sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
                if item_dir.is_dir():
                    files = []
                    for f in sorted(item_dir.iterdir()):
                        # Only show clean animation files
                        if f.is_file() and not f.name.startswith("upload_") and not f.name.endswith("_animated.glb") and not f.name.endswith("_animated.fbx") and f.name != "baked_meta.json":
                            files.append({
                                "name": f.name,
                                "size": f.stat().st_size,
                                "url": f"/api/retarget/download/{item_dir.name}/{f.name}"
                            })
                    prompt = ""
                    p_file = item_dir / "prompt.txt"
                    if p_file.is_file():
                        try:
                            prompt = p_file.read_text(encoding="utf-8").strip()
                        except Exception:
                            pass
                    res.append({
                        "id": item_dir.name,
                        "prompt": prompt,
                        "path": str(item_dir),
                        "files": files
                    })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "output_dir": str(OUTPUT_DIR.resolve()),
                "items": res
            }).encode('utf-8'))
            return
        elif url == "/api/animations":
            items = list(gallery_items.values())
            items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(items).encode('utf-8'))
        elif url.startswith("/api/retarget/download/"):
            parts = url.strip("/").split("/")
            if len(parts) == 5:
                _, _, _, aid, filename = parts
                target = OUTPUT_DIR / aid / filename
                if target.is_file():
                    data = target.read_bytes()
                    self.send_response(200)
                    content_type = "model/gltf-binary" if filename.endswith(".glb") else "application/octet-stream"
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_error(404)
        elif url.startswith("/api/animations/"):
            parts = url.strip("/").split("/")
            if len(parts) == 4:
                _, _, aid, filename = parts
                item_dir = OUTPUT_DIR / aid
                target = None
                content_type = "application/octet-stream"
                if filename == "root.f32":
                    target = item_dir / "root_positions.f32"
                elif filename == "rotations.f32":
                    target = item_dir / "local_rotations_xyzw.f32"
                elif filename == "animation.glb":
                    target = item_dir / "animation.glb"
                    content_type = "model/gltf-binary"
                elif filename == "animation_mixamo.glb":
                    target = item_dir / "animation_mixamo.glb"
                    content_type = "model/gltf-binary"
                    if not target.is_file() and (item_dir / "animation.glb").is_file():
                        try:
                            from remap_to_mixamo import remap_glb
                            remap_glb(item_dir / "animation.glb", target)
                        except Exception as remap_err:
                            print(f"Mixamo remapping error: {remap_err}")

                if target and target.is_file():
                    data = target.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    if filename == "animation.glb":
                        self.send_header("Content-Disposition", f"attachment; filename=kimodo-{aid}.glb")
                    elif filename == "animation_mixamo.glb":
                        self.send_header("Content-Disposition", f"attachment; filename=kimodo-{aid}-mixamo.glb")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode('utf-8'))
            aid = secrets.token_hex(8)
            prompt = req.get("prompt", "").strip()
            segments = req.get("segments") or []
            total_frames = req.get("frames", 60)
            if segments:
                total_frames = sum(s.get("frames", 0) for s in segments)
                prompt = segments[0].get("prompt", prompt)

            item = {
                "id": aid,
                "prompt": prompt,
                "frames": total_frames,
                "diffusion_steps": req.get("steps", 20),
                "seed": req.get("seed", 42),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "queued",
                "kind": "generated",
                "model": req.get("model", "soma-rp-v1.1"),
                "segments": segments,
                "transition_frames": req.get("transition_frames", 10),
            }
            gallery_items[aid] = item
            with task_lock:
                task_queue.append(item)
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(item).encode('utf-8'))

        elif path == "/api/retarget":
            length = int(self.headers.get("Content-Length", 0))
            content_type = self.headers.get("Content-Type", "")
            aid = query.get("animation_id", [""])[0]
            out_format = query.get("format", ["glb"])[0].lower()
            filename = query.get("filename", ["character.fbx"])[0]

            try:
                if "application/json" in content_type:
                    body = self.rfile.read(length)
                    req = json.loads(body.decode('utf-8'))
                    aid = req.get("animation_id", aid)
                    filename = req.get("filename", filename)
                    out_format = req.get("format", out_format)
                    file_bytes = base64.b64decode(req.get("file_data", ""))
                else:
                    # Direct binary stream upload
                    item_dir = OUTPUT_DIR / aid
                    item_dir.mkdir(parents=True, exist_ok=True)
                    char_ext = Path(filename).suffix or ".fbx"
                    char_path = item_dir / f"upload_character{char_ext}"
                    with open(char_path, "wb") as f:
                        remaining = length
                        while remaining > 0:
                            chunk = self.rfile.read(min(65536, remaining))
                            if not chunk:
                                break
                            f.write(chunk)
                            remaining -= len(chunk)
                    file_bytes = None

                item_dir = OUTPUT_DIR / aid
                if not item_dir.is_dir():
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Animation directory {aid} not found"}).encode('utf-8'))
                    return

                char_ext = Path(filename).suffix or ".fbx"
                char_path = item_dir / f"upload_character{char_ext}"
                if file_bytes is not None:
                    char_path.write_bytes(file_bytes)

                clean_stem = Path(filename).stem
                out_filename = f"{clean_stem}_animated.{out_format}"
                out_path = item_dir / out_filename

                blender_exe = find_blender()
                bake_script = ROOT_DIR / "scripts/bake_to_character.py"

                print(f"[Retarget] Running Blender: {blender_exe}")
                print(f"[Retarget] Character: {char_path} ({char_path.stat().st_size} bytes)")
                print(f"[Retarget] Output:    {out_path}")

                cmd = [
                    str(blender_exe),
                    "-b",
                    "-P",
                    str(bake_script),
                    "--",
                    "--character",
                    str(char_path),
                    "--motion",
                    str(item_dir),
                    "--output",
                    str(out_path),
                ]

                proc = subprocess.run(cmd, capture_output=True, text=True)
                print(f"[Retarget] Blender returncode: {proc.returncode}")
                if proc.returncode != 0 or not out_path.is_file():
                    err_msg = proc.stderr or proc.stdout or "Blender baking failed"
                    print(f"[Retarget] Error: {err_msg}")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": err_msg[-500:]}).encode('utf-8'))
                    return

                # Check for web preview GLB
                preview_filename = f"{clean_stem}_animated.glb"
                preview_path = item_dir / preview_filename
                preview_url = f"/api/retarget/download/{aid}/{preview_filename}" if preview_path.is_file() else f"/api/retarget/download/{aid}/{out_filename}"

                print(f"[Retarget] Success! Saved to {out_path}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "filename": out_filename,
                    "download_url": f"/api/retarget/download/{aid}/{out_filename}",
                    "preview_url": preview_url,
                    "character_name": clean_stem
                }).encode('utf-8'))

            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(ex)}).encode('utf-8'))

        elif path == "/api/open_folder":
            try:
                folder_path = OUTPUT_DIR.resolve()
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"[Explorer] Opening output directory: {folder_path}")
                if sys.platform == "win32":
                    subprocess.Popen(f'explorer "{folder_path}"', shell=True)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(folder_path)])
                else:
                    subprocess.Popen(["xdg-open", str(folder_path)])
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "opened", "path": str(folder_path)}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path.startswith("/api/animations/") and path.endswith("/delete"):
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                aid = parts[2]
                item_dir = OUTPUT_DIR / aid
                if item_dir.exists():
                    shutil.rmtree(item_dir, ignore_errors=True)
                json_meta = OUTPUT_DIR / f"{aid}.json"
                if json_meta.is_file():
                    try:
                        json_meta.unlink()
                    except Exception:
                        pass
                gallery_items.pop(aid, None)
                print(f"[Delete] Animation {aid} removed.")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "deleted", "id": aid}).encode('utf-8'))
                return
            self.send_error(404)
        else:
            self.send_error(404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/animations/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                aid = parts[2]
                item_dir = OUTPUT_DIR / aid
                if item_dir.exists():
                    shutil.rmtree(item_dir, ignore_errors=True)
                json_meta = OUTPUT_DIR / f"{aid}.json"
                if json_meta.is_file():
                    try:
                        json_meta.unlink()
                    except Exception:
                        pass
                gallery_items.pop(aid, None)
                print(f"[Delete] Animation {aid} removed.")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "deleted", "id": aid}).encode('utf-8'))
                return
        self.send_error(404)

if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), KimodoHandler)
    print(f"\n=======================================================")
    print(f"  Kimodo.cpp Web GUI is running!")
    print(f"  Open your browser: http://localhost:{PORT}")
    print(f"=======================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
