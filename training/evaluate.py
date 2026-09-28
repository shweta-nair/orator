"""Prints the comparative table from spec section 22 across every experiment
that has a logged result in experiments/*.json (written by train_common.run).
Run the relevant train_*.py scripts first — this only reads their output.
"""
import argparse
import glob
import json


def load_logs(pattern="experiments/*.json"):
    logs = {}
    for path in glob.glob(pattern):
        with open(path) as f:
            data = json.load(f)
        logs[data["config"]["name"]] = data
    return logs


def print_comparison(logs, target):
    print(f"\n=== {target} ===")
    print(f"{'experiment':30s} {'MAE':>8s} {'RMSE':>8s} {'Pearson r':>10s} {'Spearman rho':>13s}")
    for name, log in sorted(logs.items()):
        report = log["test_report"].get(target)
        if not report:
            continue
        print(f"{name:30s} {report['mae']:8.3f} {report['rmse']:8.3f} "
              f"{report['pearson_r']:10.3f} {report['spearman_rho']:13.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="experiments/*.json")
    args = parser.parse_args()

    logs = load_logs(args.pattern)
    if not logs:
        print("No experiment logs found. Run train_speech.py / train_visual.py / "
              "train_lstm.py / train_gru.py / train_transformer.py / train_multimodal.py first.")
        raise SystemExit(0)

    all_targets = sorted({t for log in logs.values() for t in log["test_report"]})
    for target in all_targets:
        print_comparison(logs, target)
