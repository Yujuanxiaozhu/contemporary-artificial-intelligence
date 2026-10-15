"""阶段4正式实验，原始输入、计时和摘要写入独立report_data目录。"""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import platform
from statistics import median,mean,quantiles
from time import perf_counter

from experiments.cases import Q1_GRID,Q1_START,Q1_GOAL,Q2_GRID,Q2_START,Q2_GOAL
from experiments.q3_cases import official_tree,ordered_copy,ORDERS
from experiments.q4_cases import Q4_GRID,Q4_LANDMARKS,Q4_VALUES
from experiments.q4_reference import verify_distances
from experiments.report_support import (bfs_reference,weighted_reference,validate_path,
    generate_maps,measure_methods,full_tree,exhaustive_value,cache_callables)
from src.astar import astar_maze,astar_weighted
from src.minimax import minimax,alphabeta
from src.treasure_game import precompute_distances,TreasureGame,minimax_treasure,alphabeta_treasure


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=True,indent=2),encoding='utf-8')


def timing_rows(case,mode,samples):
    return [dict(case=case,method=mode,repetition=i,elapsed_time=t) for i,t in enumerate(samples)]


def aggregate(rows):
    grouped={}
    for row in rows:
        grouped.setdefault((row['group'],row['heuristic']),[]).append(row)
    output=[]
    for (group,heuristic),values in grouped.items():
        expanded=[r['expanded_nodes'] for r in values]
        iqr=quantiles(expanded,n=4,method='inclusive') if len(expanded)>1 else [expanded[0]]*3
        output.append(dict(group=group,heuristic=heuristic,instance_count=len(values),
            mean_solution_cost=mean(r['solution_cost'] for r in values),
            median_solution_cost=median(r['solution_cost'] for r in values),
            median_expanded_nodes=median(expanded),min_expanded_nodes=min(expanded),
            max_expanded_nodes=max(expanded),expanded_q1=iqr[0],expanded_q3=iqr[2],
            median_generated_nodes=median(r['generated_nodes'] for r in values),
            median_elapsed_time=median(r['median_elapsed_time'] for r in values)))
    return output


def grid_experiments(output,question,repeats):
    weighted=question==2
    configs=([(20,.2),(40,.2),(80,.2),(40,.1),(40,.3)] if not weighted else [(20,.2),(40,.2)])
    base_seed=20261115 if weighted else 20261015
    official=dict(seed=None,grid=Q2_GRID if weighted else Q1_GRID,
                  start=Q2_START if weighted else Q1_START,goal=Q2_GOAL if weighted else Q1_GOAL)
    official['oracle_cost']=(weighted_reference if weighted else bfs_reference)(
        official['grid'],official['start'],official['goal'])
    official['actual_obstacle_density']=sum(v=='X' for row in official['grid'] for v in row)/(len(official['grid'])*len(official['grid'][0])-2)
    datasets=[('official',0,official)]
    attempts=[]
    for config_index,(size,density) in enumerate(configs):
        group=f'{size}x{size}_p{int(density*100)}'
        accepted,history=generate_maps(size,density,10,base_seed+config_index*10000,weighted)
        for item in history:
            attempts.append(dict(group=group,**item))
        for instance,item in enumerate(accepted):
            datasets.append((group,instance,item))
        print(f'Q{question} generated {group}: accepted=10, attempts={len(history)}',flush=True)
    rows,timings,inputs=[],[],[]
    function=astar_weighted if weighted else astar_maze
    modes=('zero','admissible') if weighted else ('zero','manhattan')
    for group,instance,item in datasets:
        case=f'{group}_{instance}'
        grid,start,goal=item['grid'],tuple(item['start']),tuple(item['goal'])
        methods={mode:(lambda mode=mode: function(start,goal,grid,mode,return_stats=True)) for mode in modes}
        measured,samples=measure_methods(methods,repeats)
        for mode,(result,stats) in measured.items():
            cost=result if weighted else len(result)-1
            if cost!=item['oracle_cost']:
                raise AssertionError(f'Q{question}/{case}/{mode}: oracle mismatch')
            if not weighted:
                validate_path(result,grid,start,goal,item['oracle_cost'])
            rows.append(dict(group=group,instance=instance,seed=item['seed'],heuristic=mode,
                solution_cost=cost,oracle_cost=item['oracle_cost'],expanded_nodes=stats.expanded_nodes,
                generated_nodes=stats.generated_nodes,median_elapsed_time=median(samples[mode]),
                timing_repeats=repeats,actual_obstacle_density=item['actual_obstacle_density']))
            timings.extend(timing_rows(case,mode,samples[mode]))
        inputs.append(dict(group=group,instance=instance,**item))
    folder=output/f'q{question}'
    write_csv(folder/'instances.csv',rows)
    write_csv(folder/'summary.csv',aggregate(rows))
    write_csv(folder/'timings.csv',timings)
    write_csv(folder/'generation_attempts.csv',attempts)
    write_json(folder/'inputs.json',inputs)
    print(f'Q{question} completed: {len(datasets)} inputs, {len(rows)} algorithm rows',flush=True)


