"""四邻接 A*。默认返回值与题目一致，return_stats=True 时返回 (结果, 统计)。"""
import heapq
from itertools import count
from time import perf_counter

from .metrics import SearchStats

DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def manhattan(node, goal):
    return abs(node[0] - goal[0]) + abs(node[1] - goal[1])


def weighted_lower_bound(node, goal, minimum_cost):
    # d 步至少有 d-1 次进入普通地形，最后进入 E 的代价是 0。
    # 若存在零权地形，minimum_cost=0，安全退化为 Dijkstra。
    return max(manhattan(node, goal) - 1, 0) * minimum_cost


def _validate(start, goal, grid):
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("grid must be a nonempty rectangular grid")
    rows, cols = len(grid), len(grid[0])
    for name, point in (("start", start), ("goal", goal)):
        if (not isinstance(point, tuple) or len(point) != 2
                or any(type(v) is not int for v in point)):
            raise ValueError(f"{name} must be a tuple of two integers")
        if not (0 <= point[0] < rows and 0 <= point[1] < cols):
            raise ValueError(f"{name} is outside grid")
    return rows, cols


def _search(start, goal, rows, cols, step_cost, heuristic, stats):
    serial = count()
    best_g = {start: 0}
    came_from = {}
    frontier = [(heuristic(start), next(serial), 0, start)]
    stats.generated_nodes = 1
    while frontier:
        _, _, g, node = heapq.heappop(frontier)
        # decrease-key 用新条目替代；旧条目不得重复扩展。
        if g != best_g[node]:
            continue
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            return path, g
        stats.expanded_nodes += 1
        for dr, dc in DIRECTIONS:
            neighbor = (node[0] + dr, node[1] + dc)
            if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols):
                continue
            # 非负代价下，返回起点的环不会改善最优解；也避免给 S 虚构进入代价。
            if neighbor == start:
                continue
            cost = step_cost(neighbor)
            if cost is None:
                continue
            candidate = g + cost
            if candidate < best_g.get(neighbor, float("inf")):
                best_g[neighbor] = candidate
                came_from[neighbor] = node
                heapq.heappush(frontier, (
                    candidate + heuristic(neighbor), next(serial), candidate, neighbor))
                stats.generated_nodes += 1
    return [], -1


def astar_maze(start, goal, grid, heuristic="manhattan", *, return_stats=False):
    """返回最短路径（含起终点）；不可达或端点为 X 返回 []。"""
    began = perf_counter()
    stats = SearchStats()
    rows, cols = _validate(start, goal, grid)
    if heuristic not in ("manhattan", "zero"):
        raise ValueError("heuristic must be 'manhattan' or 'zero'")
    if any(cell not in ("S", "E", ".", "X") for row in grid for cell in row):
        raise ValueError("maze cells must be S, E, . or X")
    if grid[start[0]][start[1]] == "X" or grid[goal[0]][goal[1]] == "X":
        result = []
    else:
        h = (lambda n: manhattan(n, goal)) if heuristic == "manhattan" else (lambda n: 0)
        result, _ = _search(start, goal, rows, cols,
                            lambda n: None if grid[n[0]][n[1]] == "X" else 1, h, stats)
    stats.elapsed_time = perf_counter() - began
    return (result, stats) if return_stats else result


def astar_weighted(start, goal, grid, heuristic="admissible", *, return_stats=False):
    """返回最小总代价；进入 goal 免费，起点不收费，不可达返回 -1。

    普通地形支持非负整数和数字字符串；X 是无解测试用的障碍扩展。
    S/E 标记可省略，但若存在必须位于参数指定坐标。
    """
    began = perf_counter()
    stats = SearchStats()
    rows, cols = _validate(start, goal, grid)
    if heuristic not in ("admissible", "zero"):
        raise ValueError("heuristic must be 'admissible' or 'zero'")
    costs = {}
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            node = (r, c)
            if isinstance(cell, str) and cell in ("S", "E", "X"):
                if cell == "S" and node != start:
                    raise ValueError("S marker must match start")
                if cell == "E" and node != goal:
                    raise ValueError("E marker must match goal")
                costs[node] = None if cell == "X" else 0
            else:
                if type(cell) is int:
                    cost = cell
                elif isinstance(cell, str) and cell.isascii() and cell.isdigit():
                    cost = int(cell)
                else:
                    raise ValueError("terrain must be a nonnegative integer, S, E or X")
                if cost < 0:
                    raise ValueError("negative terrain costs are unsupported")
                costs[node] = cost
    if costs[start] is None or costs[goal] is None:
        result = -1
    else:
        terrain = [cost for n, cost in costs.items()
                   if n not in (start, goal) and cost is not None]
        minimum = min(terrain, default=0)
        costs[goal] = 0
        h = ((lambda n: weighted_lower_bound(n, goal, minimum))
             if heuristic == "admissible" else (lambda n: 0))
        _, result = _search(start, goal, rows, cols, costs.__getitem__, h, stats)
    stats.elapsed_time = perf_counter() - began
    return (result, stats) if return_stats else result
