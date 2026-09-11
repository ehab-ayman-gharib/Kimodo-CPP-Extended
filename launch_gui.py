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
import re
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

def find_kmd_generate():
    candidates = [
        ROOT_DIR / "build" / "Release" / "kmd-generate.exe",
        ROOT_DIR / "build" / "Release" / "kmd-generate",
        ROOT_DIR / "build" / "kmd-generate",
        ROOT_DIR / "build" / "bin" / "kmd-generate",
        ROOT_DIR / "build" / "bin" / "Release" / "kmd-generate.exe",
        ROOT_DIR / "build" / "bin" / "Release" / "kmd-generate",
        ROOT_DIR / "bin" / "kmd-generate.exe",
        ROOT_DIR / "bin" / "kmd-generate",
    ]
    for c in candidates:
        if c.is_file():
            return c
    import shutil
    p = shutil.which("kmd-generate")
    return Path(p) if p else (ROOT_DIR / "build/Release/kmd-generate.exe")

def get_runtime_env():
    dll_dirs = [
        ROOT_DIR / "bin" / "skintokens",
        ROOT_DIR / "bin",
        ROOT_DIR / "build" / "bin" / "Release",
        ROOT_DIR / "build" / "Release",
        ROOT_DIR / "build" / "bin",
        ROOT_DIR / "build",
    ]
    env = os.environ.copy()
    lib_path_entries = [str(d) for d in dll_dirs if d.is_dir()]
    if sys.platform == "win32":
        env["PATH"] = os.pathsep.join(lib_path_entries + [env.get("PATH", "")])
    elif sys.platform == "darwin":
        env["DYLD_LIBRARY_PATH"] = os.pathsep.join(lib_path_entries + [env.get("DYLD_LIBRARY_PATH", "")])
        env["PATH"] = os.pathsep.join(lib_path_entries + [env.get("PATH", "")])
    else:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_path_entries + [env.get("LD_LIBRARY_PATH", "")])
        env["PATH"] = os.pathsep.join(lib_path_entries + [env.get("PATH", "")])
    return env

_download_state = {
    "status": "idle",  # "idle", "downloading", "complete", "error"
    "current_step": "",
    "percent": 0,
    "error": None
}
_download_lock = threading.Lock()

def _get_download_state():
    with _download_lock:
        return dict(_download_state)

def _update_download_state(**kwargs):
    with _download_lock:
        _download_state.update(kwargs)

def check_models_status():
    motion_file = ROOT_DIR / "models/kimodo-soma-rp-v1.1-f32.gguf"
    motion_ready = motion_file.is_file() and motion_file.stat().st_size > 500_000_000

    text_bundle_dir = ROOT_DIR / "generated/llm2vec-text-bundle"
    text_embed = text_bundle_dir / "embedding.gguf"
    text_ready = text_embed.is_file() and text_embed.stat().st_size > 500_000_000

    skintokens_dir = ROOT_DIR / "models/skintokens"
    st_files = ["mesh-encoder.gguf", "skin-vae.gguf", "tokenrig.gguf"]
    st_ready = all((skintokens_dir / f).is_file() and (skintokens_dir / f).stat().st_size > 10_000_000 for f in st_files)

    missing = []
    if not motion_ready:
        missing.append("SOMA v1.1 Motion Model (~1.08 GB)")
    if not text_ready:
        missing.append("Llama-3 Text Bundle (~14.1 GB)")
    if not st_ready:
        missing.append("SkinTokens Neural Rig (~1.19 GB)")

    return {
        "all_ready": motion_ready and text_ready and st_ready,
        "motion": {"ready": motion_ready, "path": str(motion_file)},
        "text_bundle": {"ready": text_ready, "dir": str(text_bundle_dir)},
        "skintokens": {"ready": st_ready, "dir": str(skintokens_dir)},
        "missing": missing,
        "download_state": _get_download_state()
    }

