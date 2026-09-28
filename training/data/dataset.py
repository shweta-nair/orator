"""Datasets consuming a manifest CSV (see manifest_schema.py) plus precomputed
.npy feature files. No raw audio/video processing happens here — that's
models/speech_encoder.py and models/visual_encoder.py's job, run offline.
"""
import csv
import numpy as np
import torch
from torch.utils.data import Dataset

from data.manifest_schema import TARGET_COLUMNS


def load_manifest(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _pad_stack(seqs):
    """Pads a list of [T_i, D] arrays to [B, T_max, D] plus a [B, T_max] mask."""
    max_t = max(s.shape[0] for s in seqs) if seqs else 1
    dim = next((s.shape[1] for s in seqs if s.ndim == 2), 1)
    batch = np.zeros((len(seqs), max_t, dim), dtype=np.float32)
    mask = np.zeros((len(seqs), max_t), dtype=np.float32)
    for i, s in enumerate(seqs):
        t = s.shape[0]
        if t:
            batch[i, :t] = s
            mask[i, :t] = 1.0
    return torch.from_numpy(batch), torch.from_numpy(mask)


class PresentationDataset(Dataset):
    def __init__(self, manifest_rows, modality="multimodal", targets=TARGET_COLUMNS, split=None, split_map=None):
        if split and split_map:
            from utils.splits import assign_split
            manifest_rows = [r for r in manifest_rows if assign_split(r["participant_id"], split_map) == split]
        self.rows = manifest_rows
        self.modality = modality
        self.targets = [t for t in targets if any(r.get(t) not in (None, "") for r in manifest_rows)]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        item = {"presentation_id": row["presentation_id"], "participant_id": row["participant_id"]}
        if self.modality in ("speech", "multimodal"):
            item["speech"] = np.load(row["speech_feature_path"]).astype(np.float32)
        if self.modality in ("visual", "multimodal"):
            item["visual"] = np.load(row["visual_feature_path"]).astype(np.float32)
        item["targets"] = {t: float(row[t]) for t in self.targets if row.get(t) not in (None, "")}
        return item


def collate(batch):
    out = {}
    if "speech" in batch[0]:
        out["speech"], out["speech_mask"] = _pad_stack([b["speech"] for b in batch])
    if "visual" in batch[0]:
        out["visual"], out["visual_mask"] = _pad_stack([b["visual"] for b in batch])

    all_targets = sorted({k for b in batch for k in b["targets"]})
    out["targets"] = {
        t: torch.tensor([b["targets"].get(t, float("nan")) for b in batch], dtype=torch.float32)
        for t in all_targets
    }
    out["presentation_ids"] = [b["presentation_id"] for b in batch]
    return out
