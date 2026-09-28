"""Generates a fake manifest.csv plus random .npy feature files, so the
dataset/split/model wiring can be exercised end-to-end before any real
recordings exist. NEVER treat metrics computed on this data as findings —
the whole point is to catch shape/plumbing bugs, not to measure anything.
"""
import csv
import os
import random

import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), "synthetic")
SCENARIOS = ["academic", "news", "flight", "advertisement", "speech"]
TARGETS = ["fluency", "pronunciation", "script_accuracy", "eye_contact", "posture",
           "gesture_activity", "overall_delivery"]


def make(n_participants=12, recordings_per_participant=3, speech_dim=768, visual_dim=512, seed=42):
    rng = np.random.default_rng(seed)
    random.seed(seed)
    os.makedirs(os.path.join(OUT_DIR, "speech"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "visual"), exist_ok=True)

    rows = []
    for p in range(n_participants):
        pid = f"p{p:03d}"
        for r in range(recordings_per_participant):
            rec_id = f"{pid}_rec{r}"
            t_speech = rng.integers(40, 90)
            t_visual = rng.integers(20, 45)

            speech_feat = rng.normal(size=(t_speech, speech_dim)).astype(np.float32)
            visual_feat = rng.normal(size=(t_visual, visual_dim)).astype(np.float32)
            speech_path = os.path.join(OUT_DIR, "speech", f"{rec_id}.npy")
            visual_path = os.path.join(OUT_DIR, "visual", f"{rec_id}.npy")
            np.save(speech_path, speech_feat)
            np.save(visual_path, visual_feat)

            row = {
                "participant_id": pid,
                "presentation_id": rec_id,
                "scenario": random.choice(SCENARIOS),
                "speech_feature_path": speech_path,
                "visual_feature_path": visual_path,
                "transcript": "synthetic transcript placeholder",
                "script": "synthetic script placeholder",
            }
            for t in TARGETS:
                row[t] = round(float(rng.uniform(40, 95)), 1)
            rows.append(row)

    manifest_path = os.path.join(OUT_DIR, "manifest.csv")
    fieldnames = list(rows[0].keys())
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} synthetic rows to {manifest_path}")
    return manifest_path


if __name__ == "__main__":
    make()
