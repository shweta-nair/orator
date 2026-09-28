"""Offline speech feature extraction — run once per recording to produce the
.npy embeddings the training pipeline actually consumes (see data/dataset.py).
Kept separate from the training loop so swapping encoders never touches
model/training code, only re-runs this precompute step.

Requires: torch, transformers (not installed in this sandbox — install
before running). No training-time dependency on this file.
"""
import numpy as np


def extract_features(audio_path: str, model_name: str = "facebook/wav2vec2-base-960h",
                      target_sr: int = 16000) -> np.ndarray:
    """Returns a [T, 768] array of per-frame speech embeddings (wav2vec2-base
    hidden size). Swap model_name for a WavLM/HuBERT/Whisper-encoder
    checkpoint to compare speech encoders (spec section 4)."""
    import torch
    import torchaudio
    from transformers import Wav2Vec2Model, Wav2Vec2FeatureExtractor

    waveform, sr = torchaudio.load(audio_path)
    if sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, sr, target_sr)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
    model = Wav2Vec2Model.from_pretrained(model_name)
    model.eval()

    inputs = extractor(waveform.squeeze(0).numpy(), sampling_rate=target_sr, return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs)
    return out.last_hidden_state.squeeze(0).numpy()  # [T, 768]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python speech_encoder.py <audio.wav> <out.npy>")
        raise SystemExit(1)
    feats = extract_features(sys.argv[1])
    np.save(sys.argv[2], feats)
    print("saved", feats.shape, "to", sys.argv[2])