def start_download_task():
    with _download_lock:
        if _download_state["status"] == "downloading":
            return False, "Download already in progress"
        _download_state["status"] = "downloading"
        _download_state["error"] = None
        _download_state["percent"] = 5
        _download_state["current_step"] = "Initializing download..."

    def _worker():
        try:
            from huggingface_hub import snapshot_download
            status = check_models_status()
            to_download = []
            if not status["motion"]["ready"]:
                to_download.append("motion")
            if not status["skintokens"]["ready"]:
                to_download.append("skintokens")
            if not status["text_bundle"]["ready"]:
                to_download.append("text")

            total_items = max(1, len(to_download))
            completed = 0

            # 1. Download SOMA v1.1 motion model
            if "motion" in to_download:
                _update_download_state(
                    current_step="Downloading SOMA v1.1 Motion Model (~1.08 GB)...",
                    percent=int((completed / total_items) * 90) + 5
                )
                print("[Downloader] Downloading SOMA v1.1 Motion Model from LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML...")
                (ROOT_DIR / "models").mkdir(parents=True, exist_ok=True)
                snapshot_download(
                    repo_id="LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML",
                    local_dir=str(ROOT_DIR),
                    allow_patterns=["models/kimodo-soma-rp-v1.1-f32.gguf", "MANIFEST.json"]
                )
                completed += 1
                _update_download_state(percent=int((completed / total_items) * 90) + 5)

            # 2. Download SkinTokens neural rig weights
            if "skintokens" in to_download:
                _update_download_state(
                    current_step="Downloading SkinTokens Neural Auto-Rig Weights (~1.19 GB)...",
                    percent=int((completed / total_items) * 90) + 5
                )
                print("[Downloader] Downloading SkinTokens weights from LocalAI-io/SkinTokens-GGUF...")
                target_dir = ROOT_DIR / "models" / "skintokens"
                target_dir.mkdir(parents=True, exist_ok=True)
                temp_dir = ROOT_DIR / "models" / "_skintokens_tmp"
                snapshot_download(
                    repo_id="LocalAI-io/SkinTokens-GGUF",
                    local_dir=str(temp_dir),
                    allow_patterns=["F16/*", "MANIFEST.json"]
                )
                src_dir = temp_dir / "F16"
                for fname in ["mesh-encoder.gguf", "skin-vae.gguf", "tokenrig.gguf"]:
                    src = src_dir / fname
                    dst = target_dir / fname
                    if src.is_file():
                        shutil.copy2(str(src), str(dst))
                shutil.rmtree(temp_dir, ignore_errors=True)
                completed += 1
                _update_download_state(percent=int((completed / total_items) * 90) + 5)

            # 3. Download Text Bundle
            if "text" in to_download:
                _update_download_state(
                    current_step="Downloading Llama-3 Text Bundle (~14.1 GB)...",
                    percent=int((completed / total_items) * 90) + 5
                )
                print("[Downloader] Downloading Llama-3 Text Bundle from LocalAI-io/Llama-3-Kimodo-GGML...")
                (ROOT_DIR / "generated").mkdir(parents=True, exist_ok=True)
                snapshot_download(
                    repo_id="LocalAI-io/Llama-3-Kimodo-GGML",
                    local_dir=str(ROOT_DIR),
                    allow_patterns=["generated/llm2vec-text-bundle/*", "MANIFEST.json"]
                )
                completed += 1

            _update_download_state(
                status="complete",
                percent=100,
                current_step="All essential models downloaded and ready!"
            )
            print("[Downloader] All requested weights installed successfully.")

        except Exception as ex:
            print(f"[Downloader] Failed to download weights: {ex}")
            _update_download_state(
                status="error",
                error=str(ex),
                current_step=f"Download error: {str(ex)[:120]}"
            )

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True, "Download started"

