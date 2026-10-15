"""题四：进入目标仍收费的 A*、距离预计算、宝藏博弈。"""
from dataclasses import dataclass
from math import inf
from time import perf_counter

from .astar import _search, _validate, manhattan
from .metrics import SearchStats, GameSearchStats

ACTION_ORDERS = ("original", "practical", "unfavorable")


def _entry_cost(cell):
    if cell == "X":
        return None
    if isinstance(cell, str) and (cell in ("A", "B") or
            (cell.startswith("T") and cell[1:].isascii() and cell[1:].isdigit()
             and int(cell[1:]) > 0)):
        return 1
    if isinstance(cell, str) and cell.isascii() and cell.isdigit():
        cell = int(cell)
    if type(cell) is not int or cell <= 0:
        raise ValueError("Q4 terrain must be positive integers, X, A, B or T<number>")
    return cell


def astar_distance(start, goal, grid, *, return_stats=False):
    """四邻接进入成本 A*；包含进入 goal 的费用，无解 -1。"""
    began = perf_counter()
    stats = SearchStats()
    rows, cols = _validate(start, goal, grid)
    costs = {(r,c): _entry_cost(cell) for r,row in enumerate(grid) for c,cell in enumerate(row)}
    if costs[start] is None or costs[goal] is None:
        result = -1
    else:
        minimum = min(v for v in costs.values() if v is not None)
        _, result = _search(start, goal, rows, cols, costs.__getitem__,
                            lambda n: manhattan(n, goal)*minimum, stats)
    stats.elapsed_time = perf_counter() - began
    return (result, stats) if return_stats else result


@dataclass(frozen=True)
class DistanceTable:
    labels: tuple
    matrix: tuple
    distance_precomputation_time: float = 0.0
    pair_stats: tuple = ()

    def distance(self, source, target):
        return self.matrix[self.labels.index(source)][self.labels.index(target)]


def precompute_distances(grid, landmarks):
    """逐方向独立计算全部 N×N 项，不假设任意进入成本地图对称。"""
    began = perf_counter()
    labels = tuple(landmarks)
    if not labels:
        raise ValueError("landmarks must not be empty")
    matrix, all_stats = [], []
    for source in labels:
        row, stats_row = [], []
        for target in labels:
            distance, stats = astar_distance(landmarks[source], landmarks[target], grid,
                                              return_stats=True)
            row.append(distance)
            stats_row.append(stats)
        matrix.append(tuple(row))
        all_stats.append(tuple(stats_row))
    return DistanceTable(labels, tuple(matrix), perf_counter()-began, tuple(all_stats))


@dataclass(frozen=True)
class GameState:
    position_a: str
    position_b: str
    remaining_treasures: tuple
    score_a: int = 0
    score_b: int = 0
    current_player: str = "A"

    def __post_init__(self):
        object.__setattr__(self, "remaining_treasures", tuple(self.remaining_treasures))
        if self.current_player not in ("A", "B"):
            raise ValueError("current_player must be A or B")
        if len(set(self.remaining_treasures)) != len(self.remaining_treasures):
            raise ValueError("remaining treasures must be unique")
        if type(self.score_a) is not int or type(self.score_b) is not int:
            raise ValueError("scores must be integers")

    @property
    def utility(self):
        return self.score_a - self.score_b


