"""Experiment 7 (optional) — multimodal + Transformer temporal encoder."""
import argparse
from config import EXPERIMENTS
import train_common

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()
    train_common.run(EXPERIMENTS["multimodal_transformer"], manifest_override=args.manifest)
