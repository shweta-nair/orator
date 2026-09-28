# Training pipeline

This is architecture scaffolding for the project's actual research
contribution (spec sections 4-13, 19-22): a deep-learning pipeline that
takes speech + visual features and predicts presentation-quality scores.

**Status: structural, not executed.** These scripts are written to run
against a real manifest of recordings + human ratings once one exists.
There is no real dataset here and no trained checkpoint — running this
against the synthetic manifest (`data/make_synthetic_manifest.py`) only
proves the code is wired correctly (shapes match, loss decreases on
noise), never a research result. Do not present numbers from a synthetic
run as findings.

## Layout

```
training/
  config.py                 experiment configs (paths, hyperparams, which
                             encoder/temporal/fusion variant to use)
  data/
    manifest_schema.py       required manifest columns
    dataset.py               PyTorch Datasets: SpeechOnly, VisionOnly, Multimodal
    make_synthetic_manifest.py   generates a fake manifest + random feature
                                  tensors, for smoke-testing the pipeline only
  models/
    speech_encoder.py         wraps a pretrained speech model (Whisper/
                               wav2vec2/HuBERT/WavLM via `transformers`)
    visual_encoder.py         CNN/ViT frame encoder (torchvision backbone)
    temporal.py                LSTM / GRU / Transformer sequence encoders
    fusion.py                  concatenation baseline + attention fusion
    heads.py                   single-task + multi-task assessment heads
    multimodal_model.py         assembles encoder(s) + temporal + fusion + head
  utils/
    seed.py                    reproducibility
    splits.py                  participant-level train/val/test split (no
                                identity leakage across a person's recordings)
    metrics.py                 MAE, RMSE, Pearson r, Spearman rho, F1 etc.
  train_speech.py              Experiment 1 — speech only
  train_visual.py               Experiment 2 — vision only
  train_lstm.py                 Experiment 5 — temporal: LSTM
  train_gru.py                  Experiment 6 — temporal: GRU
  train_transformer.py          Experiment 7 — temporal: Transformer (optional)
  train_multimodal.py           Experiment 3 — full fusion model
  evaluate.py                    loads checkpoints, prints the comparison
                                  table across experiments (section 22)
```

`train_lstm.py` / `train_gru.py` / `train_transformer.py` /
`train_speech.py` / `train_visual.py` / `train_multimodal.py` are thin
wrappers around the shared loop in `train_common.py` — they only fix which
encoders + temporal model + fusion get built, so the six scripts stay
comparable and don't duplicate the training loop six times.

## Before this can produce real results

1. A real manifest (see `data/manifest_schema.py`) — either the custom
   recorded dataset (spec section 18) or a supported public one
   (SpeechOcean762 for pronunciation, TED-LIUM for speech-only pretraining
   context, DAiSEE for engagement — not presentation-quality labels,
   SOPHIAS per its own access process).
2. Precomputed or on-the-fly speech/visual features from real pretrained
   encoders (`transformers`, `torchvision`/`mediapipe`) instead of the
   random-projection fallback encoders in this scaffold — swapped in
   automatically once real model weights + those libraries are available
   in the environment (see `models/speech_encoder.py`,
   `models/visual_encoder.py`).
3. Human ratings per recording to train against.

## Try it against synthetic data (structural check only)

Run these from inside `training/` (not the repo root) — the scripts use
paths relative to that folder.

```bash
cd training
pip install torch torchvision torchaudio transformers  # not installed in this environment — see note in models/
python data/make_synthetic_manifest.py          # writes data/synthetic/manifest.csv
python train_speech.py --manifest data/synthetic/manifest.csv
python evaluate.py                               # reads experiments/*.json, written by the line above
```

`train_visual.py` / `train_lstm.py` / `train_gru.py` / `train_transformer.py`
take the same `--manifest` flag; `train_multimodal.py` additionally takes
`--experiment <name>` to pick which config in `config.py::EXPERIMENTS` to run
(e.g. `--experiment multimodal_attention_fusion`). Run several before
`evaluate.py` to see more than one row in its comparison table.
