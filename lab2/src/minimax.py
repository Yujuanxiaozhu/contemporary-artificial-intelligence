"""题目三：标准 DFS Minimax 和 Alpha-Beta，无缓存、无内部重排。"""
import math
from time import perf_counter

from .metrics import GameSearchStats


class TreeNode:
    def __init__(self, value=None, children=None):
        self.value = value
        self.children = children if children is not None else []


def _children(node):
    if node is None or not (hasattr(node, "children") or hasattr(node, "value")):
        raise ValueError("node must have children or value")
    children = getattr(node, "children", [])
    if not isinstance(children, (list, tuple)):
        raise ValueError("children must be a list or tuple")
    return children


def _leaf_value(node, stats):
    value = getattr(node, "value", None)
    if (type(value) not in (int, float)
            or (type(value) is float and not math.isfinite(value))):
        raise ValueError("leaf value must be a finite int or float (not bool)")
    stats.evaluated_leaf_nodes += 1
    return value


def _check_player(maximizing_player):
    if type(maximizing_player) is not bool:
        raise ValueError("maximizing_player must be bool")


def minimax(root, maximizing_player=True, return_stats=False):
    """默认根为 MAX，返回最佳分数；可选返回 (分数, GameSearchStats)。"""
    began = perf_counter()
    _check_player(maximizing_player)
    stats = GameSearchStats()
    active = set()

    def visit(node, is_max):
        stats.visited_nodes += 1
        children = _children(node)
        if not children:
            return _leaf_value(node, stats)
        identity = id(node)
        if identity in active:
            raise ValueError("cycle detected: input must be an acyclic game tree")
        active.add(identity)
        try:
            value = -math.inf if is_max else math.inf
            for child in children:
                child_value = visit(child, not is_max)
                value = max(value, child_value) if is_max else min(value, child_value)
            return value
        finally:
            active.remove(identity)

    result = visit(root, maximizing_player)
    stats.elapsed_time = perf_counter() - began
    return (result, stats) if return_stats else result


def alphabeta(root, maximizing_player=True, alpha=-math.inf, beta=math.inf,
              return_stats=False):
    """全窗口时返回精确 Minimax 值；有限窗口时可能返回 fail-soft 界。

    prune_events 仅计确实跳过后续 child 的 cutoff；最后一个 child 后
    即使满足 alpha>=beta，也没有实际剪枝，不计事件。
    """
    began = perf_counter()
    _check_player(maximizing_player)
    for bound in (alpha, beta):
        if (type(bound) not in (int, float)
                or (type(bound) is float and math.isnan(bound))):
            raise ValueError("alpha and beta must be numeric non-NaN bounds")
    if alpha >= beta:
        raise ValueError("initial bounds must satisfy alpha < beta")
    stats = GameSearchStats()
    active = set()

    def visit(node, is_max, lower, upper):
        stats.visited_nodes += 1
        children = _children(node)
        if not children:
            return _leaf_value(node, stats)
        identity = id(node)
        if identity in active:
            raise ValueError("cycle detected: input must be an acyclic game tree")
        active.add(identity)
        try:
            value = -math.inf if is_max else math.inf
            for index, child in enumerate(children):
                child_value = visit(child, not is_max, lower, upper)
                if is_max:
                    value = max(value, child_value)
                    lower = max(lower, value)
                else:
                    value = min(value, child_value)
                    upper = min(upper, value)
                if lower >= upper:
                    remaining = len(children) - index - 1
                    if remaining:
                        stats.prune_events += 1
                        stats.pruned_children += remaining
                    break
            return value
        finally:
            active.remove(identity)

    result = visit(root, maximizing_player, alpha, beta)
    stats.elapsed_time = perf_counter() - began
    return (result, stats) if return_stats else result
