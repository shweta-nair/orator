"""Averages human_ratings.csv (one row per rater per recording, matching
rating_rubric.csv's columns) into manifest.csv's target columns. Safe to
re-run — it recomputes averages from scratch each time rather than
accumulating.
"""
import argparse
import csv
import os
from collections import defaultdict

TARGETS = ["fluency", "pronunciation", "script_accuracy", "eye_contact",
           "posture", "gesture_activity", "overall_delivery"]


def load_ratings(path):
    per_recording = defaultdict(lambda: defaultdict(list))
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = (row.get("presentation_id") or "").strip()
            if not pid or pid.startswith("#"):
                continue
            for t in TARGETS:
                val = (row.get(t) or "").strip()
                if val != "":
                    per_recording[pid][t].append(float(val))
    return per_recording


def averaged(per_recording):
    out = {}
    for pid, dims in per_recording.items():
        out[pid] = {t: round(sum(vals) / len(vals), 1) for t, vals in dims.items() if vals}
    return out


def merge(manifest_path, ratings_path, out_path):
    ratings = averaged(load_ratings(ratings_path))

    with open(manifest_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    updated = 0
    for row in rows:
        pid = row["presentation_id"]
        if pid in ratings:
            row.update({t: v for t, v in ratings[pid].items()})
            updated += 1

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"updated ratings for {updated}/{len(rows)} manifest rows -> {out_path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=os.path.join(here, "manifest.csv"))
    parser.add_argument("--ratings", default=os.path.join(here, "human_ratings.csv"))
    parser.add_argument("--out", default=None, help="defaults to overwriting --manifest")
    args = parser.parse_args()
    merge(args.manifest, args.ratings, args.out or args.manifest)
