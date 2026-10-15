"""统一搜索统计；节点数采用固定口径，时间单位为秒。"""
from dataclasses import dataclass


@dataclass
class SearchStats:
    # 成功出队并扫描邻居的节点数，不含目标和过期堆条目。
    expanded_nodes: int = 0
    # 入堆次数，含起点和更优 g 引起的再次入堆，不含失败的邻居尝试。
    generated_nodes: int = 0
    elapsed_time: float = 0.0
    # 为后续阶段预留，本阶段不执行博弈搜索。
    evaluated_leaf_nodes: int = 0
    prune_count: int = 0


@dataclass
class GameSearchStats:
    """博弈搜索按递归访问次数计数，与 A* SearchStats 相互独立。"""
    visited_nodes: int = 0
    evaluated_leaf_nodes: int = 0
    prune_events: int = 0
    pruned_children: int = 0
    elapsed_time: float = 0.0

    @property
    def prune_count(self):
        """兼容名称：等于直接跳过的 child 数，不是 cutoff 次数。"""
        return self.pruned_children
