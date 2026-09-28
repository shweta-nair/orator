"""Evaluation metrics for spec section 22. Pure numpy — no torch dependency,
so this half of the pipeline is testable without installing a DL framework."""
import numpy as np


def mae(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def pearson_r(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if np.std(y_true) == 0 or np.std(y_pred) == 0:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def _rank(a):
    order = np.argsort(a)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(a))
    return ranks


def spearman_rho(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    return pearson_r(_rank(y_true), _rank(y_pred))


def classification_report_basic(y_true, y_pred, positive_label=1):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    tp = np.sum((y_pred == positive_label) & (y_true == positive_label))
    fp = np.sum((y_pred == positive_label) & (y_true != positive_label))
    fn = np.sum((y_pred != positive_label) & (y_true == positive_label))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = float(np.mean(y_true == y_pred))
    return {"accuracy": accuracy, "precision": float(precision), "recall": float(recall), "f1": float(f1)}


def regression_report(y_true, y_pred):
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "pearson_r": pearson_r(y_true, y_pred),
        "spearman_rho": spearman_rho(y_true, y_pred),
    }


if __name__ == "__main__":
    y_true = [1, 2, 3, 4, 5]
    y_pred = [1.1, 2.2, 2.7, 4.4, 4.8]
    print(regression_report(y_true, y_pred))
