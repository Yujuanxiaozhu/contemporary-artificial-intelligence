"""测试用独立参考算法，不调用生产搜索或启发函数。"""
from collections import deque


def bfs_cost(start, goal, grid):
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (r, c), distance = queue.popleft()
        if (r, c) == goal:
            return distance
        for nr, nc in ((r+1, c), (r-1, c), (r, c+1), (r, c-1)):
            if (0 <= nr < len(grid) and 0 <= nc < len(grid[0])
                    and grid[nr][nc] != 'X' and (nr, nc) not in seen):
                seen.add((nr, nc))
                queue.append(((nr, nc), distance+1))
    return -1


def bellman_ford_cost(start, goal, grid):
    nodes = [(r,c) for r,row in enumerate(grid) for c,v in enumerate(row) if v != 'X']
    distances = dict.fromkeys(nodes, float('inf'))
    distances[start] = 0
    for _ in range(len(nodes)-1):
        changed = False
        for r,c in nodes:
            for neighbor in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                if neighbor not in distances or neighbor == start:
                    continue
                value = grid[neighbor[0]][neighbor[1]]
                cost = 0 if neighbor == goal else int(value)
                proposal = distances[(r,c)] + cost
                if proposal < distances[neighbor]:
                    distances[neighbor] = proposal
                    changed = True
        if not changed:
            break
    return -1 if distances[goal] == float('inf') else distances[goal]