class TreasureGame:
    def __init__(self, distances, values):
        self.distances = distances
        self.values = dict(values)
        self.treasure_order = tuple(values)
        labels = distances.labels
        if (len(set(labels)) != len(labels) or len(distances.matrix) != len(labels)
                or any(len(row) != len(labels) for row in distances.matrix)):
            raise ValueError("invalid distance matrix shape or labels")
        if not {"A", "B", *values}.issubset(labels):
            raise ValueError("distance table must include A, B and every treasure")
        if any(type(v) is not int for v in values.values()):
            raise ValueError("treasure values must be integers")
        if any(type(v) is not int or v < 0 for row in distances.matrix for v in row):
            raise ValueError("game requires finite reachable nonnegative distances")
        if any(distances.matrix[i][i] != 0 for i in range(len(labels))):
            raise ValueError("distance matrix diagonal must be zero")

    def initial_state(self):
        return GameState("A", "B", self.treasure_order)

    def validate_state(self, state):
        if not isinstance(state, GameState):
            raise ValueError("state must be GameState")
        if state.position_a not in self.distances.labels or state.position_b not in self.distances.labels:
            raise ValueError("unknown player position")
        if not set(state.remaining_treasures).issubset(self.values):
            raise ValueError("unknown remaining treasure")

    def gain(self, state, target):
        position = state.position_a if state.current_player == "A" else state.position_b
        return self.values[target] - self.distances.distance(position, target)

    def actions(self, state, order="original"):
        if order not in ACTION_ORDERS:
            raise ValueError("unknown action order")
        actions = [t for t in self.treasure_order if t in state.remaining_treasures]
        if order != "original":
            # B 自身 gain 越大，U=Score_A-Score_B 越小，所以 A/B 均高 gain 优先。
            actions.sort(key=lambda target: self.gain(state, target), reverse=order == "practical")
        return actions

    def transition(self, state, target):
        self.validate_state(state)
        if target not in state.remaining_treasures:
            raise ValueError("target must be an uncollected treasure")
        gain = self.gain(state, target)
        remaining = tuple(t for t in state.remaining_treasures if t != target)
        if state.current_player == "A":
            return GameState(target, state.position_b, remaining,
                             state.score_a+gain, state.score_b, "B")
        return GameState(state.position_a, target, remaining,
                         state.score_a, state.score_b+gain, "A")


def _prepare(game, depth, state, order):
    if type(depth) is not int or depth < 0:
        raise ValueError("depth must be a nonnegative integer number of plies")
    if order not in ACTION_ORDERS:
        raise ValueError("unknown action order")
    state = game.initial_state() if state is None else state
    game.validate_state(state)
    return state


def minimax_treasure(game, depth, state=None, order="original", *, return_stats=False):
    began = perf_counter()
    state = _prepare(game, depth, state, order)
    stats = GameSearchStats()

    def visit(current, remaining_depth):
        stats.visited_nodes += 1
        if remaining_depth == 0 or not current.remaining_treasures:
            stats.evaluated_leaf_nodes += 1
            return None, current.utility
        is_max = current.current_player == "A"
        best_target, best_value = None, -inf if is_max else inf
        for target in game.actions(current, order):
            _, value = visit(game.transition(current, target), remaining_depth-1)
            better = value > best_value if is_max else value < best_value
            if better:
                best_target, best_value = target, value
        return best_target, best_value

    target, value = visit(state, depth)
    stats.elapsed_time = perf_counter() - began
    result = {"best_target": target, "best_value": value}
    return (result, stats) if return_stats else result


def alphabeta_treasure(game, depth, state=None, order="original", *, return_stats=False):
    began = perf_counter()
    state = _prepare(game, depth, state, order)
    stats = GameSearchStats()

    def visit(current, remaining_depth, alpha, beta):
        stats.visited_nodes += 1
        if remaining_depth == 0 or not current.remaining_treasures:
            stats.evaluated_leaf_nodes += 1
            return None, current.utility
        is_max = current.current_player == "A"
        best_target, best_value = None, -inf if is_max else inf
        actions = game.actions(current, order)
        for index, target in enumerate(actions):
            _, value = visit(game.transition(current, target), remaining_depth-1, alpha, beta)
            better = value > best_value if is_max else value < best_value
            if better:
                best_target, best_value = target, value
            if is_max:
                alpha = max(alpha, best_value)
            else:
                beta = min(beta, best_value)
            if alpha >= beta:
                remaining = len(actions)-index-1
                if remaining:
                    stats.prune_events += 1
                    stats.pruned_children += remaining
                break
        return best_target, best_value

    target, value = visit(state, depth, -inf, inf)
    stats.elapsed_time = perf_counter() - began
    result = {"best_target": target, "best_value": value}
    return (result, stats) if return_stats else result
