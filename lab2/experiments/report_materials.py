"""正式实验：由真实CSV整理事实素材，不编写最终报告。"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from src.astar import astar_weighted, weighted_lower_bound
from src.treasure_game import DistanceTable,TreasureGame,minimax_treasure
from experiments.q4_cases import Q4_VALUES
from experiments.report_support import weighted_reference


def load(path):
    with path.open(encoding='utf-8') as f:
        return list(csv.DictReader(f))


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8')


def grids(rows):
    return table(['组','h','n','cost mean/median','expanded median [min,max]','expanded IQR','generated median','time median(ms)'],[
        [r['group'],r['heuristic'],r['instance_count'],f"{float(r['mean_solution_cost']):g}/{float(r['median_solution_cost']):g}",
         f"{float(r['median_expanded_nodes']):g} [{r['min_expanded_nodes']},{r['max_expanded_nodes']}]",
         f"[{float(r['expanded_q1']):g},{float(r['expanded_q3']):g}]",r['median_generated_nodes'],
         f"{float(r['median_elapsed_time'])*1000:.6f}"] for r in rows])


def games(rows):
    return table(['H','算法','顺序','首步/U','visited','leaf','events','pruned children','median(ms)'],[
        [r['depth'],r['algorithm'],r['order'],r['best_target']+'/'+r['best_value'],r['visited_nodes'],
         r['evaluated_leaf_nodes'],r['prune_events'],r['pruned_children'],
         f"{float(r['median_elapsed_time'])*1000:.6f}"] for r in rows])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[1]/'results/report_data')
    args=parser.parse_args()
    data=args.data_dir
    root=Path(__file__).resolve().parents[1]
    q1=load(data/'q1/summary.csv');q2=load(data/'q2/summary.csv')
    q3=load(data/'q3/results.csv');q4=load(data/'q4/results.csv')
    cache=load(data/'q4/cache_comparison.csv')
    prep=json.loads((data/'q4/precomputation.json').read_text(encoding='utf-8'))
    reductions=[]
    for question,rows in ((1,q1),(2,q2)):
        for group in sorted({r['group'] for r in rows}):
            pair=[r for r in rows if r['group']==group]
            zero=next(r for r in pair if r['heuristic']=='zero')
            informed=next(r for r in pair if r['heuristic']!='zero')
            percent=(1-float(informed['median_expanded_nodes'])/float(zero['median_expanded_nodes']))*100
            reductions.append([question,group,zero['median_expanded_nodes'],informed['median_expanded_nodes'],f'{percent:.2f}%'])
    reduction_table=table(['题','组','zero expanded median','heuristic expanded median','中位数之比的下降'],reductions)
    grid_method='''数据生成不计时。每组10张可达图，先独立求最优值；无解图记录并拒绝，不挖通道路。
每实例31次计时取median，组内时间为10个实例median的median。节点先取单次执行数，再在10实例上汇总，小数中位数不代表访问了半个节点。
IQR为实例节点数的25%/75%分位（inclusive）。官方样例单列，n=1。

'''
    write(data/'q1/summary.md','# Q1 正式实验素材\n\n'+grid_method+grids(q1)+'''

五组共50张随机可达图，另有官方图。全部与独立BFS费用一致，路径合法性也检查。
完整输入见inputs.json，接受/拒绝记录见generation_attempts.csv，每次时间见timings.csv。
不能把不同地图组的差异理解为仅由尺寸或障碍密度单独造成。
''')
    example_grid=[[3,3,'E']];node=(0,1);goal=(0,2)
    actual=weighted_reference(example_grid,node,goal)
    values={h:astar_weighted(node,goal,example_grid,h) for h in ('zero','admissible')}
    safe=weighted_lower_bound(node,goal,3)
    if actual!=0 or set(values.values())!={0} or safe!=0:
        raise AssertionError('E=0 counterexample validation failed')
    write(data/'q2/heuristic_counterexample.json',json.dumps(dict(grid=example_grid,start=[0,0],node=node,goal=goal,
        min_weight=3,plain_manhattan_bound=3,true_remaining_cost=actual,safe_bound=safe,algorithm_results=values),indent=2))
    admissibility='''## E=0示例与下界解释

网格[3,3,E]，起点(0,0)，观察n=(0,1)，终点(0,2)。n只距E一步，真实剩余费用0；普通Manhattan×最小普通权值=1×3=3，高估。
修正后max(1−1,0)×3=0，两算法和独立Dijkstra实际都返回剩余费用0，见heuristic_counterexample.json。

离终点距离d的路径至少d步，最后进入E免费，其余至少d−1步进入普通地形，每步至少m，所以max(d−1,0)×m是安全下界。
障碍只会增加步数；有零权普通格时m=0，不能仅取最小正权。搜索不重返起点的非负环，避免假设S的重入费用。
'''
    write(data/'q2/summary.md','# Q2 正式实验素材\n\n'+grid_method+grids(q2)+'''

两组共20张随机可达图，权值1–9、目标障碍概率20%，全部独立Dijkstra费用一致，官方结果仍为7。
本批启发式仅少量减少expanded，时间median反而更高，generated也更高。generated是入堆次数，包含g改善的重入堆，不是唯一坐标数。

'''+admissibility)
    tree_table=table(['输入','算法','顺序','value','visited','leaf','events','pruned children','median(ms)','准备median(ms)'],[
        [r['case'],r['algorithm'],r['order'],r['best_value'],r['visited_nodes'],r['evaluated_leaf_nodes'],r['prune_events'],
         r['pruned_children'],f"{float(r['median_elapsed_time'])*1000:.6f}",f"{float(r['median_order_preparation_time'])*1000:.6f}"] for r in q3])
    write(data/'q3/summary.md','# Q3 正式剪枝素材\n\n'+tree_table+'''

搜索1001次取median；复制/排序准备31次取median，排除在搜索时间外，original也有复制成本。
favorable/unfavorable均使用完整Minimax值进行正/反排序，属于oracle/theoretical对照，不是免费实际优化。
完整三叉树depth=4有121节点/81叶，depth=6有1093节点/729叶；同树Minimax三顺序访问数相同。
depth=6的Alpha-Beta原顺序359次、oracle较优125次、不利1011次。不利顺序仍可能发生剪枝。
完整自设树见custom_trees.json，仅两棵固定树，不代表所有输入。
''')
    write(data/'q4/summary.md','# Q4 正式实验素材\n\n'+games(q4)+'''

每组1001次；全部保持H=2为T2/-1，H=4为T3/3。距离预计算排除在搜索计时之外；实际practical排序计入搜索时间。
四首步素材在results/q4_decision_trace.md，排序素材在results/q4_ordering_analysis.md，缓存见本目录cache_analysis.md。
''')
    branches=load(data/'q4/decision_branches.csv')
    lookup={(r['first_move'],int(r['depth'])):r for r in branches}
    first_table=table(['A首步','即时Gain','H=2最优MIN后U','H=4完整Minimax U'],[
        [first,lookup[first,2]['initial_gain'],lookup[first,2]['minimax_value'],lookup[first,4]['minimax_value']] for first in Q4_VALUES])
    matrix=json.loads((data/'q4/distance_matrix.json').read_text(encoding='utf-8'))
    game=TreasureGame(DistanceTable(tuple(matrix['labels']),tuple(tuple(row) for row in matrix['matrix'])),Q4_VALUES)
    responses=[]
    for first in game.treasure_order:
        after_a=game.transition(game.initial_state(),first)
        for response in game.actions(after_a):
            after_b=game.transition(after_a,response)
            for depth in (2,4):
                value=minimax_treasure(game,depth-2,after_b)['best_value']
                responses.append(dict(first_move=first,b_response=response,depth=depth,value=value))
    with (data/'q4/min_responses.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(responses[0]));writer.writeheader();writer.writerows(responses)
    for first in Q4_VALUES:
        for depth in (2,4):
            if min(r['value'] for r in responses if r['first_move']==first and r['depth']==depth)!=int(lookup[first,depth]['minimax_value']):
                raise AssertionError('MIN response enumeration mismatch')
    response_table=table(['A首步','B回应','H=2 U','H=4后续最优U'],[
        [first,response,next(r['value'] for r in responses if r['first_move']==first and r['b_response']==response and r['depth']==2),
         next(r['value'] for r in responses if r['first_move']==first and r['b_response']==response and r['depth']==4)]
        for first in Q4_VALUES for response in Q4_VALUES if response!=first])
    traces=[]
    for row in branches:
        pv=json.loads(row['principal_variation'])
        traces.append(f"### 首步{row['first_move']}，H={row['depth']}，分支值{row['minimax_value']}\n\n"+
            table(['ply','玩家','目标','Gain','Score_A','Score_B','U'],[
                [i+1,s['player'],s['target'],s['gain'],s['score_a'],s['score_b'],s['utility']] for i,s in enumerate(pv)]))
    decision='''# Q4深度决策事实素材（非最终报告）

H按行动ply计数，叶评价仅U。逐一强制四个首步，再使用纯Minimax计算后续；不用有界Alpha-Beta中间值作为精确分支值。

'''+first_table+'''

H=2只看A/B一轮，T2最坏值-1，优于T3的-2；H=4纳入双方第二次行动后，T3保证3而T2为1。
T3即时Gain=-1，但改变了位置和剩余宝藏，不能只凭首步收益挑选。
一条H=4最优链是A:T3(-1)、B:T1(+1)、A:T2(0)、B:T4(-5)，最终A=-1、B=-4，U=3。
B可能存在并列最优回应，这只是固定顺序的一条最优链，不能声称所有最优应对都会让B最后取T4。

## B的全部回应

每个A首步内，B取本列最小值。

'''+response_table+'\n\n## 逐步得分\n\n'+'\n\n'.join(traces)+'\n'
    write(root/'results/q4_decision_trace.md',decision)
    ordering='# Q4 practical ordering事实素材\n\n'+games([r for r in q4 if r['algorithm']=='alphabeta' and r['order'] in ('original','practical')])+'''

按当前玩家自己的即时Gain降序，B自身Gain提高会降低U，因此B也降序。没有未来Minimax排序信息；每次排序成本包含在搜索时间。

'''
    for depth in ('2','4'):
        pair=[r for r in q4 if r['depth']==depth and r['algorithm']=='alphabeta']
        a=next(r for r in pair if r['order']=='original');b=next(r for r in pair if r['order']=='practical')
        ordering+=f"- H={depth}：visited {a['visited_nodes']}→{b['visited_nodes']}，leaf {a['evaluated_leaf_nodes']}→{b['evaluated_leaf_nodes']}，events {a['prune_events']}→{b['prune_events']}，pruned child {a['pruned_children']}→{b['pruned_children']}；median {float(a['median_elapsed_time'])*1000:.6f}→{float(b['median_elapsed_time'])*1000:.6f} ms。\n"
    ordering+='''
本次H=2节点更少但时间略高，约0.2μs差值受排序开销和系统噪声影响，不下稳定速度结论；H=4节点与本次时间均下降。
practical是启发式，不保证任何地图、深度、状态都得到最大剪枝或更快。原始样本见report_data/q4/timings.csv。
'''
    write(root/'results/q4_ordering_analysis.md',ordering)
    cache_table=table(['模式','target/U','A*次数','累计A*expanded','累计A*generated','game visited','leaf','median(ms)'],[
        [r['mode'],r['best_target']+'/'+r['best_value'],r['astar_calls'],r['astar_expanded'],r['astar_generated'],r['visited_nodes'],
         r['evaluated_leaf_nodes'],f"{float(r['median_elapsed_time'])*1000:.6f}"] for r in cache])
    cache_text='''# 距离缓存事实素材

全部为H=4、纯Minimax、original。无缓存类仅在experiments/report_support.py，共享正式转移/搜索；仅持有坐标/标签，不持有矩阵，每次Gain都实际跑A*。

'''+cache_table+f"\n\n一次预计算重复{prep['repeats']}次的median为{prep['median_precomputation_time']*1000:.6f}ms，36次A*、累计expanded={prep['astar_expanded']}、generated={prep['astar_generated']}。\n"+'''
reused仅测已有表的后续查询，准备成本单列，不能当成消失。one_shot_total外层直接计时，包含完整预计算、构建game和一次搜索；没有把两个median相加当成实测总时间。
uncached的65个访问对应64条行动边，各边跑一次A*。各模式决策、U和博弈访问量完全相同，缓存只减少距离获取的重复工作。
search-only两组已有game对象的初始化都排除；uncached带调用/节点计数，有少量记录开销。
同地图多个深度、算法或反复查询能复用一次矩阵。本次one-shot也低于uncached，但不推广到所有地图。重复预计算只是估计一次成本，不表示正式每次查询都重建。
'''
    write(data/'q4/cache_analysis.md',cache_text)
    seed_rows=[]
    for question in (1,2):
        inputs=json.loads((data/f'q{question}/inputs.json').read_text(encoding='utf-8'))
        attempts=load(data/f'q{question}/generation_attempts.csv')
        for group in sorted({r['group'] for r in inputs if r['group']!='official'}):
            accepted=[r for r in inputs if r['group']==group]
            seed_rows.append([question,group,len(accepted),sum(r['group']==group for r in attempts),', '.join(str(r['seed']) for r in accepted)])
    seed_table=table(['题','配置','可达数','尝试数','全部接受种子'],seed_rows)
    write(data/'seeds.md','# 固定随机输入\n\n'+seed_table+'''

Q1基础20261015，配置顺序20/p20、40/p20、80/p20、40/p10、40/p30，每配置加10000，尝试seed=配置基数+attempt。
Q2基础20261115，配置20/p20、40/p20，每配置加10000。端点固定开放，其余独立抽样，无解拒绝，不按算法节省率挑图。
Q3完整三叉树depth4 seed=20261219，depth6 seed=20261221，叶randint(-50,50)。完整输入已保存，不依赖未来随机实现。
''')
    method='''## 方法和环境

本阶段Python 3.12.14；所有原代码、测试、旧数据原样保留。matplotlib缺失，无安装或下载，不生成PNG。
计数取单次执行；计时两次预热后重复取median，组内方法循环轮换先后。地图31次，小树/博弈1001次，缓存/准备101次，组内相同次数；Q3排序准备31次。
地图时间先每实例取median再组内10图取median；数据生成和独立验证排除，生产算法自己的检查/启发计算保留。Q3 oracle准备单列，Q4实际practical排序计入搜索。
BFS/Dijkstra独立核对所有接受输入费用，Q3用独立穷举定义核对值，Q4官方值和全部36个距离仍核对。所有重复执行检查结果/节点不变。

'''
    summary='# 正式实验报告数据摘要（非最终实验报告）\n\n'+method+'## Q1\n\n'+grids(q1)+'\n\n## Q2\n\n'+grids(q2)+'\n\n'+reduction_table+'''

下降百分比为两个组内节点中位数之比，不是每实例降幅的median，也不是普遍保证。

## Q3

'''+tree_table+'\n\n## Q4\n\n'+games(q4)+'\n\n## 首步分支值\n\n'+first_table+'\n\n## 缓存\n\n'+cache_table+f"\n\n预计算median另为{prep['median_precomputation_time']*1000:.6f}ms；one-shot总时间已直接包含预计算。\n"+'''
## 文件入口

- q1/summary.md、q2/summary.md：地图表和E=0说明；inputs.json是完整输入，generation_attempts.csv包括拒绝记录。
- q3/summary.md：全部树/顺序，custom_trees.json是自设树；preparation_timings.csv含准备开销。
- q4/summary.md、q4/cache_analysis.md：综合题和缓存；每次计时保留在各timings.csv。
- ../q4_decision_trace.md、../q4_ordering_analysis.md：首步解释及practical事实素材。
- seeds.md、run_config.json：随机种子、环境、重复次数和范围。
- analysis_notes.md：报告建议结构对应的事实和限制。

不编写最终报告，不制作提交压缩包。
'''
    write(data/'summary.md',summary)
    notes='''# 分析事实笔记（非最终报告）

## 1. A*状态、g/h/f和队列

状态为(row,col)，g是当前已知最小费用，f=g+h；heapq按f出队，同f固定FIFO。严格改善g才更新父节点并入堆，跳过过期条目。
expanded不含目标，generated是入堆次数含起点与改善g后的重入堆。计时包括算法自身输入检查、启发准备和路径恢复，不含外部数据生成。

## 2. Q1事实

'''+reduction_table+'''

20%障碍下20/40/80的扩展中位数分别320.5→232、1277→810、5122.5→3333；绝对节省增加，相对节省未单调增加。
40×40的10/20/30%样本中相对节省增加，但更多障碍也缩小zero可达区域；只接纳可达图造成条件选择，不能说障碍越多搜索必然越难。
同f的FIFO也影响访问范围；不可把这些有限样本规律当定理。

## 3. Q2可采纳性和事实

'''+admissibility+'''
20×20扩展中位数311→299，40×40为1256→1251.5，本批generated与时间median均增加。随机图最小普通权1使下界较松：40组费用median284.5，起点估计77。
启发计算与不同堆更新顺序带来开销；节点略少不保证更快，generated也不是唯一坐标数。

## 4. Q3回传和剪枝

完整Minimax同树三顺序访问量相同，MAX/MIN依层取最大/最小。depth6值-14，1093访问、729叶；Alpha-Beta原顺序359、oracle较优125、不利1011。
提前取得强alpha/beta界限可跳过无须继续区分的分支。事件数、直接跳过child数、少访问的全部后代数不能混同。
oracle较优排序准备median约9.023ms，搜索约0.0921ms；不能把未来完整信息的成本藏掉。不利顺序也不是必然不剪枝。
官方树小，本次原顺序Alpha-Beta虽然少一个叶子，时间仍高于Minimax。

## 5. Q4深度差异

'''+first_table+'''

H=2只评估A/B一轮，T2的保证值-1优于T3的-2；H=4纳入更新后位置、剩余宝藏和第二次行动的负收益，T3保证3而T2为1。
不要只看即时Gain。全部B回应和一条条可核算的最优链在q4_decision_trace.md；并列最优应对不能解释成唯一过程。

## 6. practical实际效果

H=2访问13→11、叶8→6、事件2→3、直接跳过4→6；median约36.7→36.9μs，未同步更快。
H=4访问47→37、叶16→12、事件5→6、直接跳过6→8；median约135.9→127.2μs。
排序只用当前自己的Gain，B也降序，因为自身收益提高会降低U；与Q3未来值oracle不同，排序开销计入时间。

## 7. 距离预计算实际效果

'''+cache_table+f"\n\n一次预计算median {prep['median_precomputation_time']*1000:.6f}ms，36次A*、329扩展；无缓存64条行动边各跑A*，累计670扩展。\n"+'''
缓存不减少纯Minimax的65个博弈节点，只减少距离获取的重复计算。one-shot直接计时包含准备，不用median之和冒充总时间。
已有矩阵可被多深度、多算法、反复查询共享，reused行的0次A*不表示首次构建免费。

## 8. 实验限制

- 微秒计时有系统调度、解释器、缓存和其他进程噪声；没有跨机器重复或置信区间推断，不作普遍速度百分比结论。
- 官方树小；自设也只有两棵固定三叉树，叶值域有限。
- 地图每配置10张且以可达为条件，仅代表有限样本；不同尺寸/密度不是同一图的逐步改造，不能完全隔离因果。
- 组内节点中位数之比不等于配对降幅median；样本均值不是理论复杂度。
- oracle需要未来完整信息，准备另列，不能直接当实际优化。
- practical不保证所有输入最大剪枝或更快，小树排序可能抵消收益。
- 缓存只比较官方地图H=4 original Minimax，无缓存计数有少量记录开销；one-shot和reuse必须分开。
- 早期题一、二数据来自3.11.9；本阶段正式比较全在3.12.14新采集，不混用旧计时。
- matplotlib缺失，仅提供CSV/Markdown；图表采用标准库SVG，见report/assets。
'''
    write(data/'analysis_notes.md',notes)
    print('Summaries, analysis notes, decision explanations, seeds generated.')


if __name__=='__main__':
    main()
