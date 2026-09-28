"""Experiment 3 — full speech+visual fusion model (spec section 21).
Also where Experiment 4 (no temporal) and Experiment 8 (fusion comparison)
configs live in config.EXPERIMENTS — point --experiment at any of them.
"""
import argparse
from config import EXPERIMENTS
import train_common

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default="multimodal_lstm",
                         choices=[k for k in EXPERIMENTS if k.startswith("multimodal")])
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()
    train_common.run(EXPERIMENTS[args.experiment], manifest_override=args.manifest)
