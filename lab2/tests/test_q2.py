import copy
import random
import unittest

from experiments.cases import Q2_START, Q2_GOAL, Q2_GRID
from src.astar import astar_weighted, weighted_lower_bound
from tests.oracles import bellman_ford_cost


class WeightedTests(unittest.TestCase):
    def check_case(self, start, goal, grid, expected):
        before = copy.deepcopy(grid)
        for mode in ('zero', 'admissible'):
            with self.subTest(mode=mode):
                result, stats = astar_weighted(start,goal,grid,mode,return_stats=True)
                self.assertIs(type(result),int)
                self.assertEqual(result,expected)
                self.assertGreaterEqual(stats.elapsed_time,0)
                self.assertGreaterEqual(stats.generated_nodes,stats.expanded_nodes)
                self.assertEqual(grid,before)

    def test_official(self):
        self.check_case(Q2_START,Q2_GOAL,Q2_GRID,7)
        self.assertEqual(bellman_ford_cost(Q2_START,Q2_GOAL,Q2_GRID),7)
        self.assertEqual(astar_weighted(Q2_START,Q2_GOAL,Q2_GRID),7)

    def test_same_endpoint(self):
        self.check_case((0,0),(0,0),[['S']],0)

    def test_adjacent_free_goal(self):
        self.check_case((0,0),(0,1),[['S','E']],0)
        self.assertEqual(weighted_lower_bound((0,0),(0,1),3),0)

    def test_no_solution(self):
        self.check_case((0,0),(0,2),[['S','X','E']],-1)

    def test_blocked_endpoints(self):
        self.check_case((0,0),(0,1),[['X','E']],-1)
        self.check_case((0,0),(0,1),[['S','X']],-1)

    def test_longer_but_cheaper_route(self):
        self.check_case((0,0),(0,2),[['S',9,'E'],[1,1,1]],3)

    def test_string_costs(self):
        self.check_case((0,0),(0,3),[['S','2','3','E']],5)

    def test_zero_terrain(self):
        self.check_case((0,0),(0,3),[['S',0,0,'E']],0)

    def test_integer_endpoints(self):
        self.check_case((0,0),(0,2),[[8,2,9]],2)

    def test_invalid_inputs(self):
        for grid in ([],[[]],[[1],[1,2]],[['S',-1,'E']],
                     [['S',1.5,'E']],[['S',True,'E']],[['S','?','E']],
                     [['S','S','E']],[['S','E',1]]):
            goal = (0,len(grid[0])-1) if grid and grid[0] else (0,0)
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                astar_weighted((0,0),goal,grid)
        with self.assertRaises(ValueError):
            astar_weighted((0,0),(0,0),[[1]],'unknown')
        with self.assertRaises(ValueError):
            astar_weighted((0,0),(2,0),[[1]])

    def test_seeded_maps_against_bellman_ford(self):
        rng = random.Random(20261015)
        for case in range(150):
            # 交替覆盖严格正权与含零权地图，避免随机实验全退化为 h=0。
            minimum = case % 2
            grid = [['X' if rng.random()<0.2 else rng.randint(minimum,9)
                     for _ in range(5)] for _ in range(4)]
            grid[0][0],grid[3][4]='S','E'
            with self.subTest(case=case):
                self.check_case((0,0),(3,4),grid,bellman_ford_cost((0,0),(3,4),grid))

    def test_heuristic_admissibility_and_consistency(self):
        # 对每个可达节点独立计算真实剩余代价，验证下界；S 的入边被排除。
        rng = random.Random(17)
        for case in range(30):
            grid = [[rng.randint(1,9) for _ in range(4)] for _ in range(4)]
            start,goal=(0,0),(3,3)
            grid[0][0],grid[3][3]='S','E'
            minimum=min(v for row in grid for v in row if type(v) is int)
            numeric=copy.deepcopy(grid)
            numeric[0][0]='X'
            for r in range(4):
                for c in range(4):
                    node=(r,c)
                    if node == start:
                        exact=bellman_ford_cost(start,goal,grid)
                    else:
                        exact=bellman_ford_cost(node,goal,numeric)
                    h=weighted_lower_bound(node,goal,minimum)
                    with self.subTest(case=case,node=node):
                        self.assertLessEqual(h,exact)
                        for nxt in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                            if 0<=nxt[0]<4 and 0<=nxt[1]<4 and nxt!=start:
                                cost=0 if nxt==goal else grid[nxt[0]][nxt[1]]
                                self.assertLessEqual(h,cost+weighted_lower_bound(nxt,goal,minimum))


if __name__ == '__main__':
    unittest.main()
