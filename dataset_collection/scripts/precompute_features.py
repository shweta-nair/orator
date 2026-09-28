"""Runs the offline encoders (training/models/speech_encoder.py,
visual_encoder.py) over every row in manifest.csv, replacing the raw
audio/video paths ingest.py left behind with real .npy embedding paths.

Requires torch, torchaudio, torchvision, transformers — not installed in
the sandbox this scaffold was built in. Not executed; syntax-checked only.
Run this on a machine with those installed before training.
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "training"))

FEATURES_DIR_NAME = "features"


def run(manifest_path, out_path):
    from models.speech_encoder import extract_features as extract_speech
    from models.visual_encoder import extract_features as extract_visual
    import numpy as np

    base = os.path.dirname(os.path.abspath(manifest_path))
    feat_dir = os.path.join(base, FEATURES_DIR_NAME)
    os.makedirs(os.path.join(feat_dir, "speech"), exist_ok=True)
    os.makedirs(os.path.join(feat_dir, "visual"), exist_ok=True)

    with open(manifest_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    for row in rows:
        pid = row["presentation_id"]
        audio_path = row["speech_feature_path"]
        if audio_path and os.path.isfile(audio_path) and not audio_path.endswith(".npy"):
            feats = extract_speech(audio_path)
            out = os.path.join(feat_dir, "speech", f"{pid}.npy")
            np.save(out, feats)
            row["speech_feature_path"] = out
            print(f"speech features -> {out}  {feats.shape}")

        video_path = row["visual_feature_path"]
        if video_path and os.path.isfile(video_path) and not video_path.endswith(".npy"):
            feats = extract_visual(video_path)
            out = os.path.join(feat_dir, "visual", f"{pid}.npy")
            np.save(out, feats)
            row["visual_feature_path"] = out
            print(f"visual features -> {out}  {feats.shape}")
        elif not video_path:
            print(f"warning: {pid} has no video — will only be usable for speech-only experiments")

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote updated manifest -> {out_path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=os.path.join(here, "manifest.csv"))
    parser.add_argument("--out", default=None, help="defaults to overwriting --manifest")
    args = parser.parse_args()
    run(args.manifest, args.out or args.manifest)
