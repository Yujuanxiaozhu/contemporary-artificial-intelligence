"""Reproducible TF-IDF text classification experiment (CPU only)."""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "2")

import argparse
import hashlib
import json
import platform
import re
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parent
FEATURES = {
    "baseline": {},
    "bigrams": {"ngram_range": (1, 2)},
    "sublinear": {"sublinear_tf": True},
    "clean_headers": {"clean_headers": True},
    "combined": {"ngram_range": (1, 2), "sublinear_tf": True},
}


def clean_headers(text):
    """Remove a mail header only if its structure is recognized; keep Subject."""
    parts = re.split(r"\r?\n\s*\r?\n", text, maxsplit=1)
    if len(parts) != 2:
        return text
    header, body = parts
    if not re.search(r"(?im)^(from|subject|organization|lines):", header):
        return text
    subject = re.search(r"(?im)^subject:\s*(.*)", header)
    return ((subject.group(1) + "\n") if subject else "") + body


def make_vectorizer(feature):
    options = dict(FEATURES[feature])
    if options.pop("clean_headers", False):
        # Custom preprocessors replace sklearn's lowercase step.
        options["preprocessor"] = lambda s: clean_headers(s).lower()
    return TfidfVectorizer(max_features=20000, min_df=2, **options)


def make_model(name, value, seed):
    if name == "NB":
        return MultinomialNB(alpha=value)
    if name == "SVM":
        return LinearSVC(C=value, max_iter=5000, random_state=seed)
    return LogisticRegression(C=value, max_iter=2000, random_state=seed)


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate(texts, targets, train_idx, val_idx, model_name, value, feature, seed, stage, cache):
    if feature not in cache:
        start = time.perf_counter()
        vectorizer = make_vectorizer(feature)
        train_x = vectorizer.fit_transform(texts.iloc[train_idx])
        val_x = vectorizer.transform(texts.iloc[val_idx])
        cache[feature] = (vectorizer, train_x, val_x, time.perf_counter() - start)
    vectorizer, train_x, val_x, feature_seconds = cache[feature]
    model = make_model(model_name, value, seed)
    start = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(train_x, targets[train_idx])
    fit_seconds = time.perf_counter() - start
    start = time.perf_counter()
    pred = model.predict(val_x)
    predict_seconds = time.perf_counter() - start
    train_pred = model.predict(train_x)
    record = dict(stage=stage, seed=seed, model=model_name, parameter=float(value),
                  feature=feature, accuracy=accuracy_score(targets[val_idx], pred),
                  macro_f1=f1_score(targets[val_idx], pred, average="macro"),
                  train_accuracy=accuracy_score(targets[train_idx], train_pred),
                  fit_seconds=fit_seconds, predict_seconds=predict_seconds,
                  feature_seconds=feature_seconds, n_features=train_x.shape[1],
                  train_nnz=train_x.nnz,
                  warnings=[str(w.message) for w in caught])
    print(json.dumps(record, ensure_ascii=False), flush=True)
    return record, pred, model, vectorizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(args.data_dir / "train_data.csv")
    test = pd.read_csv(args.data_dir / "test_data_unlabeled.csv")
    if train.text.isna().any() or test.text.isna().any():
        raise ValueError("Missing text detected; decide a handling rule before fitting.")
    texts, targets = train.text.astype(str), train.target.to_numpy()
    assert set(targets) == set(range(10))
    audit = dict(train_rows=len(train), test_rows=len(test),
                 class_counts=train.target.value_counts().sort_index().to_dict(),
                 empty_train=int(texts.str.strip().eq("").sum()),
                 duplicate_train=int(texts.duplicated().sum()),
                 exact_train_test_overlap=len(set(texts) & set(test.text)),
                 data_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in args.data_dir.glob("*.csv")},
                 environment=dict(python=platform.python_version(), platform=platform.platform(),
                                  numpy=np.__version__, pandas=pd.__version__,
                                  sklearn=sklearn.__version__, scipy=scipy.__version__,
                                  matplotlib=matplotlib.__version__, cpu_count=os.cpu_count()),
                 selection_rule="Primary accuracy; secondary macro-F1. Seed 42 holdout is for selection, not an unbiased test.")
    save_json(out / "data_audit.json", audit)
    train_idx, val_idx = train_test_split(np.arange(len(train)), test_size=0.2,
                                        stratify=targets, random_state=42)
    pd.DataFrame({"row_index": np.arange(len(train)),
                  "split": np.where(np.isin(np.arange(len(train)), val_idx), "validation", "train")}).to_csv(out / "split_seed42.csv", index=False)
    records, cache, outputs = [], {}, {}

    def run(name, value, feature, stage):
        rec, pred, model, vec = evaluate(texts, targets, train_idx, val_idx,
                                         name, value, feature, 42, stage, cache)
        records.append(rec)
        outputs[(name, float(value), feature)] = (pred, model, vec)
        pd.DataFrame(records).to_csv(out / "experiments.csv", index=False)
        return rec

    for name in ("NB", "SVM", "LR"):
        for value in (0.1, 1.0, 10.0):
            run(name, value, "baseline", "model_parameter")
    key = lambda r: (r["accuracy"], r["macro_f1"])
    baseline = max(records, key=key)
    for feature in ("bigrams", "sublinear", "clean_headers", "combined"):
        run(baseline["model"], baseline["parameter"], feature, "feature_ablation")
    best = max(records, key=key)
    # Check two preselected configurations on alternate splits; do not tune on them.
    sensitivity = []
    candidates = {(r["model"], r["parameter"], r["feature"]) for r in (baseline, best)}
    for seed in (17, 2026):
        ti, vi = train_test_split(np.arange(len(train)), test_size=0.2,
                                 stratify=targets, random_state=seed)
        seed_cache = {}
        for name, value, feature in sorted(candidates):
            rec, _, _, _ = evaluate(texts, targets, ti, vi, name, value, feature,
                                    seed, "split_sensitivity", seed_cache)
            sensitivity.append(rec)
    pd.DataFrame(sensitivity).to_csv(out / "sensitivity.csv", index=False)
    save_json(out / "selection.json", {"baseline": baseline, "selected": best,
                                     "train_rows": len(train_idx), "validation_rows": len(val_idx)})
    pred, selected_model, selected_vec = outputs[(best["model"], best["parameter"], best["feature"])]
    save_json(out / "classification_report.json", classification_report(targets[val_idx], pred, output_dict=True))
    cm = confusion_matrix(targets[val_idx], pred, labels=range(10))
    pd.DataFrame(cm, index=range(10), columns=range(10)).to_csv(out / "confusion_matrix.csv")
    pd.DataFrame({"row_index": val_idx, "true": targets[val_idx], "predicted": pred}).to_csv(out / "validation_predictions.csv", index=False)
    wrong = pred != targets[val_idx]
    pd.DataFrame({"row_index": val_idx[wrong], "true": targets[val_idx][wrong],
                  "predicted": pred[wrong], "text": texts.iloc[val_idx[wrong]].to_numpy()}).to_csv(out / "errors.csv", index=False)
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, cmap="Blues")
    for i in range(10):
        for j in range(10):
            ax.text(j, i, str(cm[i,j]), ha="center", va="center", fontsize=7,
                    color="white" if cm[i,j] > cm.max() / 2 else "black")
    ax.set(xticks=range(10), yticks=range(10), xlabel="Predicted label", ylabel="True label")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(out / "confusion_matrix.png", dpi=200)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(5.5, 3.3))
    for name in ("NB", "SVM", "LR"):
        rs = [r for r in records if r["stage"] == "model_parameter" and r["model"] == name]
        ax.plot([r["parameter"] for r in rs], [r["accuracy"] * 100 for r in rs], marker="o", label=name)
    ax.set_xscale("log")
    ax.set(xlabel="alpha (NB) / C (SVM, LR)", ylabel="Validation accuracy (%)")
    ax.legend(); ax.grid(alpha=0.2); fig.tight_layout()
    fig.savefig(out / "parameter_comparison.png", dpi=200)
    plt.close(fig)
    # Refit vocabulary, IDF, and classifier using all labeled data only after selection.
    vectorizer = make_vectorizer(best["feature"])
    full_x = vectorizer.fit_transform(texts)
    test_x = vectorizer.transform(test.text.astype(str))
    final_model = make_model(best["model"], best["parameter"], 42)
    start = time.perf_counter()
    final_model.fit(full_x, targets)
    final_fit_seconds = time.perf_counter() - start
    predictions = final_model.predict(test_x)
    assert len(predictions) == len(test) and set(predictions).issubset(set(range(10)))
    pd.Series(predictions).to_csv(out / "prediction.csv", index=False, header=False)
    # Model persistence is optional; the code reproduces predictions from the original CSVs.
    save_json(out / "final_training.json", dict(fit_seconds=final_fit_seconds,
              n_features=full_x.shape[1], prediction_rows=len(predictions),
              prediction_counts=pd.Series(predictions).value_counts().sort_index().to_dict(),
              prediction_sha256=hashlib.sha256((out / "prediction.csv").read_bytes()).hexdigest()))
    print("DONE: results saved to", out, flush=True)


if __name__ == "__main__":
    main()
