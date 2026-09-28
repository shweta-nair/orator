"""Experiment 1 — speech only (spec section 21)."""
import argparse
from config import EXPERIMENTS
import train_common

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()
    train_common.run(EXPERIMENTS["speech_only"], manifest_override=args.manifest)
