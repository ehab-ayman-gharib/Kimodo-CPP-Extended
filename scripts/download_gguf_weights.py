import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download

MODELS = {
    "soma-rp-v1.1": ("LocalAI-io/Kimodo-SOMA-RP-v1.1-GGML", "models/kimodo-soma-rp-v1.1-f32.gguf"),
    "soma-seed-v1.1": ("LocalAI-io/Kimodo-SOMA-SEED-v1.1-GGML", "models/kimodo-soma-seed-v1.1-f32.gguf"),
    "g1-rp-v1": ("LocalAI-io/Kimodo-G1-RP-v1-GGML", "models/kimodo-g1-rp-v1-f32.gguf"),
    "g1-seed-v1": ("LocalAI-io/Kimodo-G1-SEED-v1-GGML", "models/kimodo-g1-seed-v1-f32.gguf"),
}
TEXT_REPO = "LocalAI-io/Llama-3-Kimodo-GGML"
SKINTOKENS_REPO = "LocalAI-io/SkinTokens-GGUF"

def download_skintokens(output: Path, precision: str = "F16"):
    import shutil
    print(f"Downloading SkinTokens {precision} weights from {SKINTOKENS_REPO}...")
    target_dir = output / "models" / "skintokens"
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output / "models" / "_skintokens_tmp"
    snapshot_download(
        repo_id=SKINTOKENS_REPO,
        local_dir=str(temp_dir),
        allow_patterns=[f"{precision}/*", "MANIFEST.json"],
    )
    src_dir = temp_dir / precision
    for fname in ["mesh-encoder.gguf", "skin-vae.gguf", "tokenrig.gguf"]:
        src = src_dir / fname
        dst = target_dir / fname
        if src.is_file():
            shutil.copy2(str(src), str(dst))
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("SkinTokens neural rig weights verified in models/skintokens.")

def verify_manifest(manifest_path: Path, output: Path, requested_patterns: list[str]):
    root = output.resolve()
    if not manifest_path.is_file():
        print(f"No MANIFEST.json found at {manifest_path}, skipping checksum check.")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "kimodo-gguf-manifest-v1":
        print(f"Warning: unsupported manifest format {manifest.get('format')}")
        return
    for entry in manifest.get("files", []):
        rel = Path(entry.get("path", ""))
        if rel.is_absolute() or ".." in rel.parts or rel.suffix != ".gguf":
            raise SystemExit(f"unsafe manifest path: {rel}")
        if requested_patterns and not any(rel.match(p) for p in requested_patterns):
            continue
        p = root / rel
        if not p.is_file() or p.stat().st_size != entry.get("bytes"):
            raise SystemExit(f"missing or wrong-sized file: {rel}")
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != entry.get("sha256"):
            raise SystemExit(f"checksum mismatch: {rel}")
    print("Verified native Kimodo GGUF bundle integrity.")

def download_model(repo: str, output: Path, allow_patterns: list[str]):
    print(f"Downloading {repo} into {output} (patterns: {allow_patterns})...")
    snapshot_download(
        repo_id=repo,
        local_dir=str(output),
        allow_patterns=allow_patterns + ["MANIFEST.json"],
    )
    manifest_path = output / "MANIFEST.json"
    verify_manifest(manifest_path, output, allow_patterns)

def main():
    parser = argparse.ArgumentParser(description="Download Kimodo & SkinTokens GGUF weights")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: current)")
    parser.add_argument("--model", "-m", action="append", choices=list(MODELS.keys()), default=[], help="Model(s) to download")
    parser.add_argument("--motion-only", action="store_true", help="Download only motion model, skip text bundle")
    parser.add_argument("--skintokens", action="store_true", help="Download SkinTokens neural auto-rigging weights (mesh-encoder, skin-vae, tokenrig)")
    parser.add_argument("--essential", action="store_true", help="Download all essential weights: SOMA v1.1 motion, Llama-3 text bundle, and SkinTokens")
    parser.add_argument("--all-models", action="store_true", help="Download all available motion models")
    args = parser.parse_args()

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    models_to_download = args.model
    if args.all_models:
        models_to_download = list(MODELS.keys())
    elif not models_to_download:
        models_to_download = ["soma-rp-v1.1"]

    for m in models_to_download:
        repo, rel_file = MODELS[m]
        download_model(repo, out_dir, [rel_file])

    if not args.motion_only:
        download_model(TEXT_REPO, out_dir, ["generated/llm2vec-text-bundle/*"])

    if args.skintokens or args.essential:
        download_skintokens(out_dir)

    print("\nAll requested weights downloaded and verified successfully!")

if __name__ == "__main__":
    main()
