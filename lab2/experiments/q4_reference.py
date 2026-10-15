"""独立 Dijkstra 参考算法；不调用生产 A* 或地形解析函数。"""
import heapq


def dijkstra_distance(grid, start, goal):
    def entry(point):
        value = grid[point[0]][point[1]]
        if value == 'X':
            return None
        if isinstance(value, str) and (value in ('A','B') or value.startswith('T')):
            return 1
        return int(value)
    if entry(start) is None or entry(goal) is None:
        return -1
    queue = [(0,start)]
    distance = {start:0}
    while queue:
        cost, point = heapq.heappop(queue)
        if cost != distance[point]:
            continue
        if point == goal:
            return cost
        r,c = point
        for nr,nc in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
            if not (0 <= nr < len(grid) and 0 <= nc < len(grid[0])):
                continue
            step = entry((nr,nc))
            if step is None:
                continue
            candidate = cost+step
            if candidate < distance.get((nr,nc),float('inf')):
                distance[(nr,nc)] = candidate
                heapq.heappush(queue,(candidate,(nr,nc)))
    return -1


def verify_distances(table, grid, landmarks):
    checked = 0
    for i,source in enumerate(table.labels):
        for j,target in enumerate(table.labels):
            expected = dijkstra_distance(grid,landmarks[source],landmarks[target])
            if table.matrix[i][j] != expected:
                raise AssertionError(f'{source}->{target}: A*={table.matrix[i][j]}, Dijkstra={expected}')
            checked += 1
    return checked
