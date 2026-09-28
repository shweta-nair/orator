# Next Steps (prioritized)

Honest read of where this project actually stands: the web layer and
rule-based analysis work end-to-end; the deep-learning research contribution
— the actual point of the thesis — has architecture but zero data and zero
executed training runs. This is the order that gets you to a first real
result fastest.

## 1. Get PyTorch running somewhere with real headroom
This sandbox couldn't install it (disk space, and no route to a CPU-only
wheel index). You'll need a machine — your own laptop, a lab machine, or a
free-tier Colab/Kaggle notebook — with a few GB free and normal internet
access. `pip install torch torchvision torchaudio transformers`.

## 2. Prove the pipeline wiring first, on synthetic data
```bash
python training/data/make_synthetic_manifest.py
python training/train_speech.py
python training/evaluate.py
```
This should run without errors and produce meaningless-but-real numbers
(random data, so nothing to interpret) — the point is only to catch any
shape/dependency bugs in `training/` before real data is on the line.

## 3. Start data collection immediately, in parallel
This is the actual bottleneck, and it takes calendar time (recruiting,
recording, rating) that no amount of coding shortens. Start with
`dataset_collection/PROTOCOL.md` today:
- Recruit 15-20 participants
- Record all 5 scenarios per person using `frontend/index.html`
- Get 2+ raters scoring each recording with `dataset_collection/rating_rubric.csv`

## 4. First real result: Experiment 1 (speech-only)
Once you have even 10-15 rated recordings:
```bash
python dataset_collection/scripts/ingest.py
python dataset_collection/scripts/merge_ratings.py
python dataset_collection/scripts/precompute_features.py   # needs step 1's torch env
python training/train_speech.py --manifest dataset_collection/manifest.csv
```
This is the first number in the thesis that means something. Everything
before this point is infrastructure, not a finding.

## 5. Then, in order
- Experiment 2 (vision-only) once you also have video for those recordings
- Experiment 3/4 (multimodal, with vs. without temporal modeling)
- Experiments 5-7 (LSTM vs. GRU vs. Transformer comparison)
- Experiment 8 (fusion comparison: concat vs. attention)
- `evaluate.py` prints the comparison table for the write-up

## 6. Only after there's a real trained model
- Wire the Flask backend's `attempts` endpoint to call the trained model
  instead of the current rule-based `fusion_service.py` — the API shape
  (`speech`, `visual`, `overall` scores) was designed to not need to change
  when you do this.
- (The history/progress/dashboard pages are now built and read the stored
  attempts, so a trained model only has to return the same `speech` /
  `visual` / `overall` fields.)
- Consider the stretch features (impromptu mode, AI script generator, etc.)
  only if time remains — they're the least essential part of the thesis
  contribution.

## Realistic timeline flag
Sections 1-2 are a day or two of work. Section 3 (data collection) is
realistically **weeks**, not days, if you want more than a token dataset —
scope your thesis timeline around that, not around the code.
