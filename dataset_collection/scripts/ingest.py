"""Scans raw_recordings/<participant_id>/<scenario>/<attempt_n>/ into a
manifest.csv matching training/data/manifest_schema.py. Run this first,
then merge_ratings.py, then precompute_features.py (see PROTOCOL.md).

Expects, per attempt folder:
    audio.wav
    video.mp4        (optional at this stage — a warning is printed if missing)
    transcript.txt
    script.txt

Leaves speech_feature_path/visual_feature_path pointing at the raw audio/
video files for now; precompute_features.py overwrites them with real .npy
paths once torch is available.
"""
import argparse
import csv
import os

REQUIRED = ["audio.wav", "transcript.txt", "script.txt"]
OPTIONAL = ["video.mp4"]


def scan(raw_dir):
    rows = []
    if not os.path.isdir(raw_dir):
        print(f"no such directory: {raw_dir}")
        return rows

    for participant_id in sorted(os.listdir(raw_dir)):
        p_path = os.path.join(raw_dir, participant_id)
        if not os.path.isdir(p_path) or participant_id.startswith("."):
            continue
        for scenario in sorted(os.listdir(p_path)):
            s_path = os.path.join(p_path, scenario)
            if not os.path.isdir(s_path):
                continue
            for attempt in sorted(os.listdir(s_path)):
                a_path = os.path.join(s_path, attempt)
                if not os.path.isdir(a_path):
                    continue

                missing = [f for f in REQUIRED if not os.path.isfile(os.path.join(a_path, f))]
                if missing:
                    print(f"skipping {a_path}: missing {missing}")
                    continue

                video_path = os.path.join(a_path, "video.mp4")
                if not os.path.isfile(video_path):
                    video_path = os.path.join(a_path, "video.webm")
                if not os.path.isfile(video_path):
                    print(f"warning: no video.mp4/video.webm in {a_path} (visual features will be unavailable for this row)")
                    video_path = ""

                with open(os.path.join(a_path, "transcript.txt")) as f:
                    transcript = f.read().strip()
                with open(os.path.join(a_path, "script.txt")) as f:
                    script = f.read().strip()

                rows.append({
                    "participant_id": participant_id,
                    "presentation_id": f"{participant_id}_{scenario}_{attempt}",
                    "scenario": scenario,
                    "speech_feature_path": os.path.join(a_path, "audio.wav"),  # raw for now
                    "visual_feature_path": video_path,                          # raw for now
                    "transcript": transcript,
                    "script": script,
                })
    return rows


def write_manifest(rows, out_path):
    if not rows:
        print("no rows found — nothing written")
        return
    # target columns get added empty here; merge_ratings.py fills them in
    from_target_cols = ["fluency", "pronunciation", "script_accuracy", "eye_contact",
                         "posture", "gesture_activity", "overall_delivery"]
    fieldnames = list(rows[0].keys()) + from_target_cols
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            for t in from_target_cols:
                row.setdefault(t, "")
            writer.writerow(row)
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--raw_dir", default=os.path.join(here, "raw_recordings"))
    parser.add_argument("--out", default=os.path.join(here, "manifest.csv"))
    args = parser.parse_args()

    rows = scan(args.raw_dir)
    write_manifest(rows, args.out)