def tree_experiments(output,repeats,prep_repeats):
    cases=[('official',official_tree(),None,None)]
    inputs=[]
    def serialize(node):
        return {'children':[serialize(c) for c in node.children]} if node.children else {'value':node.value}
    for depth in (4,6):
        seed=20261215+depth
        tree=full_tree(3,depth,seed)
        cases.append((f'b3_d{depth}',tree,depth,seed))
        inputs.append(dict(case=f'b3_d{depth}',branching=3,depth=depth,seed=seed,tree=serialize(tree)))
    rows,timings,prep_raw=[],[],[]
    for name,source,depth,seed in cases:
        expected=exhaustive_value(source)
        methods={}
        preparation={}
        for order in ORDERS:
            times=[]
            for i in range(prep_repeats):
                began=perf_counter()
                copied=ordered_copy(source,order)
                elapsed=perf_counter()-began
                times.append(elapsed)
                prep_raw.append(dict(case=name,order=order,repetition=i,elapsed_time=elapsed))
            preparation[order]=median(times)
            for algorithm in (minimax,alphabeta):
                methods[f'{algorithm.__name__}:{order}']=(lambda algorithm=algorithm,copied=copied: algorithm(copied,return_stats=True))
        measured,samples=measure_methods(methods,repeats)
        plain_counts=set()
        for key,(result,stats) in measured.items():
            algorithm,order=key.split(':')
            if result!=expected:
                raise AssertionError(f'Q3 {name}/{key}: mismatch')
            if algorithm=='minimax':
                plain_counts.add((stats.visited_nodes,stats.evaluated_leaf_nodes))
            rows.append(dict(case=name,branching='' if depth is None else 3,depth=depth,seed=seed,
                algorithm=algorithm,order=order,best_value=result,**{k:v for k,v in asdict(stats).items() if k!='elapsed_time'},
                median_elapsed_time=median(samples[key]),timing_repeats=repeats,
                median_order_preparation_time=preparation[order],preparation_repeats=prep_repeats,
                oracle_ordering=order!='original'))
            timings.extend(timing_rows(name,key,samples[key]))
        if len(plain_counts)!=1:
            raise AssertionError('Minimax work changed across ordering')
        if depth is not None and plain_counts!={((3**(depth+1)-1)//2,3**depth)}:
            raise AssertionError('full tree count mismatch')
        print(f'Q3 completed {name}, value={expected}',flush=True)
    write_csv(output/'q3/results.csv',rows)
    write_csv(output/'q3/timings.csv',timings)
    write_csv(output/'q3/preparation_timings.csv',prep_raw)
    write_json(output/'q3/custom_trees.json',inputs)


def decision_branches(game):
    rows=[]
    initial=game.initial_state()
    for first in game.treasure_order:
        for depth in (2,4):
            state=game.transition(initial,first)
            value=minimax_treasure(game,depth-1,state)['best_value']
            trace=[dict(player='A',target=first,gain=game.gain(initial,first),
                        score_a=state.score_a,score_b=state.score_b,utility=state.utility)]
            for remaining in range(depth-1,0,-1):
                if not state.remaining_treasures:
                    break
                target=minimax_treasure(game,remaining,state)['best_target']
                step=dict(player=state.current_player,target=target,gain=game.gain(state,target))
                state=game.transition(state,target)
                trace.append(dict(step,score_a=state.score_a,score_b=state.score_b,utility=state.utility))
            if state.utility!=value:
                raise AssertionError('principal variation does not yield branch minimax value')
            rows.append(dict(first_move=first,depth=depth,initial_gain=trace[0]['gain'],
                             best_min_response=trace[1]['target'],minimax_value=value,
                             principal_variation=json.dumps(trace)))
    return rows


def game_experiments(output,repeats,cache_repeats):
    table=precompute_distances(Q4_GRID,Q4_LANDMARKS)
    if verify_distances(table,Q4_GRID,Q4_LANDMARKS)!=36:
        raise AssertionError('matrix validation incomplete')
    game=TreasureGame(table,Q4_VALUES)
    methods={}
    for depth in (2,4):
        methods[f'{depth}:minimax:original']=(lambda depth=depth: minimax_treasure(game,depth,return_stats=True))
        for order in ('original','practical','unfavorable'):
            methods[f'{depth}:alphabeta:{order}']=(lambda depth=depth,order=order: alphabeta_treasure(game,depth,order=order,return_stats=True))
    measured,samples=measure_methods(methods,repeats)
    rows,timings=[],[]
    for key,(result,stats) in measured.items():
        depth,algorithm,order=key.split(':')
        expected={'best_target':'T2','best_value':-1} if depth=='2' else {'best_target':'T3','best_value':3}
        if result!=expected:
            raise AssertionError('Q4 official hard requirement failed')
        rows.append(dict(depth=int(depth),algorithm=algorithm,order=order,**result,
            **{k:v for k,v in asdict(stats).items() if k!='elapsed_time'},
            median_elapsed_time=median(samples[key]),timing_repeats=repeats))
        timings.extend(timing_rows('official',key,samples[key]))
    write_csv(output/'q4/results.csv',rows)
    write_csv(output/'q4/timings.csv',timings)
    write_csv(output/'q4/decision_branches.csv',decision_branches(game))
    write_json(output/'q4/distance_matrix.json',dict(labels=table.labels,matrix=table.matrix,verified_pairs=36))
    prep_times=[]
    for i in range(cache_repeats):
        prepared=precompute_distances(Q4_GRID,Q4_LANDMARKS)
        if prepared.matrix!=table.matrix:
            raise AssertionError('repeated precomputation changed matrix')
        prep_times.append(dict(repetition=i,elapsed_time=prepared.distance_precomputation_time))
    write_csv(output/'q4/precomputation_timings.csv',prep_times)
    cache_measured,cache_samples=measure_methods(cache_callables(table,Q4_GRID,Q4_LANDMARKS,Q4_VALUES),cache_repeats)
    cache_rows,cache_timings=[],[]
    for mode,(result,stats) in cache_measured.items():
        if (result['best_target'],result['best_value'],stats.visited_nodes,stats.evaluated_leaf_nodes)!=('T3',3,65,24):
            raise AssertionError('cache reference changed game result or traversal')
        cache_rows.append(dict(mode=mode,depth=4,algorithm='minimax',order='original',**result,
            **{k:v for k,v in asdict(stats).items() if k!='elapsed_time'},
            median_elapsed_time=median(cache_samples[mode]),timing_repeats=cache_repeats))
        cache_timings.extend(timing_rows('H4_minimax_original',mode,cache_samples[mode]))
    write_csv(output/'q4/cache_comparison.csv',cache_rows)
    write_csv(output/'q4/cache_timings.csv',cache_timings)
    write_json(output/'q4/precomputation.json',dict(single_precomputation_time=table.distance_precomputation_time,
        median_precomputation_time=median(r['elapsed_time'] for r in prep_times),repeats=cache_repeats,
        astar_calls=len(table.labels)**2,astar_expanded=sum(s.expanded_nodes for row in table.pair_stats for s in row),
        astar_generated=sum(s.generated_nodes for row in table.pair_stats for s in row)))
    print('Q4 official decisions, 8 formal groups, decision traces and cache comparison completed',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--map-repeats',type=int,default=31)
    parser.add_argument('--search-repeats',type=int,default=1001)
    parser.add_argument('--cache-repeats',type=int,default=101)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'results/report_data')
    args=parser.parse_args()
    if min(args.map_repeats,args.search_repeats,args.cache_repeats)<1:
        parser.error('all repeat counts must be positive')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    write_json(args.output_dir/'run_config.json',dict(python_version=platform.python_version(),
        map_repeats=args.map_repeats,search_repeats=args.search_repeats,cache_repeats=args.cache_repeats,
        map_instances_per_group=10,q1_seed_base=20261015,q2_seed_base=20261115,
        q3_seeds={'b3_d4':20261219,'b3_d6':20261221},
        measurement='single-run logical counts; two warmups; cyclic interleaving; median repeated internal elapsed_time',
        one_shot_cache_measurement='external timer includes matrix build + game construction + one search',
        sampling='IID obstacles except forced open endpoints; reject unreachable; no route carving',
        plots=False,matplotlib='not installed; no dependency installation'))
    print('Python',platform.python_version(),flush=True)
    grid_experiments(args.output_dir,1,args.map_repeats)
    grid_experiments(args.output_dir,2,args.map_repeats)
    tree_experiments(args.output_dir,args.search_repeats,args.map_repeats)
    game_experiments(args.output_dir,args.search_repeats,args.cache_repeats)
    print('All measured decisions/costs/counts validated. Raw data saved.',flush=True)


if __name__=='__main__':
    main()