def worker_loop():
    bin_path = find_kmd_generate()
    text_bundle = ROOT_DIR / "generated/llm2vec-text-bundle"
    env = get_runtime_env()

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

        t_start = time.time()
        print(f"\n[Worker] Starting job: {item['id']} ({item['prompt'][:40]}...)")
        print(f"[Worker] Frames: {item['frames']}, Steps: {item['diffusion_steps']}, Seed: {item['seed']}")
        print(f"[Worker] Binary: {bin_path}")

        # Check if binary exists
        if not bin_path.is_file():
            print(f"[Worker] Error: Generator binary not found at {bin_path}")
            item["status"] = "failed"
            item["error"] = f"Generator binary not found at {bin_path}. Please build kimodo first (e.g. cmake --build build)."
            json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")
            continue

        model_key = item.get("model", "soma-rp-v1.1")
        model_info = MODELS.get(model_key, MODELS["soma-rp-v1.1"])
        model_path = model_info["path"]

        # Check if model or text bundle is missing - auto-download on first use!
        if not model_path.is_file() or not (text_bundle / "embedding.gguf").is_file():
            print("[Worker] Weights missing for generation. Initiating automatic background download...")
            item["status"] = "running"
            item["progress"] = "Downloading missing motion/text models from HuggingFace (first-time setup)..."
            json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")

            start_download_task()
            while True:
                dst = _get_download_state()
                if dst["status"] == "complete":
                    print("[Worker] Background download complete. Resuming generation.")
                    break
                elif dst["status"] == "error":
                    item["status"] = "failed"
                    item["error"] = f"Automatic download failed: {dst.get('error')}"
                    json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")
                    break
                time.sleep(1.0)

            if item["status"] == "failed":
                continue

        prompt_file = item_dir / "prompt.txt"
        prompt_file.write_text(item["prompt"], encoding="utf-8")

        # Run kmd-generate
        if item.get("segments"):
            cmd = [
                str(bin_path),
                str(model_path),
                str(text_bundle),
                "--sequence",
                str(item.get("transition_frames", 10)),
                str(item["diffusion_steps"]),
                str(item["seed"]),
                str(item_dir)
            ]
            for idx, seg in enumerate(item["segments"]):
                seg_prompt_file = item_dir / f"prompt_seg_{idx}.txt"
                seg_prompt_file.write_text(seg.get("prompt", ""), encoding="utf-8")
                cmd.extend([str(seg.get("frames", 30)), str(seg_prompt_file)])
        else:
            cmd = [
                str(bin_path),
                str(model_path),
                str(text_bundle),
                str(prompt_file),
                str(item["frames"]),
                str(item["diffusion_steps"]),
                str(item["seed"]),
                str(item_dir)
            ]
            seg_json = item_dir / "segments.json"
            seg_data = {
                "segments": item["segments"],
                "transition_frames": item.get("transition_frames", 10)
            }
            seg_json.write_text(json.dumps(seg_data, indent=2), encoding="utf-8")
            cmd.extend(["--segments", str(seg_json)])

        try:
            res = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[Worker] Process failed with return code {res.returncode}")
                print(f"[Worker] Stderr: {res.stderr}")
                item["status"] = "failed"
                item["error"] = res.stderr or "Generation failed"
            else:
                print(f"[Worker] Process completed successfully in {time.time() - t_start:.2f}s")
                export_skeleton_glb(item_dir, model_info["skeleton_key"])
                item["status"] = "ready"
                item["progress"] = ""
                item["duration"] = round(time.time() - t_start, 2)
                item["files"] = {
                    "root": f"/api/animations/{item['id']}/root.f32",
                    "rotations": f"/api/animations/{item['id']}/rotations.f32",
                    "glb": f"/api/animations/{item['id']}/animation.glb",
                    "glb_mixamo": f"/api/animations/{item['id']}/animation_mixamo.glb"
                }
        except Exception as e:
            print(f"[Worker] Exception running generator: {e}")
            item["status"] = "failed"
            item["error"] = str(e)

        json_path.write_text(json.dumps(item, indent=2), encoding="utf-8")

threading.Thread(target=worker_loop, daemon=True).start()

CONFIG_PATH = ROOT_DIR / "config.json"

def get_config():
    if CONFIG_PATH.is_file():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def set_config_value(key, val):
    cfg = get_config()
    if val is None:
        cfg.pop(key, None)
    else:
        cfg[key] = val
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Config] Error saving config: {e}")

