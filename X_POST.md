# Kimodo-CPP Extended: Universal AI Motion Retargeting 🚀

Supercharged **Kimodo-CPP** with local GGUF neural motion generation and a universal 3D character baking engine.

Here is everything new in this release 👇

---

### 🧠 Core Neural Engine & Inference
* **100% Offline & Local**: High-speed C++ GGUF inference powered by ggml (zero external API dependencies).
* **Quantized Multi-Model Support**: Native support for SOMA-RP v1.1, SOMA-SEED, and SMPL-X motion models.
* **Diffusion Motion Synthesis**: Text-to-motion generation in seconds directly on consumer hardware.

---

### 🎭 Universal Multi-Rig Retargeting & Character Baker
Bake AI motion directly onto any 3D character mesh with zero distortion while **preserving native skeleton hierarchies**:

* **Universal T-Pose & A-Pose Calibration**: Smart rest-pose detection that automatically compensates for angled limbs, preventing arms from clipping through the chest or crossing behind the back.
* **Native Unreal Engine Mannequins (`SK_Mannequin` / UE4 & UE5)**: Preserves native `pelvis`, `upperarm_l`, and `thigh_l` hierarchies so assets drop seamlessly into Unreal animation blueprints.
* **Native Reallusion Character Creator (CC3 & CC4)**: Preserves native `CC_Base_Hip` hierarchies for instant compatibility with CC4 and iClone.
* **Standard Humanoid & Mixamo**: Direct in-place baking preserving original character names and custom prefixes (`Hero_`, `Bear_Mama_`).
* **Autodesk 3ds Max Bipeds**: Modernizes classic Character Studio `Bip001` and `Bip<Name>` rigs into clean, standard meter GLBs with zero mesh stretching.

---

### 📐 Anatomical Precision & Grounding
* **Proportional Floor Grounding**: Height-aware root displacement guarantees solid floor contact without floating or knee buckling.
* **Enforced 30 FPS Timeline**: Sanitizes incoming FBX metadata to prevent fast-forward or desynchronized playback.
* **Clean Single-Action Export**: Purges legacy tracks to export pristine GLB & FBX files with opaque material sanitization for WebGL/Lens Studio/Unity.

---

### 💻 Dual-View Web Studio & Asset Management
* **Side-by-Side Dual Viewport**: Real-time synchronized playback of the SOMA skeleton alongside your custom 3D character mesh.
* **Drag-and-Drop Character Baking**: Instant preview and download of animated GLBs ready for game engines.
* **One-Click Asset Management**: Delete unwanted past animations and manage your generation gallery directly in-browser.
* **Native File Explorer Integration**: Open the active generation folder directly in Windows Explorer with the "Browse folder" shortcut.

---

#3DAnimation #GameDev #AI #MotionGeneration #Blender #Mixamo #CharacterCreator #IndieDev
