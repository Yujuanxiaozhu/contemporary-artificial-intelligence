"""PDF 第12页官方建树代码；排序仅用于离线访问顺序实验。"""
from copy import deepcopy

from src.minimax import TreeNode, minimax

ORDERS = ("original", "favorable", "unfavorable")


def official_tree():
    leaf1 = TreeNode(value=3)
    leaf2 = TreeNode(value=5)
    leaf3 = TreeNode(value=6)
    leaf4 = TreeNode(value=9)
    leaf5 = TreeNode(value=1)
    leaf6 = TreeNode(value=2)
    max1 = TreeNode(children=[leaf1, leaf2])
    max2 = TreeNode(children=[leaf3, leaf4])
    max3 = TreeNode(children=[leaf5, leaf6])
    min1 = TreeNode(children=[max1, max2])
    min2 = TreeNode(children=[max2, max3])
    return TreeNode(children=[min1, min2])


def ordered_copy(root, order, maximizing_player=True):
    """保持共享对象关系的副本；只重排每个 children 列表。

    favorable: MAX 降序、MIN 升序；unfavorable 反向。
    排序键为完整 Minimax 的真实值，是离线理想顺序实验，非免费启发式。
    准备阶段不计入后续单次搜索统计，实验另记录其耗时。
    """
    if order not in ORDERS:
        raise ValueError("unknown order")
    result = deepcopy(root)
    seen = set()

    def arrange(node, is_max):
        if not node.children or id(node) in seen:
            return
        seen.add(id(node))
        if order != "original":
            descending = is_max if order == "favorable" else not is_max
            node.children.sort(
                key=lambda child: minimax(child, maximizing_player=not is_max),
                reverse=descending)
        for child in node.children:
            arrange(child, not is_max)

    arrange(result, maximizing_player)
    return result
