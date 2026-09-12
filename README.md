# Kimodo-CPP Extended

**Universal AI Motion Retargeting, Neural Auto-Rigging & Local 3D Character Studio**

Kimodo-CPP Extended builds upon [`kimodo.cpp`](https://github.com/localai-org/kimodo.cpp) and [`skin-tokens.cpp`](https://github.com/localai-org/skin-tokens.cpp) to bridge the gap between raw neural motion generation and production-ready 3D game pipelines. It provides 100% offline, private text-to-motion synthesis, GPU-accelerated neural auto-rigging for static meshes, and a universal character baking engine that retargets AI motion directly onto custom 3D characters while strictly preserving authentic skeleton hierarchies.

---

## What's New in Kimodo-CPP Extended

### 1. Universal Multi-Rig Character Baker (Preserves Native Skeletons)
Bake AI motion directly onto custom character meshes (`.fbx`, `.glb`, `.gltf`) using background Blender automation without altering original bone hierarchies:
- **Unreal Engine Mannequin (`SK_Mannequin` / UE4 & UE5)**: 100% native preservation (`pelvis`, `spine_01-03`, `clavicle_l`, `upperarm_l`, `thigh_l`, `calf_l`). Assets drop directly into Unreal animation blueprints with zero retargeting setup.
- **Reallusion Character Creator (CC3 & CC4)**: Native preservation of `CC_Base_Hip`, `CC_Base_Waist`, and `CC_Base_Spine01-02` with upper thoracic forward flex to eliminate arm/torso penetration.
- **Mixamo & Standard Humanoid**: In-place retargeting for T-Pose and A-Pose meshes with virtual angular compensation (`Q_lift`) and name-prefix agnosticism (`Hero_`, `Character_`).
- **Autodesk 3ds Max Character Studio Biped**: Automatic centimeter-to-meter normalization and IBM de-skewing with zero ground-shift on classic bipeds (`Bip001`, `Bip<Name>`).

### 2. Neural Auto-Rigging with SkinTokens AI
Turn unrigged, static humanoid meshes (`.glb`, `.fbx`, `.obj`) into fully rigged 22-joint Mixamo-compatible characters in ~1 minute:
- Integrated with [`skin-tokens.cpp`](https://github.com/localai-org/skin-tokens.cpp) for local GPU-accelerated neural skinning weight prediction.
- Synchronizes vertex groups and bind-pose transforms with Blender automation.
- One-click auto-rigging directly inside the web studio.

### 3. Interactive Skinning Weights Heatmap Visualizer
Inspect character skinning directly in Three.js inside the browser:
- **Full-Skeleton Multi-Bone Heatmap**: Distinct rainbow/partition color palette per bone to instantly evaluate vertex coverage and skinning quality.
- **Focused Single-Bone Turbo Heatmap**: Smooth blue-to-red Turbo gradient previewing individual joint influences.
- Bone vertex statistics (coverage percentage, max weight) displayed live in the viewport.

### 4. Zero-Distortion Anatomical Calibration
- **Automatic T-Pose & A-Pose Detection**: Compensates for angled rest limbs, preventing arms from crossing behind the back or clipping through the chest.
- **Height-Aware Floor Grounding**: Proportional root displacement guarantees feet make solid contact with the floor without floating or knee buckling.
- **Clean Single-Action Export**: Purges unused legacy tracks to export pristine GLB & FBX files with opaque material sanitization for WebGL, Lens Studio, and Unity.

### 5. Interactive Dual-Viewport Web Studio (`launch_gui.py`)
- **Side-by-Side Dual Viewports**: Real-time synchronized playback of the SOMA control skeleton alongside your custom 3D character mesh.
- **Live Clearance Sliders**: Non-destructive Arm, Forearm, and Floor Grounding sliders updating character poses instantly without re-generating motion.
- **AI Engines & Models HUD**: Live stage-header indicator displaying status of Motion Synthesis (SOMA), Text Conditioning (Llama-3), Neural Rigging (SkinTokens), GPU backend (Vulkan), and Blender.
- **Blender Auto-Detection & Relocation**: Automatic discovery across standard program directories on Windows/Linux, with a native file browser to relocate or reset custom Blender paths.
- **360° Turntable Video Recorder**: High-speed turntable rotation with automatic canvas capture to export looping demonstration videos.
- **Asset Management & Explorer Integration**: One-click deletion of past generations and direct "Browse folder" shortcut in native Windows Explorer.

---

## Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Blender 3.6, 4.x, or 5.x** (Used for headless retargeting and baking)
- **Vulkan Runtime & Drivers** (Installed automatically with modern NVIDIA/AMD/Intel drivers)

### 2. Install Dependencies & Download Models
Download essential weights (SOMA v1.1 motion, LLaMA-3 text encoder, and SkinTokens neural auto-rigging weights) in one command:

```bash
# Clone the repository
git clone https://github.com/ehab-ayman-gharib/kimodo.cpp-Extended.git
cd kimodo.cpp-Extended

# Install Python requirements
pip install huggingface_hub

# Download essential GGUF models
python scripts/download_gguf_weights.py --essential
```

### 3. Launch the Web Studio

```bash
python launch_gui.py
```

Open **`http://localhost:8094`** in your browser.

1. **Enter a Prompt**: Type an action description (e.g., *"A person balances on one leg with arms raised high like a crane, then jumps and executes a front kick."*) and click **Generate**.
2. **Preview AI Motion**: Watch the 30-joint SOMA skeleton dance or move in the left viewport.
3. **Bake onto Character**: Upload an `.fbx` or `.glb` model on the right panel and click **Bake to Mesh**.
4. **Auto-Rig Static Meshes**: Upload an unrigged character mesh and click **Auto-Rig with SkinTokens** to generate a rigged Mixamo-compatible mesh in ~1 minute.
5. **Adjust Poses**: Drag the **Arm Clearance** or **Floor Grounding** sliders to calibrate spacing live.
6. **Inspect Skinning**: Click **Weights** to toggle the 3D vertex skinning heatmap directly on the character.

---

## Command Line & Batch Baking

### Character Baking via PowerShell

```powershell
.\bake_animation.ps1 -Character "Test_Models\Character_Creator\CC3_Base_Plus.Fbx" -Motion "demo-output\<animation-id>" -Output "output_animated.glb"
```

### Direct Blender CLI Baking

```bash
blender -b -P scripts/bake_to_character.py -- \
  --character "path/to/character.fbx" \
  --motion "path/to/motion_folder_or_glb" \
  --output "path/to/output.glb" \
  --arm-clearance 10.0 \
  --grounding-offset -0.05
```

For mathematical formulations, coordinate frame transforms, and bone mapping topology rules, see **[docs/RETARGETING_CONSTITUTION.md](docs/RETARGETING_CONSTITUTION.md)**.

---

## Build from Source

### Windows (MSVC + CMake)
Install CMake 3.25+, Visual Studio 2022 (with C++ Desktop development), and the Vulkan SDK:

```powershell
# Initialize GGML submodule
git submodule update --init --recursive

# Configure and build Release binaries
cmake -B build -G "Visual Studio 17 2022" -A x64 -DKIMODO_ENABLE_VULKAN=ON
cmake --build build --config Release -j
```

Compiled binaries (`kmd-generate.exe`, `kmd-encode.exe`, `kmd-inspect.exe`) will be generated in `build/Release/` or `build/bin/Release/`.

### Linux & Nix

```bash
git submodule update --init --recursive
scripts/download_gguf_weights.sh --output "$PWD" --model soma-rp-v1.1
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
```

Or reproducibly with Nix:

```bash
nix develop path:. --command cmake --preset debug
nix develop path:. --command cmake --build --preset debug
```

---

## Weights & Models

Ready-to-run native GGML weights are published under the Hugging Face `LocalAI-io` organization:

- **Text Encoder**: [Llama-3-Kimodo-GGML](https://huggingface.co/LocalAI-io/Llama-3-Kimodo-GGML)
- **Motion Checkpoints**:
  - [Kimodo-SOMA-RP-v1.1-GGML](https://huggingface.co/LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML) (30-joint compact control skeleton)
  - [Kimodo-SOMA-SEED-v1.1-GGML](https://huggingface.co/LocalAI-io/Kimodo-SOMA-SEED-v1.1-GGML)
  - [Kimodo-G1-RP-v1-GGML](https://huggingface.co/LocalAI-io/Kimodo-G1-RP-v1-GGML) (34-joint Unitree G1)
  - [Kimodo-G1-SEED-v1-GGML](https://huggingface.co/LocalAI-io/Kimodo-G1-SEED-v1-GGML)
- **Neural Auto-Rigging**: [SkinTokens-GGUF](https://huggingface.co/LocalAI-io/SkinTokens-GGUF) (`mesh-encoder`, `skin-vae`, `tokenrig`)

Install specific models using:

```bash
python scripts/download_gguf_weights.py --model soma-rp-v1.1 --skintokens
```

---

## License

The C++ port, Python studio, and tooling are licensed under **Apache-2.0**; see [LICENSE](LICENSE). GGML, SkinTokens, and the underlying model weights retain their respective licenses:

| Component / Checkpoint | Upstream Terms | Commercial Use |
| --- | --- | --- |
| SOMA RP/SEED v1.1 | [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) | Permitted |
| G1 RP/SEED v1 | [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) | Permitted |
| SkinTokens GGUF | [LocalAI-io / Apache-2.0] | Permitted |
| Kimodo-SMPLX-RP-v1 | [NVIDIA Internal Scientific R&D License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-internal-scientific-research-and-development-model-license/) | Non-commercial R&D only |

---

## Credits & Upstream Acknowledgements

Special thanks and appreciation to:
- **[@jichiep](https://github.com/jichiep)** and the **LocalAI team** for building the core open-source C++ foundations:
  - [`kimodo.cpp`](https://github.com/localai-org/kimodo.cpp): Fast, 100% offline C++ / GGML & Vulkan GPU text-to-motion inference.
  - [`skin-tokens.cpp`](https://github.com/localai-org/skin-tokens.cpp): High-performance C++ neural auto-rigging engine.
- **NVIDIA Research** for the original [Kimodo](https://github.com/NVlabs/kimodo) text-to-motion architecture.
- **The Blender Foundation** for the open-source 3D creation suite powering our headless retargeting engine.
