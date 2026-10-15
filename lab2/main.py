"""运行官方样例；--csv 可选保存内部基线数据。"""
import argparse
import csv
from dataclasses import asdict
from pathlib import Path
import platform

from experiments.cases import Q1_START, Q1_GOAL, Q1_GRID, Q2_START, Q2_GOAL, Q2_GRID
from src.astar import astar_maze, astar_weighted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", choices=("1", "2", "all"), default="all")
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    rows = []
    print("Python", platform.python_version())
    if args.question in ("1", "all"):
        for heuristic in ("zero", "manhattan"):
            path, stats = astar_maze(Q1_START, Q1_GOAL, Q1_GRID, heuristic, return_stats=True)
            cost = len(path) - 1 if path else -1
            print(f"Q1 {heuristic}: cost={cost}, coordinates={len(path)}, path={path}")
            print(asdict(stats))
            rows.append(dict(question=1, heuristic=heuristic, solution_cost=cost,
                             path_coordinates=len(path), **asdict(stats)))
    if args.question in ("2", "all"):
        for heuristic in ("zero", "admissible"):
            cost, stats = astar_weighted(Q2_START, Q2_GOAL, Q2_GRID, heuristic, return_stats=True)
            print(f"Q2 {heuristic}: minimum_cost={cost}")
            print(asdict(stats))
            rows.append(dict(question=2, heuristic=heuristic, solution_cost=cost,
                             path_coordinates="", **asdict(stats)))
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
