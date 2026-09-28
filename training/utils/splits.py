"""Participant-level train/val/test split.

Spec section 19 explicitly calls out avoiding identity leakage: never split
individual clips from the same participant across train and test. This
splits by participant_id, not by row, so every recording from one person
lands entirely in one split.
"""
import random


def participant_split(participant_ids, val_frac=0.15, test_frac=0.15, seed=42):
    unique = sorted(set(participant_ids))
    rng = random.Random(seed)
    rng.shuffle(unique)

    n = len(unique)
    n_test = max(1, round(n * test_frac)) if n > 2 else 0
    n_val = max(1, round(n * val_frac)) if n > 2 else 0

    test_ids = set(unique[:n_test])
    val_ids = set(unique[n_test:n_test + n_val])
    train_ids = set(unique[n_test + n_val:])

    return {"train": train_ids, "val": val_ids, "test": test_ids}


def assign_split(participant_id, split_map):
    for split_name, ids in split_map.items():
        if participant_id in ids:
            return split_name
    return "train"


if __name__ == "__main__":
    # quick self-check — no torch required
    fake_ids = [f"p{i}" for i in range(20)] * 3  # 3 recordings each, simulating repeats
    splits = participant_split(fake_ids)
    overlap = splits["train"] & splits["val"] & splits["test"]
    assert not (splits["train"] & splits["val"]), "train/val overlap"
    assert not (splits["train"] & splits["test"]), "train/test overlap"
    assert not (splits["val"] & splits["test"]), "val/test overlap"
    print("participant split OK:", {k: len(v) for k, v in splits.items()})
