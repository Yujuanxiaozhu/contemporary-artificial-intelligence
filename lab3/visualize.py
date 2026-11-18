"""Render the CIFAR-10 experiment report from saved training and test results."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator, PercentFormatter

RUNS = ("baseline", "augmented")
COLORS = ("#225f9c", "#b34b19")
METRICS = ("train_loss", "train_acc", "val_loss", "val_acc", "lr")
FIGURE_WIDTH = 180 / 25.4  # inches; avoid tight cropping so the print width stays fixed


def read_history(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = sorted(csv.DictReader(file), key=lambda row: int(row["epoch"]))
    epochs = [int(row["epoch"]) for row in rows]
    if not epochs or len(set(epochs)) != len(epochs):
        raise ValueError(f"Expected a nonempty history with unique epochs in {path}")
    return epochs, {metric: [float(row[metric]) for row in rows] for metric in METRICS}


def save_figure(fig, path):
    try:
        fig.savefig(path, dpi=250, facecolor="white")
    finally:
        plt.close(fig)


def plot_curves(run_dir):
    histories = [read_history(run_dir / run / "history.csv") for run in RUNS]
    epochs = histories[0][0]
    if epochs != histories[1][0]:
        raise ValueError("Baseline and augmented histories must contain the same epochs")

    fig, axes = plt.subplots(2, 2, figsize=(FIGURE_WIDTH, 4.4), sharex=True)
    titles = ("Training loss", "Training accuracy", "Validation loss", "Validation accuracy")
    for ax, metric, title in zip(axes.flat, METRICS[:4], titles):
        for run, color, style, (_, values) in zip(RUNS, COLORS, ("-", "--"), histories):
            ax.plot(epochs, values[metric], color=color, linestyle=style,
                    linewidth=1.6, marker="o" if len(epochs) == 1 else None,
                    label=run.capitalize())
        ax.set_title(title, loc="left", fontsize=10, fontweight="bold")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=7, integer=True))
        ax.tick_params(labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        if metric.endswith("acc"):
            ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    for ax in axes[-1]:
        ax.set_xlabel("Epoch", fontsize=9)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92), pad=1.0)
    save_figure(fig, run_dir / "curves.png")


def plot_confusion(run_dir, result):
    classes = result["classes"]
    counts = np.asarray(result["confusion"], dtype=int)
    totals = counts.sum(axis=1, keepdims=True)
    fractions = np.divide(counts, totals, out=np.zeros_like(counts, dtype=float),
                          where=totals != 0)

    fig, (ax, bars) = plt.subplots(1, 2, figsize=(FIGURE_WIDTH, 4.0),
                                  gridspec_kw={"width_ratios": (3.05, 1.25)})
    fig.suptitle(f"Test results — {result['selected'].capitalize()}  |  "
                 f"Accuracy {result['test_acc']:.1%}  ·  Loss {result['test_loss']:.4f}",
                 fontsize=11, fontweight="bold")
    positions = np.arange(len(classes))
    ax.imshow(fractions, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for true, pred in np.ndindex(counts.shape):
        if counts[true, pred]:
            value = fractions[true, pred]
            ax.text(pred, true, str(counts[true, pred]), ha="center", va="center",
                    color="white" if value > 0.57 else "#111111", fontsize=7)
    ax.set_title("Confusion matrix (counts; shading normalized by row)", fontsize=9)
    ax.set_xticks(positions, classes, rotation=45, ha="right")
    ax.set_yticks(positions, classes)
    ax.set_xlabel("Predicted class", fontsize=9)
    ax.set_ylabel("True class", fontsize=9)
    ax.tick_params(length=0, labelsize=8)

    acc = np.asarray(result["per_class_acc"], dtype=float)
    bars.barh(positions, acc, color=COLORS[0], height=0.63)
    for i, value in enumerate(acc):
        bars.text(value + 0.025, i, f"{value:.1%}", va="center", fontsize=7)
    bars.set_title("Per-class accuracy", fontsize=9)
    bars.set_ylim(ax.get_ylim())
    bars.set_xlim(0, 1.25)
    bars.set_yticks([])
    bars.set_xticks([0, 0.5, 1], ["0%", "50%", "100%"])
    bars.tick_params(axis="x", labelsize=8)
    bars.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout(rect=(0, 0, 1, 0.93), w_pad=1.2)
    # Align bar rows with the heatmap rows, accounting for rotated x labels.
    left = ax.get_position()
    right = bars.get_position()
    bars.set_position([right.x0, left.y0, right.width, left.height])
    save_figure(fig, run_dir / "confusion.png")


def select_examples(errors):
    groups = defaultdict(list)
    for item in errors:
        groups[item["true"], item["pred"]].append(item)
    pairs = sorted(groups, key=lambda pair: (-len(groups[pair]), pair))[:3]
    selected = []
    for pair in pairs:
        records = sorted(groups[pair], key=lambda item: (-item["confidence"], item["index"]))
        # For an even count use the lower-confidence of the two middle samples.
        examples = [("Highest", records[0])]
        if len(records) > 1:
            examples.append(("Median", records[len(records) // 2]))
        selected.append((pair, len(records), examples))
    return selected


def plot_errors(run_dir, data_dir, result):
    selected = select_examples(result["errors"])
    if not selected:
        fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, 1.4))
        ax.axis("off")
        ax.text(0.5, 0.5, "No test misclassifications", ha="center", va="center", fontsize=11)
        shown = []
    else:
        # Load only the original test images. No checkpoint, augmentation or downloads.
        from torchvision.datasets import CIFAR10

        dataset = CIFAR10(root=str(data_dir), train=False, download=False)
        classes = result["classes"]
        height = 1.24 * len(selected) + 0.48
        fig, axes = plt.subplots(len(selected), 2, figsize=(FIGURE_WIDTH, height),
                                 squeeze=False, gridspec_kw={"wspace": 0.10, "hspace": 0.5})
        fig.suptitle("Most frequent test errors (true → predicted)", fontsize=11, fontweight="bold")
        fig.subplots_adjust(left=0.05, right=0.95, bottom=0.06 / height, top=1 - 0.62 / height)
        shown = []
        for row, ((true, pred), count, examples) in enumerate(selected):
            for column, ax in enumerate(axes[row]):
                ax.set_axis_off()
                if column >= len(examples):
                    continue
                label, item = examples[column]
                image, target = dataset[item["index"]]
                if target != true:
                    raise ValueError(f"Test label disagrees with test.json at index {item['index']}")
                ax.imshow(image, interpolation="nearest")
                ax.set_title(f"{classes[true]} → {classes[pred]} ({count})\n"
                             f"{label}: {item['confidence']:.1%}", fontsize=8, pad=3)
                shown.append(item)
    save_figure(fig, run_dir / "errors.png")
    (run_dir / "error_examples.json").write_text(
        json.dumps(shown, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="Directory containing both runs and test.json")
    parser.add_argument("--data-dir", required=True, type=Path, help="CIFAR-10 dataset root used for test evaluation")
    args = parser.parse_args()
    with (args.run_dir / "test.json").open(encoding="utf-8") as file:
        result = json.load(file)
    plot_curves(args.run_dir)
    plot_confusion(args.run_dir, result)
    plot_errors(args.run_dir, args.data_dir, result)


if __name__ == "__main__":
    main()
