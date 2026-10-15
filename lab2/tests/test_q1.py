import copy
import random
import unittest

from experiments.cases import Q1_START, Q1_GOAL, Q1_GRID
from src.astar import astar_maze
from tests.oracles import bfs_cost


class MazeTests(unittest.TestCase):
    def check_case(self, start, goal, grid, expected):
        before = copy.deepcopy(grid)
        for mode in ('zero', 'manhattan'):
            with self.subTest(mode=mode, start=start, goal=goal):
                path, stats = astar_maze(start, goal, grid, mode, return_stats=True)
                self.assertIsInstance(path, list)
                if expected == -1:
                    self.assertEqual(path, [])
                else:
                    self.assertEqual(path[0], start)
                    self.assertEqual(path[-1], goal)
                    self.assertEqual(len(path)-1, expected)
                    self.assertEqual(len(set(path)), len(path))
                    for r,c in path:
                        self.assertTrue(0 <= r < len(grid) and 0 <= c < len(grid[0]))
                        self.assertNotEqual(grid[r][c], 'X')
                    for a,b in zip(path,path[1:]):
                        self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]), 1)
                self.assertGreaterEqual(stats.elapsed_time, 0)
                self.assertGreaterEqual(stats.generated_nodes, stats.expanded_nodes)
                self.assertEqual(grid, before)

    def test_official(self):
        self.check_case(Q1_START, Q1_GOAL, Q1_GRID, 7)
        self.assertEqual(bfs_cost(Q1_START,Q1_GOAL,Q1_GRID),7)
        self.assertIsInstance(astar_maze(Q1_START,Q1_GOAL,Q1_GRID),list)

    def test_same_endpoint(self):
        self.check_case((0,0),(0,0),[['S']],0)
        _, s = astar_maze((0,0),(0,0),[['S']], return_stats=True)
        self.assertEqual((s.expanded_nodes,s.generated_nodes),(0,1))

    def test_no_solution(self):
        self.check_case((0,0),(0,2),[['S','X','E']],-1)

    def test_single_route(self):
        self.check_case((0,0),(1,2),[['S','X','X'],['.','.','E']],3)

    def test_multiple_shortest_routes(self):
        self.check_case((0,0),(2,2),[['S','.','.'],['.','.','.'],['.','.','E']],4)

    def test_blocked_endpoints(self):
        self.check_case((0,0),(0,1),[['X','E']],-1)
        self.check_case((0,0),(0,1),[['S','X']],-1)

    def test_invalid_inputs(self):
        for start,goal,grid in [((0,0),(0,0),[]),((0,0),(0,0),[[]]),
                ((0,0),(0,0),[['.'],['.','.']]),((-1,0),(0,0),[['.']]),
                ((0,0),(1,0),[['.']]),([0,0],(0,0),[['.']]),
                ((0,0),(0,0),[['?']])]:
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                astar_maze(start,goal,grid)
        with self.assertRaises(ValueError):
            astar_maze((0,0),(0,0),[['.']], 'unknown')

    def test_seeded_maps_against_bfs(self):
        rng = random.Random(20261015)
        for case in range(150):
            grid = [['X' if rng.random()<0.3 else '.' for _ in range(6)] for _ in range(5)]
            grid[0][0],grid[4][5]='S','E'
            with self.subTest(case=case):
                self.check_case((0,0),(4,5),grid,bfs_cost((0,0),(4,5),grid))


if __name__ == '__main__':
    unittest.main()
