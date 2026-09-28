"""Shared training loop. train_speech.py / train_visual.py / train_lstm.py /
train_gru.py / train_transformer.py / train_multimodal.py are thin wrappers
that pick a config from config.EXPERIMENTS and call `run(cfg)` here — so the
loop (early stopping, checkpointing, logging) is identical and comparable
across every experiment in spec section 21.
"""
import json
import os

import torch
from torch.utils.data import DataLoader

from utils.seed import set_seed
from utils.splits import participant_split
from utils.metrics import regression_report
from data.dataset import load_manifest, PresentationDataset, collate
from models.multimodal_model import build_model


def run(cfg, manifest_override=None):
    set_seed(cfg.seed)
    manifest_path = manifest_override or cfg.manifest_path
    rows = load_manifest(manifest_path)
    split_map = participant_split([r["participant_id"] for r in rows], seed=cfg.seed)

    train_ds = PresentationDataset(rows, cfg.modality, cfg.targets, "train", split_map)
    val_ds = PresentationDataset(rows, cfg.modality, cfg.targets, "val", split_map)
    test_ds = PresentationDataset(rows, cfg.modality, cfg.targets, "test", split_map)

    train_dl = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, collate_fn=collate)
    val_dl = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False, collate_fn=collate)
    test_dl = DataLoader(test_ds, batch_size=cfg.batch_size, shuffle=False, collate_fn=collate)

    model = build_model(cfg).to(cfg.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    loss_fn = torch.nn.MSELoss()

    best_val_loss = float("inf")
    epochs_without_improvement = 0
    os.makedirs(cfg.checkpoint_dir, exist_ok=True)
    ckpt_path = os.path.join(cfg.checkpoint_dir, f"{cfg.name}.pt")

    for epoch in range(cfg.epochs):
        model.train()
        train_loss = _run_epoch(model, train_dl, cfg, optimizer, loss_fn, train=True)
        model.eval()
        with torch.no_grad():
            val_loss = _run_epoch(model, val_dl, cfg, optimizer, loss_fn, train=False)

        print(f"[{cfg.name}] epoch {epoch+1}/{cfg.epochs}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            torch.save(model.state_dict(), ckpt_path)
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= cfg.patience:
                print(f"[{cfg.name}] early stopping at epoch {epoch+1}")
                break

    model.load_state_dict(torch.load(ckpt_path))
    model.eval()
    test_report = _evaluate(model, test_dl, cfg)

    log_path = os.path.join("experiments", f"{cfg.name}.json")
    os.makedirs("experiments", exist_ok=True)
    with open(log_path, "w") as f:
        json.dump({"config": cfg.__dict__, "best_val_loss": best_val_loss, "test_report": test_report}, f, indent=2)

    print(f"[{cfg.name}] wrote {log_path}")
    return test_report


def _to_device(batch, device):
    for k in ("speech", "speech_mask", "visual", "visual_mask"):
        if k in batch:
            batch[k] = batch[k].to(device)
    batch["targets"] = {t: v.to(device) for t, v in batch["targets"].items()}
    return batch


def _run_epoch(model, dl, cfg, optimizer, loss_fn, train):
    total_loss, n_batches = 0.0, 0
    for batch in dl:
        batch = _to_device(batch, cfg.device)
        preds = model(batch)
        losses = []
        for t in cfg.targets:
            if t not in batch["targets"] or t not in preds:
                continue
            valid = ~torch.isnan(batch["targets"][t])
            if valid.any():
                losses.append(loss_fn(preds[t][valid], batch["targets"][t][valid]))
        if not losses:
            continue
        loss = torch.stack(losses).mean()

        if train:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        total_loss += loss.item()
        n_batches += 1
    return total_loss / max(1, n_batches)


def _evaluate(model, dl, cfg):
    all_preds, all_true = {t: [] for t in cfg.targets}, {t: [] for t in cfg.targets}
    with torch.no_grad():
        for batch in dl:
            batch = _to_device(batch, cfg.device)
            preds = model(batch)
            for t in cfg.targets:
                if t not in batch["targets"] or t not in preds:
                    continue
                valid = ~torch.isnan(batch["targets"][t])
                all_preds[t].extend(preds[t][valid].tolist())
                all_true[t].extend(batch["targets"][t][valid].tolist())

    report = {}
    for t in cfg.targets:
        if all_true[t]:
            report[t] = regression_report(all_true[t], all_preds[t])
    return report
