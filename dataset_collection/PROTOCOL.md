# Custom Dataset Collection Protocol

This is the concrete next milestone: without this, there is no data to run
Experiment 1 (speech-only) on, let alone anything multimodal. Nothing else
in this repo produces a real research result until recordings + ratings
exist.

## 1. Recruit participants

- Aim for **at least 15-20 participants** to start. With 5 scenarios and
  ~2-3 attempts each, that's 150-300 recordings — enough to run a first
  participant-level train/val/test split (`utils/splits.py`) without every
  split being 1-2 people.
- Classmates, project teammates, and volunteers from your department are
  the realistic pool for a thesis timeline. Track `participant_id` as an
  anonymized code (`p001`, `p002`, ...), not a name, from the first file
  you save — see `consent_form_template.md`.

## 2. Scenarios

Five starter scripts are in `scenarios/` (spec section 18). Each
participant reads (or paraphrases, for the "advanced" difficulty tier) all
five, ideally on separate days to avoid fatigue flattening the variation
you're trying to measure.

| Scenario | Typical length | Difficulty (spec section 35) |
|---|---|---|
| academic | 60-90s | intermediate |
| news | 30-45s | beginner |
| flight announcement | 30-45s | beginner |
| advertisement | 20-30s | intermediate |
| formal speech | 60-120s | advanced |

## 3. Recording setup

Use `frontend/index.html` directly — it now saves real files:

1. On the setup screen, fill in the participant code, pick the scenario,
   and set the attempt number, then paste that scenario's script from
   `scenarios/`.
2. Click "Finish & save recording" when done — the browser downloads two
   files: `<participant>_<scenario>_attempt<N>.webm` (the actual
   audio+video) and a matching `.json` sidecar (transcript, script,
   duration). Both land in the browser's default Downloads folder.
3. Have each participant do all 5 scenarios this way. Move their `.webm`/
   `.json` pairs out of Downloads into one shared folder per session (or
   just let them accumulate — `organize_downloads.py` scans by matching
   filename pairs, not by folder).
4. Once you've collected a batch, organize them in one step:
   ```bash
   python scripts/organize_downloads.py --src "C:\Users\you\Downloads"
   ```
   This extracts a real `audio.wav` via ffmpeg, keeps the original as
   `video.webm`, and writes `transcript.txt`/`script.txt` — exactly the
   layout `ingest.py` expects. **Requires ffmpeg on PATH**
   (https://ffmpeg.org/download.html) — without it, video is saved but no
   `audio.wav` is produced, and `ingest.py` will skip those recordings
   until you install it and re-run.

## 4. Human ratings

- Each recording needs ratings on the target dimensions in
  `training/data/manifest_schema.py::TARGET_COLUMNS` (fluency, pronunciation,
  script_accuracy, eye_contact, posture, gesture_activity, overall_delivery).
- Use `rating_rubric.csv` as the actual rating instrument — hand it to
  raters as a spreadsheet, one row per recording, one column per dimension,
  0-100 scale with the anchors described in the rubric notes.
- **Use at least 2 raters per recording** where possible (spec section 18
  explicitly calls for multiple evaluators) — inter-rater agreement is
  itself something worth reporting in a thesis, and `scripts/merge_ratings.py`
  averages multiple raters automatically.

## 5. Turn it into a manifest

```bash
python scripts/organize_downloads.py --src "C:\Users\you\Downloads"   # webm/json -> raw_recordings/
python scripts/ingest.py            # raw_recordings/ -> manifest.csv (no feature paths yet)
python scripts/merge_ratings.py     # merges human_ratings.csv into manifest.csv target columns
# once torch/transformers/torchvision are installed on a machine with room for them:
python scripts/precompute_features.py   # fills in speech_feature_path / visual_feature_path
```

The resulting `manifest.csv` matches exactly what `training/train_speech.py`
etc. expect — point `--manifest` at it and Experiment 1 becomes a real
number for the first time.

## 6. Ethics / consent

Get written consent before recording anyone, even informally for a thesis —
see `consent_form_template.md`. If your institution has an ethics/IRB
process for research involving human subjects (recording people's voice and
face), check whether this project needs sign-off before you start recruiting.
