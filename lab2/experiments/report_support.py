"""阶段4实验辅助，不改变src内主体算法。"""
from collections import deque
from dataclasses import asdict, replace
import heapq
import random
from statistics import median
from time import perf_counter
from types import SimpleNamespace

from src.minimax import TreeNode
from src.treasure_game import TreasureGame, astar_distance, precompute_distances, minimax_treasure


def bfs_reference(grid, start, goal):
    queue=deque([(start,0)])
    seen={start}
    while queue:
        point,distance=queue.popleft()
        if point==goal:
            return distance
        r,c=point
        for nxt in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
            nr,nc=nxt
            if 0<=nr<len(grid) and 0<=nc<len(grid[0]) and grid[nr][nc]!='X' and nxt not in seen:
                seen.add(nxt)
                queue.append((nxt,distance+1))
    return -1


def weighted_reference(grid, start, goal):
    # 题二独立Dijkstra；没有调用生产费用解析或启发函数。
    queue=[(0,start)]
    best={start:0}
    while queue:
        cost,point=heapq.heappop(queue)
        if cost!=best[point]:
            continue
        if point==goal:
            return cost
        r,c=point
        for nxt in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
            nr,nc=nxt
            if not (0<=nr<len(grid) and 0<=nc<len(grid[0])) or grid[nr][nc]=='X':
                continue
            step=0 if nxt in (start,goal) else int(grid[nr][nc])
            candidate=cost+step
            if candidate<best.get(nxt,float('inf')):
                best[nxt]=candidate
                heapq.heappush(queue,(candidate,nxt))
    return -1


def validate_path(path, grid, start, goal, expected):
    if not path or path[0]!=start or path[-1]!=goal or len(path)-1!=expected:
        raise AssertionError('path endpoints or optimum do not match independent BFS')
    for r,c in path:
        if not (0<=r<len(grid) and 0<=c<len(grid[0])) or grid[r][c]=='X':
            raise AssertionError('path outside traversable grid')
    for a,b in zip(path,path[1:]):
        if abs(a[0]-b[0])+abs(a[1]-b[1])!=1:
            raise AssertionError('non-adjacent path step')


def measure_methods(methods, repeats):
    """一次逻辑计数+两次预热；重复时轮换算法先后，返回全部原始时间。"""
    baselines={key:call() for key,call in methods.items()}
    for call in methods.values():
        for _ in range(2):
            call()
    logical={key:{k:v for k,v in asdict(stats).items() if k!='elapsed_time'}
             for key,(_,stats) in baselines.items()}
    samples={key:[] for key in methods}
    names=list(methods)
    for iteration in range(repeats):
        order=names[iteration%len(names):]+names[:iteration%len(names)]
        for key in order:
            value,stats=methods[key]()
            counts={k:v for k,v in asdict(stats).items() if k!='elapsed_time'}
            if value!=baselines[key][0] or counts!=logical[key]:
                raise AssertionError(f'non-deterministic result/counts in {key}')
            samples[key].append(stats.elapsed_time)
    return baselines,samples


def generate_maps(size, density, count, base_seed, weighted):
    accepted=[]
    attempts=[]
    for attempt in range(10000):
        seed=base_seed+attempt
        rng=random.Random(seed)
        grid=[]
        for _ in range(size):
            row=[]
            for _ in range(size):
                blocked=rng.random()<density
                row.append('X' if blocked else (rng.randint(1,9) if weighted else '.'))
            grid.append(row)
        start,goal=(0,0),(size-1,size-1)
        grid[0][0],grid[-1][-1]='S','E'
        expected=(weighted_reference if weighted else bfs_reference)(grid,start,goal)
        actual=sum(v=='X' for row in grid for v in row)/(size*size-2)
        attempts.append(dict(seed=seed,attempt=attempt,reachable=expected>=0,
                             oracle_cost=expected,actual_obstacle_density=actual))
        if expected>=0:
            accepted.append(dict(seed=seed,grid=grid,start=start,goal=goal,
                                 oracle_cost=expected,actual_obstacle_density=actual))
        if len(accepted)==count:
            return accepted,attempts
    raise RuntimeError('failed to obtain requested reachable instances within 10000 attempts')


def full_tree(branching, depth, seed):
    rng=random.Random(seed)
    def build(level):
        if level==0:
            return TreeNode(value=rng.randint(-50,50))
        return TreeNode(children=[build(level-1) for _ in range(branching)])
    return build(depth)


def exhaustive_value(node, is_max=True):
    if not node.children:
        return node.value
    values=[exhaustive_value(child,not is_max) for child in node.children]
    return (max if is_max else min)(values)


class UncachedTreasureGame(TreasureGame):
    """仅实验用：共享正式转移/Minimax，每次需要距离都真正运行A*。

    distances只有地标名称，完全不持有距离矩阵；gain不调用查表接口。
    """
    def __init__(self, grid, landmarks, values):
        self.grid=grid
        self.landmarks=dict(landmarks)
        self.values=dict(values)
        self.treasure_order=tuple(values)
        self.distances=SimpleNamespace(labels=tuple(landmarks))
        self.reset_counters()

    def reset_counters(self):
        self.astar_calls=0
        self.astar_expanded=0
        self.astar_generated=0

    def gain(self, state, target):
        source=state.position_a if state.current_player=='A' else state.position_b
        cost,stats=astar_distance(self.landmarks[source],self.landmarks[target],self.grid,return_stats=True)
        if cost<0:
            raise ValueError('uncached reference encountered unreachable target')
        self.astar_calls+=1
        self.astar_expanded+=stats.expanded_nodes
        self.astar_generated+=stats.generated_nodes
        return self.values[target]-cost


def cache_callables(table, grid, landmarks, values):
    cached=TreasureGame(table,values)
    uncached=UncachedTreasureGame(grid,landmarks,values)

    def reused():
        result,stats=minimax_treasure(cached,4,return_stats=True)
        return dict(result,astar_calls=0,astar_expanded=0,astar_generated=0),stats

    def no_cache():
        uncached.reset_counters()
        result,stats=minimax_treasure(uncached,4,return_stats=True)
        if uncached.astar_calls!=stats.visited_nodes-1:
            raise AssertionError('uncached must call A* exactly once per original-order action')
        return dict(result,astar_calls=uncached.astar_calls,astar_expanded=uncached.astar_expanded,
                    astar_generated=uncached.astar_generated),stats

    def one_shot():
        began=perf_counter()
        fresh=precompute_distances(grid,landmarks)
        game=TreasureGame(fresh,values)
        result,stats=minimax_treasure(game,4,return_stats=True)
        total=perf_counter()-began
        # 仅在实验返回副本中把计时改为端到端，不修改生产统计对象或算法。
        stats=replace(stats,elapsed_time=total)
        return dict(result,astar_calls=len(fresh.labels)**2,
                    astar_expanded=sum(s.expanded_nodes for row in fresh.pair_stats for s in row),
                    astar_generated=sum(s.generated_nodes for row in fresh.pair_stats for s in row)),stats
    return {'cached_reused_search':reused,'uncached_search':no_cache,'cached_one_shot_total':one_shot}
