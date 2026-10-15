"""python -m experiments.q3_baseline；结果为实际运行数据。"""
import argparse
import csv
from dataclasses import asdict
from pathlib import Path
from statistics import median
from time import perf_counter
import platform

from experiments.q3_cases import ORDERS, official_tree, ordered_copy
from src.minimax import minimax, alphabeta


def run(repeats):
    rows = []
    source = official_tree()
    for order in ORDERS:
        began = perf_counter()
        root = ordered_copy(source, order)
        preparation_time = perf_counter() - began
        for algorithm in (minimax, alphabeta):
            value, stats = algorithm(root, return_stats=True)
            if value != 5:
                raise AssertionError(f"{algorithm.__name__}/{order}: {value} != 5")
            # 重复计时不累计节点数；并确认每次执行的逻辑统计不变。
            timings = []
            for _ in range(repeats):
                repeated_value, repeated = algorithm(root, return_stats=True)
                if (repeated_value, repeated.visited_nodes, repeated.evaluated_leaf_nodes,
                    repeated.prune_events, repeated.pruned_children) != (
                    value, stats.visited_nodes, stats.evaluated_leaf_nodes,
                    stats.prune_events, stats.pruned_children):
                    raise AssertionError("repeated execution changed logical result")
                timings.append(repeated.elapsed_time)
            rows.append(dict(algorithm=algorithm.__name__, order=order, best_value=value,
                             **asdict(stats), prune_count=stats.prune_count,
                             timing_repeats=repeats, median_elapsed_time=median(timings),
                             order_preparation_time=preparation_time))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=1000)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1]/"results")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    rows = run(args.repeats)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir/"q3_baseline.csv").open("w",encoding="utf-8",newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [f"Python {platform.python_version()}; official PDF tree; root MAX",
             "Single-run counts; prune_count=pruned_children; median timing excludes order preparation.",
             "Counts are visits, not distinct object identities; shared max2 is not cached."]
    for row in rows:
        lines.append(" | ".join(f"{key}={value}" for key,value in row.items()))
    text = "\n".join(lines) + "\n"
    (args.output_dir/"q3_baseline.txt").write_text(text,encoding="utf-8")
    print(text,end="")


if __name__ == "__main__":
    main()
