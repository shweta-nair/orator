"""Takes the .webm + .json pairs the browser demo downloads (see
frontend/index.html's "Finish & save recording" button) and organizes them
into raw_recordings/<participant>/<scenario>/<attempt>/, extracting a real
audio.wav via ffmpeg so ingest.py's requirements are met.

Usage:
    python organize_downloads.py --src "C:\\Users\\you\\Downloads"

Requires ffmpeg on PATH (https://ffmpeg.org/download.html). Without it,
audio.wav can't be produced and ingest.py will skip those recordings.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None


def process_pair(json_path, raw_dir):
    with open(json_path) as f:
        meta = json.load(f)

    webm_path = os.path.splitext(json_path)[0] + ".webm"
    if not os.path.isfile(webm_path):
        print(f"skipping {json_path}: no matching .webm found")
        return False

    dest = os.path.join(raw_dir, meta["participant_id"], meta["scenario"], f"attempt{meta['attempt']}")
    os.makedirs(dest, exist_ok=True)

    video_dest = os.path.join(dest, "video.webm")
    shutil.copy2(webm_path, video_dest)  # OpenCV can read webm directly (see visual_encoder.py)

    audio_dest = os.path.join(dest, "audio.wav")
    if has_ffmpeg():
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, "-vn", "-ar", "16000", "-ac", "1", audio_dest],
            capture_output=True, text=True,
        )
        if result.returncode != 0 or not os.path.isfile(audio_dest):
            print(f"warning: ffmpeg failed to extract audio for {webm_path}\n{result.stderr[-500:]}")
    else:
        print(f"warning: ffmpeg not found on PATH — audio.wav not created for {dest}; "
              f"install ffmpeg (https://ffmpeg.org/download.html) and re-run this script")

    with open(os.path.join(dest, "transcript.txt"), "w") as f:
        f.write(meta.get("transcript", ""))
    with open(os.path.join(dest, "script.txt"), "w") as f:
        f.write(meta.get("script", ""))

    print(f"organized -> {dest}")
    return True


def run(src_dir, raw_dir):
    json_files = glob.glob(os.path.join(src_dir, "*.json"))
    if not json_files:
        print(f"no .json metadata files found in {src_dir}")
        return
    count = sum(process_pair(j, raw_dir) for j in json_files)
    print(f"\norganized {count}/{len(json_files)} recordings into {raw_dir}")
    if count:
        print("next: run ingest.py, then merge_ratings.py once ratings exist")


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="folder the browser downloaded .webm/.json pairs into")
    parser.add_argument("--raw_dir", default=os.path.join(here, "raw_recordings"))
    args = parser.parse_args()
    run(args.src, args.raw_dir)
