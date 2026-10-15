"""python -m experiments.q4_baseline：距离一次预计算，全部搜索只查表。"""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import platform
from statistics import median

from experiments.q4_cases import Q4_GRID, Q4_LANDMARKS, Q4_VALUES
from experiments.q4_reference import dijkstra_distance
from src.treasure_game import (ACTION_ORDERS, TreasureGame, precompute_distances,
                               minimax_treasure, alphabeta_treasure)


def write_csv(path, rows, fields=None):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repeats',type=int,default=1000)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'results')
    args=parser.parse_args()
    if args.repeats<1:
        parser.error('--repeats must be positive')
    output=args.output_dir
    output.mkdir(parents=True,exist_ok=True)
    # 全部实验组与重复计时共用这一次生成的矩阵。
    table=precompute_distances(Q4_GRID,Q4_LANDMARKS)
    verification=[]
    for i,source in enumerate(table.labels):
        for j,target in enumerate(table.labels):
            oracle=dijkstra_distance(Q4_GRID,Q4_LANDMARKS[source],Q4_LANDMARKS[target])
            computed=table.matrix[i][j]
            if computed!=oracle:
                raise AssertionError(f'{source}->{target}: A*={computed}, Dijkstra={oracle}')
            verification.append(dict(source=source,target=target,astar_distance=computed,
                                     dijkstra_distance=oracle,match=True,**asdict(table.pair_stats[i][j])))
    write_csv(output/'q4_astar_pairs.csv',verification)
    matrix_rows=[dict(source=source,**dict(zip(table.labels,table.matrix[i])))
                 for i,source in enumerate(table.labels)]
    write_csv(output/'q4_distance_matrix.csv',matrix_rows)
    matrix_text='row/column order: '+', '.join(table.labels)+'\n'
    matrix_text+='source '+' '.join(f'{label:>4}' for label in table.labels)+'\n'
    for label,row in zip(table.labels,table.matrix):
        matrix_text+=f'{label:>6} '+' '.join(f'{v:>4}' for v in row)+'\n'
    matrix_text+=f'A* / independent Dijkstra verified: {len(verification)}/36 pairs\n'
    matrix_text+=f'distance_precomputation_time={table.distance_precomputation_time:.12f} s\n'
    (output/'q4_distance_matrix.txt').write_text(matrix_text,encoding='utf-8')
    game=TreasureGame(table,Q4_VALUES)
    rows=[]
    for depth in (2,4):
        for order in ACTION_ORDERS:
            plain=minimax_treasure(game,depth,order=order)
            for algorithm in (minimax_treasure,alphabeta_treasure):
                result,stats=algorithm(game,depth,order=order,return_stats=True)
                if result!=plain:
                    raise AssertionError('Minimax and Alpha-Beta disagree on official unique optimum')
                counts=(stats.visited_nodes,stats.evaluated_leaf_nodes,stats.prune_events,stats.pruned_children)
                timings=[]
                for _ in range(args.repeats):
                    repeated,repeated_stats=algorithm(game,depth,order=order,return_stats=True)
                    if repeated!=result or (repeated_stats.visited_nodes,repeated_stats.evaluated_leaf_nodes,
                         repeated_stats.prune_events,repeated_stats.pruned_children)!=counts:
                        raise AssertionError('repeated execution changed result or logical node counts')
                    timings.append(repeated_stats.elapsed_time)
                rows.append(dict(depth=depth,algorithm=algorithm.__name__,order=order,
                                 **result,**asdict(stats),prune_count=stats.prune_count,
                                 timing_repeats=args.repeats,median_elapsed_time=median(timings)))
    write_csv(output/'q4_baseline.csv',rows)
    metadata=dict(python_version=platform.python_version(),landmark_order=table.labels,
                  distance_precomputation_time=table.distance_precomputation_time,
                  independently_verified_pairs=len(verification),astar_calls_for_precomputation=36,
                  timing_repeats=args.repeats,game_timing_includes_practical_sort=True,
                  game_timing_includes_astar=False)
    (output/'q4_run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    text=f'Python {platform.python_version()}\n'+matrix_text
    text+='Counts are from one execution; timings include action sorting, exclude distance precomputation.\n'
    text+='prune_count=pruned_children; only actual skipped children count as cutoff events.\n'
    for row in rows:
        text+=' | '.join(f'{key}={value}' for key,value in row.items())+'\n'
    (output/'q4_baseline.txt').write_text(text,encoding='utf-8')
    print(text,end='')


if __name__=='__main__':
    main()
