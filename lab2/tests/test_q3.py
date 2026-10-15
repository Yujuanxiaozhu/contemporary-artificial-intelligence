"""题三手算/独立穷举参考值、剪枝和顺序保持验证。"""
import random
import unittest

from experiments.q3_cases import ORDERS, official_tree, ordered_copy
from src.metrics import SearchStats, GameSearchStats
from src.minimax import TreeNode, minimax, alphabeta


def reference_value(node, is_max=True):
    if not node.children:
        return node.value
    # 独立穷举定义，不调用两种生产算法。
    values = sorted(reference_value(c, not is_max) for c in node.children)
    return values[-1 if is_max else 0]


def occurrence_counts(node):
    if not node.children:
        return 1, 1
    counts = [occurrence_counts(c) for c in node.children]
    return 1+sum(n for n,_ in counts), sum(n for _,n in counts)


def signature(node):
    if not node.children:
        return ('leaf', node.value)
    return ('node', tuple(sorted((signature(c) for c in node.children), key=repr)))


def snapshot(root):
    found = {}
    def visit(node):
        if id(node) in found:
            return
        found[id(node)] = (node.value, tuple(id(c) for c in node.children))
        for child in node.children:
            visit(child)
    visit(root)
    return found


class GameTreeTests(unittest.TestCase):
    def check_value(self, root, expected, is_max=True):
        before = snapshot(root)
        plain, ms = minimax(root, is_max, return_stats=True)
        pruned, ab = alphabeta(root, is_max, return_stats=True)
        self.assertEqual(plain, expected)
        self.assertEqual(pruned, expected)
        self.assertEqual((ms.visited_nodes,ms.evaluated_leaf_nodes), occurrence_counts(root))
        self.assertEqual((ms.prune_events,ms.pruned_children,ms.prune_count), (0,0,0))
        self.assertLessEqual(ab.visited_nodes,ms.visited_nodes)
        self.assertLessEqual(ab.evaluated_leaf_nodes,ms.evaluated_leaf_nodes)
        self.assertEqual(ab.prune_count,ab.pruned_children)
        self.assertGreaterEqual(ms.elapsed_time,0)
        self.assertGreaterEqual(ab.elapsed_time,0)
        self.assertEqual(snapshot(root),before)
        return ms, ab

    def test_single_leaf(self):
        for value in (0,-7,4.25,10**400):
            with self.subTest(value=value):
                ms,ab=self.check_value(TreeNode(value),value)
                self.assertEqual((ms.visited_nodes,ms.evaluated_leaf_nodes),(1,1))
                self.assertEqual((ab.visited_nodes,ab.evaluated_leaf_nodes),(1,1))

    def test_one_level_max(self):
        self.check_value(TreeNode(children=[TreeNode(3),TreeNode(8),TreeNode(1)]),8)

    def test_one_level_min(self):
        self.check_value(TreeNode(children=[TreeNode(3),TreeNode(8),TreeNode(1)]),1,False)

    def test_unbalanced_tree(self):
        root=TreeNode(children=[TreeNode(-2),
            TreeNode(children=[TreeNode(7),TreeNode(children=[TreeNode(1),TreeNode(4)])]),
            TreeNode(children=[TreeNode(9)])])
        self.check_value(root,9)

    def test_negative_leaves(self):
        root=TreeNode(children=[TreeNode(children=[TreeNode(-9),TreeNode(-3)]),
                                TreeNode(children=[TreeNode(-5),TreeNode(-8)])])
        self.check_value(root,-8)

    def test_equal_values_and_equality_cutoff(self):
        root=TreeNode(children=[TreeNode(children=[TreeNode(4),TreeNode(4)]),
                                TreeNode(children=[TreeNode(4),TreeNode(4)])])
        ms,ab=self.check_value(root,4)
        self.assertEqual((ms.visited_nodes,ms.evaluated_leaf_nodes),(7,4))
        self.assertEqual((ab.visited_nodes,ab.evaluated_leaf_nodes,ab.prune_events,ab.pruned_children),(6,3,1,1))

    def test_official_tree_original(self):
        root=official_tree()
        self.assertIs(root.children[0].children[1],root.children[1].children[0])
        self.assertEqual(len(snapshot(root)),12)
        self.assertEqual(minimax(root),5)
        self.assertEqual(alphabeta(root),5)
        ms,ab=self.check_value(root,5)
        self.assertEqual((ms.visited_nodes,ms.evaluated_leaf_nodes),(15,8))
        self.assertEqual((ab.visited_nodes,ab.evaluated_leaf_nodes,ab.prune_events,ab.pruned_children),(14,7,1,1))

    def test_official_all_orders_and_structure(self):
        source=official_tree()
        before=snapshot(source)
        expected={'original':(14,7,1,1),'favorable':(11,5,2,2),'unfavorable':(15,8,0,0)}
        for order in ORDERS:
            with self.subTest(order=order):
                root=ordered_copy(source,order)
                self.assertEqual(signature(root),signature(source))
                self.assertEqual(len(snapshot(root)),12)
                ms,ab=self.check_value(root,5)
                self.assertEqual((ms.visited_nodes,ms.evaluated_leaf_nodes),(15,8))
                self.assertEqual((ab.visited_nodes,ab.evaluated_leaf_nodes,ab.prune_events,ab.pruned_children),expected[order])
        self.assertEqual(snapshot(source),before)
        with self.assertRaises(ValueError):
            ordered_copy(source,'unknown')

    def test_cutoff_skips_whole_subtree(self):
        root=TreeNode(children=[TreeNode(5),TreeNode(children=[TreeNode(1),
            TreeNode(children=[TreeNode(100),TreeNode(200)]),TreeNode(7)])])
        ms,ab=self.check_value(root,5)
        self.assertEqual((ms.visited_nodes,ms.evaluated_leaf_nodes),(8,5))
        self.assertEqual((ab.visited_nodes,ab.evaluated_leaf_nodes,ab.prune_events,ab.pruned_children),(4,2,1,2))
        # 直接跳过 2 个 child，而不是其整棵子树内 4 个节点。
        self.assertEqual(ms.visited_nodes-ab.visited_nodes,4)

    def test_no_pruning_unfavorable(self):
        ms,ab=self.check_value(ordered_copy(official_tree(),'unfavorable'),5)
        self.assertEqual(ab.prune_events,0)
        self.assertEqual(ms.visited_nodes,ab.visited_nodes)

    def test_dfs_leaf_access_order_and_no_cache(self):
        log=[]
        class Leaf:
            children=()
            def __init__(self,value,label):
                self.number,self.label=value,label
            @property
            def value(self):
                log.append(self.label)
                return self.number
        shared=TreeNode(children=[Leaf(6,'c'),Leaf(9,'d')])
        root=TreeNode(children=[
            TreeNode(children=[TreeNode(children=[Leaf(3,'a'),Leaf(5,'b')]),shared]),
            TreeNode(children=[shared,TreeNode(children=[Leaf(1,'e'),Leaf(2,'f')])])])
        self.assertEqual(minimax(root),5)
        self.assertEqual(log,list('abcdcdef'))
        log.clear()
        self.assertEqual(alphabeta(root),5)
        self.assertEqual(log,list('abccdef'))

    def test_last_child_bound_is_not_prune_event(self):
        root=TreeNode(children=[TreeNode(5),TreeNode(children=[TreeNode(1)])])
        _,ab=self.check_value(root,5)
        self.assertEqual((ab.prune_events,ab.pruned_children),(0,0))

    def test_teacher_compatible_nodes(self):
        class TeacherNode:
            def __init__(self,value=None,children=None):
                self.value=value
                self.children=children if children is not None else []
        self.check_value(TeacherNode(value=999,children=[TeacherNode(2),TeacherNode(7)]),7)

    def test_invalid_values_and_inputs(self):
        for solver in (minimax,alphabeta):
            for value in (None,True,'3',float('nan'),float('inf'),-float('inf')):
                with self.subTest(solver=solver.__name__,value=value),self.assertRaises(ValueError):
                    solver(TreeNode(value))
            for root in (None,object(),TreeNode(children='wrong')):
                with self.subTest(solver=solver.__name__),self.assertRaises(ValueError):
                    solver(root)
            with self.assertRaises(ValueError):
                solver(TreeNode(1),maximizing_player=1)
            cycle=TreeNode()
            cycle.children=[cycle]
            with self.assertRaisesRegex(ValueError,'cycle'):
                solver(cycle)
        for alpha,beta in ((2,2),(4,1),(float('nan'),1),(False,3),('0',3)):
            with self.subTest(alpha=alpha,beta=beta),self.assertRaises(ValueError):
                alphabeta(TreeNode(1),alpha=alpha,beta=beta)

    def test_finite_window_documented_bound(self):
        root=TreeNode(children=[TreeNode(6),TreeNode(9)])
        self.assertEqual(alphabeta(root,beta=5),6)
        self.assertEqual(alphabeta(root),9)

    def test_stats_independent_and_astar_unchanged(self):
        self.assertEqual(SearchStats().expanded_nodes,0)
        self.assertEqual(SearchStats().generated_nodes,0)
        self.assertEqual(GameSearchStats().prune_count,0)
        _,first=alphabeta(official_tree(),return_stats=True)
        _,second=alphabeta(TreeNode(1),return_stats=True)
        self.assertIsNot(first,second)
        self.assertEqual(second.visited_nodes,1)
        self.assertEqual(first.visited_nodes,14)

    def test_seeded_random_trees(self):
        rng=random.Random(20261015)
        def generate(depth):
            if depth==0 or rng.random()<0.25:
                return TreeNode(rng.randint(-30,30))
            return TreeNode(children=[generate(depth-1) for _ in range(rng.randint(1,4))])
        # 300 棵树 × MAX/MIN 根 × 三种顺序 = 1800 组一致性检查。
        for case in range(300):
            source=generate(rng.randint(1,5))
            original=signature(source)
            for is_max in (True,False):
                expected=reference_value(source,is_max)
                for order in ORDERS:
                    with self.subTest(case=case,is_max=is_max,order=order):
                        root=ordered_copy(source,order,is_max)
                        self.assertEqual(signature(root),original)
                        self.check_value(root,expected,is_max)


if __name__=='__main__':
    unittest.main()