def validate_blender(path_str):
    if not path_str or not isinstance(path_str, str):
        return False, None, "No path provided"
    p = Path(path_str.strip().strip('"').strip("'"))
    # Handle macOS .app bundle path
    if sys.platform == "darwin" and p.suffix == ".app":
        app_binary = p / "Contents/MacOS/Blender"
        if app_binary.is_file():
            p = app_binary
    if not p.is_file():
        # Check if it resolves via system PATH
        p_which = shutil.which(str(p))
        if p_which:
            p = Path(p_which)
        else:
            return False, None, f"File not found: {path_str}"
    try:
        res = subprocess.run([str(p), "--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and "Blender" in res.stdout:
            ver_line = res.stdout.splitlines()[0].strip()
            return True, str(p.resolve()), ver_line
        return False, None, f"Executed successfully but unexpected output: {res.stdout[:80]}"
    except Exception as e:
        return False, None, str(e)

def find_blender_info():
    # 1. Check manually saved config
    saved_path = get_config().get("blender_path")
    if saved_path:
        ok, res_path, ver = validate_blender(saved_path)
        if ok:
            return {
                "found": True,
                "path": res_path,
                "version": ver,
                "is_manual": True
            }

    # 2. Auto-detect from system locations
    candidates = [
        Path(r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"),
        Path("/Applications/Blender.app/Contents/MacOS/Blender"),
        Path("/usr/bin/blender"),
        Path("/usr/local/bin/blender"),
        Path("/snap/bin/blender"),
    ]
    p_which = shutil.which("blender")
    if p_which:
        candidates.append(Path(p_which))

    for c in candidates:
        if c.is_file():
            ok, res_path, ver = validate_blender(str(c))
            if ok:
                return {
                    "found": True,
                    "path": res_path,
                    "version": ver,
                    "is_manual": False
                }

    return {
        "found": False,
        "path": None,
        "version": None,
        "is_manual": False
    }

def find_blender():
    info = find_blender_info()
    return info["path"]

def native_browse_blender():
    # Try Tkinter dialog first (standard in Windows/macOS Python)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if sys.platform == "win32":
            filetypes = [("Blender (blender.exe)", "blender.exe"), ("Executables (*.exe)", "*.exe"), ("All Files (*.*)", "*.*")]
        elif sys.platform == "darwin":
            filetypes = [("Blender App (*.app)", "*.app"), ("All Files (*)", "*")]
        else:
            filetypes = [("All Files (*)", "*")]
        chosen = filedialog.askopenfilename(title="Select Blender Executable", filetypes=filetypes)
        root.destroy()
        if chosen:
            return str(Path(chosen).resolve())
    except Exception as e:
        print(f"[Browse] Tkinter file dialog unavailable: {e}")

    # Fallback on Windows: PowerShell OpenFileDialog
    if sys.platform == "win32":
        try:
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d = New-Object System.Windows.Forms.OpenFileDialog; "
                "$d.Filter = 'Blender (blender.exe)|blender.exe|Executables (*.exe)|*.exe|All Files (*.*)|*.*'; "
                "$d.Title = 'Select Blender Executable'; "
                "if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){ Write-Output $d.FileName }"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps_script], capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and res.stdout.strip():
                return str(Path(res.stdout.strip()).resolve())
        except Exception as ex:
            print(f"[Browse] PowerShell dialog fallback error: {ex}")

    # Fallback on macOS: osascript
    if sys.platform == "darwin":
        try:
            as_code = 'POSIX path of (choose file of type {"app", ""} with prompt "Select Blender application")'
            res = subprocess.run(["osascript", "-e", as_code], capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and res.stdout.strip():
                return str(Path(res.stdout.strip()).resolve())
        except Exception:
            pass

    # Fallback on Linux: zenity
    if shutil.which("zenity"):
        try:
            res = subprocess.run(["zenity", "--file-selection", "--title=Select Blender executable"], capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and res.stdout.strip():
                return str(Path(res.stdout.strip()).resolve())
        except Exception:
            pass

    return None

def find_skintokens():
    candidates = [
        ROOT_DIR / "bin" / "skintokens" / "skintokens-cli.exe",
        ROOT_DIR / "bin" / "skintokens" / "skintokens-cli",
        ROOT_DIR / "build" / "bin" / "skintokens-cli",
        ROOT_DIR / "build" / "skintokens-cli",
    ]
    import shutil
    p = shutil.which("skintokens-cli")
    if p:
        candidates.append(Path(p))
    exe = next((c for c in candidates if c.is_file()), None)
    models = ROOT_DIR / "models" / "skintokens"
    script = ROOT_DIR / "scripts" / "convert_to_mixamo.py"
    return (
        exe,
        models if models.is_dir() else None,
        script if script.is_file() else None
    )

_cached_vulkan_env = None

def get_vulkan_env():
    global _cached_vulkan_env
    if _cached_vulkan_env is not None:
        return _cached_vulkan_env.copy()

    env = get_runtime_env()
    try:
        skintokens_exe, skintokens_models, _ = find_skintokens()
        if skintokens_exe and skintokens_models:
            proc = subprocess.run(
                [str(skintokens_exe), "inspect", str(skintokens_models), "--device", "vulkan"],
                capture_output=True,
                text=True,
                timeout=6
            )
            devices = []
            for line in proc.stderr.splitlines():
                m = re.match(r"ggml_vulkan:\s+(\d+)\s+=\s+(.*?)\s+\((.*?)\)", line)
                if m:
                    devices.append((int(m.group(1)), m.group(2), m.group(3)))
            best_idx = 0
            for idx, name, vendor in devices:
                nl = name.lower()
                vl = vendor.lower()
                if any(k in nl or k in vl for k in ["nvidia", "geforce", "rtx", "amd", "radeon", "discrete", "apple", "m1", "m2", "m3", "m4"]):
                    best_idx = idx
                    print(f"[Vulkan] Auto-selected GPU [{best_idx}]: {name} ({vendor})")
                    break
            env["GGML_VK_VISIBLE_DEVICES"] = str(best_idx)
            _cached_vulkan_env = env
            return env.copy()
    except Exception as e:
        print(f"[Vulkan] Device discovery warning: {e}")
    env["GGML_VK_VISIBLE_DEVICES"] = "1"
    _cached_vulkan_env = env
    return env.copy()

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
        elif url.startswith("/api/preview_model/download/"):
            parts = url.strip("/").split("/")
            if len(parts) == 5:
                _, _, _, pid, raw_filename = parts
                filename = urllib.parse.unquote(raw_filename)
                target = OUTPUT_DIR / "_preview" / pid / filename
                if not target.is_file():
                    target = OUTPUT_DIR / "_preview" / pid / raw_filename
                if target.is_file():
                    data = target.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "model/gltf-binary")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self.send_error(404)
        elif url.startswith("/api/retarget/download/"):
            parts = url.strip("/").split("/")
            if len(parts) == 5:
                _, _, _, aid, raw_filename = parts
                filename = urllib.parse.unquote(raw_filename)
                target = OUTPUT_DIR / aid / filename
                if not target.is_file():
                    target = OUTPUT_DIR / aid / raw_filename
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
        elif url == "/api/blender":
            info = find_blender_info()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(info).encode('utf-8'))
            return
        elif url == "/api/models/status":
            info = check_models_status()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(info).encode('utf-8'))
            return
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        content_type = self.headers.get("Content-Type", "")

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
            aid = query.get("animation_id", [""])[0]
            out_format = query.get("format", ["glb"])[0].lower()
            raw_filename = query.get("filename", ["character.fbx"])[0]
            filename = urllib.parse.unquote(raw_filename)
            preview_id = query.get("preview_id", [""])[0]
            arm_clearance = float(query.get("arm_clearance", [0.0])[0]) if "arm_clearance" in query else 0.0
            forearm_clearance = float(query.get("forearm_clearance", [0.0])[0]) if "forearm_clearance" in query else 0.0
            grounding_offset = float(query.get("grounding_offset", [0.0])[0]) if "grounding_offset" in query else 0.0

            try:
                if "application/json" in content_type:
                    body = self.rfile.read(length)
                    req = json.loads(body.decode('utf-8'))
                    aid = req.get("animation_id", aid)
                    filename = urllib.parse.unquote(req.get("filename", filename))
                    preview_id = req.get("preview_id", preview_id)
                    out_format = req.get("format", out_format)
                    file_bytes = base64.b64decode(req.get("file_data", "")) if req.get("file_data") else None
                    if "arm_clearance" in req:
                        try:
                            arm_clearance = float(req.get("arm_clearance", 0.0))
                        except Exception:
                            arm_clearance = 0.0
                    if "forearm_clearance" in req:
                        try:
                            forearm_clearance = float(req.get("forearm_clearance", 0.0))
                        except Exception:
                            forearm_clearance = 0.0
                    if "grounding_offset" in req:
                        try:
                            grounding_offset = float(req.get("grounding_offset", 0.0))
                        except Exception:
                            grounding_offset = 0.0
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

                # If preview_id is provided, check if an auto-rigged Mixamo GLB is available in that preview folder
                if preview_id and (OUTPUT_DIR / "_preview" / preview_id).is_dir():
                    prev_dir = OUTPUT_DIR / "_preview" / preview_id
                    rigged_candidates = list(prev_dir.glob("*_mixamo.glb"))
                    if not rigged_candidates and (prev_dir / "preview.glb").is_file():
                        rigged_candidates = [prev_dir / "preview.glb"]
                    if rigged_candidates:
                        rigged_src = rigged_candidates[0]
                        char_path = item_dir / f"upload_character{rigged_src.suffix}"
                        shutil.copyfile(rigged_src, char_path)
                        print(f"[Retarget] Using auto-rigged model from preview {preview_id}: {rigged_src.name}")

                char_ext = Path(filename).suffix or ".fbx"
                char_path = item_dir / f"upload_character{char_ext}"
                if file_bytes is not None:
                    char_path.write_bytes(file_bytes)
                elif not char_path.is_file():
                    existing_chars = list(item_dir.glob("upload_character.*"))
                    if existing_chars:
                        char_path = existing_chars[0]

                clean_stem = Path(filename).stem.replace(" ", "_")
                out_filename = f"{clean_stem}_animated.{out_format}"
                out_path = item_dir / out_filename

                blender_exe = find_blender()
                if not blender_exe or not Path(blender_exe).is_file():
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Blender executable not found. Please click 'Locate Blender' in the UI to configure your Blender path."}).encode('utf-8'))
                    return
                bake_script = ROOT_DIR / "scripts/bake_to_character.py"

                print(f"[Retarget] Running Blender: {blender_exe}")
                print(f"[Retarget] Character: {char_path} ({char_path.stat().st_size if char_path.is_file() else 'missing'} bytes)")
                print(f"[Retarget] Output:    {out_path}")
                print(f"[Retarget] Arm Clearance:     {arm_clearance:+.1f}°")
                print(f"[Retarget] Forearm Clearance: {forearm_clearance:+.1f}°")
                print(f"[Retarget] Grounding Offset:  {grounding_offset:+.1f}cm")

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
                if abs(arm_clearance) > 0.001:
                    cmd.extend(["--arm-clearance", str(arm_clearance)])
                if abs(forearm_clearance) > 0.001:
                    cmd.extend(["--forearm-clearance", str(forearm_clearance)])
                if abs(grounding_offset) > 0.001:
                    cmd.extend(["--grounding-offset", str(grounding_offset / 100.0)])

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

        elif path == "/api/preview_model":
            length = int(self.headers.get("Content-Length", 0))
            raw_filename = query.get("filename", ["character.fbx"])[0]
            filename = urllib.parse.unquote(raw_filename)
            pid = secrets.token_hex(6)
            prev_dir = OUTPUT_DIR / "_preview" / pid
            prev_dir.mkdir(parents=True, exist_ok=True)
            
            char_ext = Path(filename).suffix or ".fbx"
            char_path = prev_dir / f"input_char{char_ext}"
            with open(char_path, "wb") as f:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            # Check if matching file exists in workspace to accurately resolve sibling .fbm texture folders
            ws_file = ROOT_DIR / filename
            actual_input = ws_file if ws_file.is_file() else char_path
            
            out_glb = prev_dir / "preview.glb"
            blender_exe = find_blender()
            script_path = ROOT_DIR / "scripts/convert_to_preview_glb.py"

            cmd = [
                str(blender_exe),
                "-b",
                "-P",
                str(script_path),
                "--",
                str(actual_input),
                str(out_glb),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode == 0 and out_glb.is_file():
                meta_file = prev_dir / "preview_meta.json"
                is_rigged = True
                bone_count = 0
                if meta_file.is_file():
                    try:
                        meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                        is_rigged = bool(meta_data.get("is_rigged", True))
                        bone_count = int(meta_data.get("bone_count", 0))
                    except Exception:
                        pass

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "preview_url": f"/api/preview_model/download/{pid}/preview.glb",
                    "preview_id": pid,
                    "filename": filename,
                    "is_rigged": is_rigged,
                    "bone_count": bone_count
                }).encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": proc.stderr or proc.stdout or "Preview conversion failed"}).encode('utf-8'))

        elif path == "/api/auto_rig":
            length = int(self.headers.get("Content-Length", 0))
            raw_filename = query.get("filename", ["character.glb"])[0]
            filename = urllib.parse.unquote(raw_filename)
            preview_id = query.get("preview_id", [""])[0]
            device = query.get("device", ["vulkan"])[0].lower()
            if device not in ["vulkan", "cpu"]:
                device = "vulkan"

            file_bytes = None
            if "application/json" in content_type:
                body = self.rfile.read(length)
                req = json.loads(body.decode('utf-8'))
                filename = urllib.parse.unquote(req.get("filename", filename))
                preview_id = req.get("preview_id", preview_id)
                device = req.get("device", device)
                if req.get("file_data"):
                    file_bytes = base64.b64decode(req["file_data"])
            elif length > 0 and not preview_id:
                file_bytes = self.rfile.read(length)

            if device not in ["vulkan", "cpu"]:
                device = "vulkan"

            skintokens_exe, skintokens_models, convert_mixamo_script = find_skintokens()
            if not skintokens_exe or not skintokens_models or not convert_mixamo_script:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "SkinTokens binaries, models, or conversion script not found in Kimodo-CPP."}).encode('utf-8'))
                return

            blender_exe = find_blender()
            if not blender_exe or not Path(blender_exe).is_file():
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Blender executable not found. Please click 'Locate Blender' in the UI to configure your Blender path."}).encode('utf-8'))
                return

            if preview_id and (OUTPUT_DIR / "_preview" / preview_id).is_dir():
                work_dir = OUTPUT_DIR / "_preview" / preview_id
                work_id = preview_id
            else:
                work_id = secrets.token_hex(6)
                work_dir = OUTPUT_DIR / "_preview" / work_id
                work_dir.mkdir(parents=True, exist_ok=True)

            char_ext = Path(filename).suffix.lower() or ".glb"
            raw_input_path = work_dir / f"input_char{char_ext}"
            if file_bytes is not None:
                raw_input_path.write_bytes(file_bytes)

            input_glb = work_dir / "preview.glb"
            if not input_glb.is_file():
                if char_ext in [".glb", ".gltf"] and raw_input_path.is_file():
                    input_glb = raw_input_path
                elif raw_input_path.is_file():
                    script_preview = ROOT_DIR / "scripts/convert_to_preview_glb.py"
                    conv_cmd = [str(blender_exe), "-b", "-P", str(script_preview), "--", str(raw_input_path), str(input_glb)]
                    subprocess.run(conv_cmd, capture_output=True, text=True)

            if not input_glb.is_file():
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Could not prepare input mesh GLB from {filename}."}).encode('utf-8'))
                return

            beams = 5
            if "beams" in query:
                try:
                    b_val = int(query["beams"][0])
                    if 1 <= b_val <= 20:
                        beams = b_val
                except ValueError:
                    beams = 5

            print(f"[Auto-Rig] Starting SkinTokens neural rig on {input_glb.name} (device: {device}, beams: {beams})...")
            tokens_rigged_glb = work_dir / "tokens_rigged.glb"

            rig_cmd = [
                str(skintokens_exe),
                "rig",
                str(skintokens_models),
                str(input_glb),
                str(tokens_rigged_glb),
                "--device", device,
                "--beams", str(beams)
            ]
            t_start = time.time()
            vk_env = get_vulkan_env() if device == "vulkan" else get_runtime_env()
            rig_proc = subprocess.run(rig_cmd, env=vk_env, capture_output=True, text=True)
            t_elapsed = round(time.time() - t_start, 1)
            print(f"[Auto-Rig] skintokens rig finished in {t_elapsed}s (returncode: {rig_proc.returncode})")

            if rig_proc.returncode != 0 or not tokens_rigged_glb.is_file() or tokens_rigged_glb.stat().st_size < 1000:
                err = rig_proc.stderr or rig_proc.stdout or "SkinTokens rig failed to generate skeleton."
                print(f"[Auto-Rig] Error: {err}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": err[-500:]}).encode('utf-8'))
                return

            # Convert to Mixamo bone naming & synchronize vertex groups
            clean_stem = Path(filename).stem.replace(" ", "_")
            mixamo_rigged_glb = work_dir / f"{clean_stem}_mixamo.glb"
            mixamo_cmd = [
                str(blender_exe),
                "-b",
                "-P",
                str(convert_mixamo_script),
                "--",
                str(tokens_rigged_glb),
                str(mixamo_rigged_glb),
                "Mixamo",
                "mixamorig:"
            ]
            mixamo_proc = subprocess.run(mixamo_cmd, capture_output=True, text=True)
            print(f"[Auto-Rig] Mixamo conversion finished in Blender (returncode: {mixamo_proc.returncode})")

            if mixamo_proc.returncode != 0 or not mixamo_rigged_glb.is_file():
                err = mixamo_proc.stderr or mixamo_proc.stdout or "Mixamo bone conversion failed."
                print(f"[Auto-Rig] Error: {err}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": err[-500:]}).encode('utf-8'))
                return

            try:
                shutil.copyfile(mixamo_rigged_glb, work_dir / "preview.glb")
                (work_dir / "preview_meta.json").write_text(json.dumps({
                    "is_rigged": True,
                    "bone_count": 22,
                    "has_mesh": True,
                    "rig_type": "mixamo"
                }), encoding="utf-8")
            except Exception as e:
                print(f"[Auto-Rig] Note on copying preview: {e}")

            download_url = f"/api/preview_model/download/{work_id}/{clean_stem}_mixamo.glb"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "character_name": f"{clean_stem} (Mixamo)",
                "filename": f"{clean_stem}_mixamo.glb",
                "preview_url": download_url,
                "download_url": download_url,
                "preview_id": work_id,
                "is_rigged": True,
                "bone_count": 22,
                "beams": beams,
                "elapsed_seconds": t_elapsed
            }).encode('utf-8'))

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

        elif path == "/api/blender":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode('utf-8'))
            new_path = req.get("path", "").strip()
            ok, res_path, ver = validate_blender(new_path)
            if ok:
                set_config_value("blender_path", res_path)
                print(f"[Blender] User configured manual Blender path: {res_path} ({ver})")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "found": True,
                    "path": res_path,
                    "version": ver,
                    "is_manual": True
                }).encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Invalid Blender path: {ver}"
                }).encode('utf-8'))

        elif path == "/api/blender/browse":
            print("[Blender] Opening native system file dialog to locate Blender...")
            chosen = native_browse_blender()
            if not chosen:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"cancelled": True}).encode('utf-8'))
                return
            ok, res_path, ver = validate_blender(chosen)
            if ok:
                set_config_value("blender_path", res_path)
                print(f"[Blender] User selected Blender via browse dialog: {res_path} ({ver})")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "found": True,
                    "path": res_path,
                    "version": ver,
                    "is_manual": True
                }).encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Selected file is not a valid Blender executable: {ver}"
                }).encode('utf-8'))

        elif path == "/api/blender/reset":
            set_config_value("blender_path", None)
            info = find_blender_info()
            print(f"[Blender] Reset to auto-detection: {info}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(info).encode('utf-8'))

        elif path == "/api/models/download":
            ok, msg = start_download_task()
            status = check_models_status()
            self.send_response(200 if ok else 409)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": ok,
                "message": msg,
                "download_state": status["download_state"]
            }).encode('utf-8'))

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
