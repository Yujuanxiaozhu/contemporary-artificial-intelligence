"""题四独立距离验证、手算状态、随机博弈及旧语义隔离。"""
from dataclasses import FrozenInstanceError
import random
import unittest
from unittest.mock import patch

from experiments.q4_cases import Q4_GRID, Q4_LANDMARKS, Q4_VALUES
from experiments.q4_reference import dijkstra_distance, verify_distances
from src.astar import astar_weighted
from src.treasure_game import (ACTION_ORDERS, DistanceTable, GameState, TreasureGame,
    astar_distance, precompute_distances, minimax_treasure, alphabeta_treasure)


def reference_decision(game, state, depth):
    # 独立穷举：不调用生产 transition/gain/actions/utility 或任一博弈算法。
    def solve(pa, pb, remaining, sa, sb, player, limit):
        if limit == 0 or not remaining:
            return sa-sb, (None,)
        values = {}
        for target in remaining:
            rest = tuple(t for t in remaining if t != target)
            if player == 'A':
                gain = game.values[target]-game.distances.distance(pa,target)
                values[target] = solve(target,pb,rest,sa+gain,sb,'B',limit-1)[0]
            else:
                gain = game.values[target]-game.distances.distance(pb,target)
                values[target] = solve(pa,target,rest,sa,sb+gain,'A',limit-1)[0]
        best = (max if player=='A' else min)(values.values())
        return best, tuple(t for t,v in values.items() if v==best)
    return solve(state.position_a,state.position_b,state.remaining_treasures,
                 state.score_a,state.score_b,state.current_player,depth)


def full_counts(n, depth):
    if depth==0 or n==0:
        return 1,1
    nodes,leaves=full_counts(n-1,depth-1)
    return 1+n*nodes,n*leaves


class DistanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table=precompute_distances(Q4_GRID,Q4_LANDMARKS)

    def test_official_map_and_landmarks(self):
        self.assertEqual((len(Q4_GRID),{len(r) for r in Q4_GRID}),(7,{7}))
        self.assertEqual(Q4_VALUES,{'T1':9,'T2':6,'T3':7,'T4':7})
        self.assertEqual(Q4_LANDMARKS,{'A':(0,0),'B':(6,6),'T1':(0,6),
                                    'T2':(2,2),'T3':(4,4),'T4':(6,0)})
        for label,(r,c) in Q4_LANDMARKS.items():
            self.assertEqual(Q4_GRID[r][c],label)
        self.assertEqual(Q4_GRID[1][2],6)
        self.assertEqual(Q4_GRID[3][3],8)
        self.assertEqual(Q4_GRID[5][2],9)

    def test_matrix_shape_labels_diagonal_reachability(self):
        table=self.table
        self.assertEqual(table.labels,('A','B','T1','T2','T3','T4'))
        self.assertEqual(len(table.matrix),6)
        for i,row in enumerate(table.matrix):
            self.assertEqual(len(row),6)
            self.assertEqual(row[i],0)
            self.assertTrue(all(v>=0 for v in row))
        self.assertGreaterEqual(table.distance_precomputation_time,0)

    def test_all_36_pairs_independent_dijkstra(self):
        self.assertEqual(verify_distances(self.table,Q4_GRID,Q4_LANDMARKS),36)

    def test_every_special_cell_cost_one_and_no_q2_rule(self):
        for label in ('A','B','T1','T2','T3','T4'):
            with self.subTest(label=label):
                self.assertEqual(astar_distance((0,0),(0,1),((1,label),)),1)
        self.assertEqual(astar_distance((0,0),(0,1),((2,7),)),7)
        self.assertEqual(astar_weighted((0,0),(0,1),(('S','E'),)),0)

    def test_obstacles_unreachable_and_detour(self):
        self.assertEqual(astar_distance((0,0),(0,2),(('A','X','T1'),)),-1)
        grid=(('A','X','T1'),(1,1,1))
        self.assertEqual(astar_distance((0,0),(0,2),grid),4)
        self.assertEqual(astar_distance((0,0),(0,1),(('X','T1'),)),-1)

    def test_same_endpoint_and_actual_directional_costs(self):
        self.assertEqual(astar_distance((0,0),(0,0),(('A',),)),0)
        table=precompute_distances(((2,5),),{'left':(0,0),'right':(0,1)})
        self.assertEqual(table.matrix,((0,5),(2,0)))
        # 任意数值端点不强制对称；官方特殊端点均为1，结果才恰好对称。

    def test_other_treasure_and_player_do_not_block(self):
        grid=(('A','T1','B','T2'),)
        self.assertEqual(astar_distance((0,0),(0,3),grid),3)
        table=precompute_distances(grid,{'A':(0,0),'B':(0,2),'T1':(0,1),'T2':(0,3)})
        game=TreasureGame(table,{'T1':4,'T2':2})
        state=game.transition(game.initial_state(),'T2')
        self.assertEqual(state.remaining_treasures,('T1',))
        self.assertEqual(state.position_a,'T2')
        self.assertEqual(game.distances.distance('A','T2'),3)

    def test_precomputation_calls_astar_once_per_pair(self):
        with patch('src.treasure_game.astar_distance',wraps=astar_distance) as run:
            table=precompute_distances(Q4_GRID,Q4_LANDMARKS)
            self.assertEqual(run.call_count,36)
        self.assertEqual(table.matrix,self.table.matrix)
        self.assertEqual(len(table.pair_stats),6)

    def test_seeded_weighted_grids_against_dijkstra(self):
        rng=random.Random(20261015)
        for case in range(80):
            grid=[[('X' if rng.random()<0.25 else rng.randint(1,9)) for _ in range(5)] for _ in range(4)]
            grid[0][0],grid[3][4]='A','T1'
            with self.subTest(case=case):
                self.assertEqual(astar_distance((0,0),(3,4),grid),
                                 dijkstra_distance(grid,(0,0),(3,4)))

    def test_invalid_path_inputs(self):
        for grid in ([],[[]],[[1],[1,2]],[['A',0]],[['A',-1]],[['A',True]],
                     [['A','E']],[['A','?']]):
            with self.subTest(grid=grid),self.assertRaises(ValueError):
                astar_distance((0,0),(0,0),grid)
        with self.assertRaises(ValueError):
            astar_distance((-1,0),(0,0),[['A']])
        with self.assertRaises(ValueError):
            precompute_distances([['A']],{})


class TreasureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table=precompute_distances(Q4_GRID,Q4_LANDMARKS)
        cls.game=TreasureGame(cls.table,Q4_VALUES)
        table=precompute_distances((('A','T1','B','T2'),),
              {'A':(0,0),'B':(0,2),'T1':(0,1),'T2':(0,3)})
        cls.small=TreasureGame(table,{'T1':4,'T2':2})

    def check_case(self,game,state,depth):
        expected,optimal=reference_decision(game,state,depth)
        before=(state,game.distances.matrix,dict(game.values))
        for order in ACTION_ORDERS:
            for algorithm in (minimax_treasure,alphabeta_treasure):
                with self.subTest(order=order,algorithm=algorithm.__name__):
                    result,stats=algorithm(game,depth,state,order,return_stats=True)
                    self.assertEqual(result['best_value'],expected)
                    self.assertIn(result['best_target'],optimal)
                    if len(optimal)==1:
                        self.assertEqual(result['best_target'],optimal[0])
                    nodes,leaves=full_counts(len(state.remaining_treasures),depth)
                    if algorithm is minimax_treasure:
                        self.assertEqual((stats.visited_nodes,stats.evaluated_leaf_nodes),(nodes,leaves))
                        self.assertEqual((stats.prune_events,stats.pruned_children),(0,0))
                    else:
                        self.assertLessEqual(stats.visited_nodes,nodes)
                        self.assertLessEqual(stats.evaluated_leaf_nodes,leaves)
                    self.assertEqual(stats.prune_count,stats.pruned_children)
                    self.assertGreaterEqual(stats.elapsed_time,0)
                    self.assertEqual(before,(state,game.distances.matrix,dict(game.values)))

    def test_official_h2(self):
        for algorithm in (minimax_treasure,alphabeta_treasure):
            self.assertEqual(algorithm(self.game,2),{'best_target':'T2','best_value':-1})
        self.check_case(self.game,self.game.initial_state(),2)

    def test_official_h4(self):
        for algorithm in (minimax_treasure,alphabeta_treasure):
            self.assertEqual(algorithm(self.game,4),{'best_target':'T3','best_value':3})
        self.check_case(self.game,self.game.initial_state(),4)

    def test_official_single_run_counts_all_orders(self):
        expected={2:{'original':(13,8,2,4),'practical':(11,6,3,6),'unfavorable':(16,11,1,1)},
                  4:{'original':(47,16,5,6),'practical':(37,12,6,8),'unfavorable':(53,19,2,3)}}
        for depth in (2,4):
            for order in ACTION_ORDERS:
                _,stats=alphabeta_treasure(self.game,depth,order=order,return_stats=True)
                self.assertEqual((stats.visited_nodes,stats.evaluated_leaf_nodes,
                                  stats.prune_events,stats.pruned_children),expected[depth][order])

    def test_hand_computable_two_treasures_both_players(self):
        # A->T1:4-1=3，B->T2:2-1=1，所以 A 首选 T1 的 U=2。
        self.assertEqual(minimax_treasure(self.small,2),{'best_target':'T1','best_value':2})
        state=GameState('A','B',('T1','T2'),current_player='B')
        self.assertEqual(minimax_treasure(self.small,2,state),{'best_target':'T1','best_value':-4})
        self.check_case(self.small,self.small.initial_state(),2)
        self.check_case(self.small,state,2)

    def test_single_treasure_a_and_b(self):
        self.check_case(self.small,GameState('A','B',('T1',)),1)
        state=GameState('A','B',('T1',),7,2,'B')
        self.assertEqual(minimax_treasure(self.small,1,state),{'best_target':'T1','best_value':2})
        self.check_case(self.small,state,1)

    def test_transition_gain_scores_positions_and_remaining(self):
        initial=self.game.initial_state()
        self.assertEqual(self.game.gain(initial,'T2'),2)
        after_a=self.game.transition(initial,'T2')
        self.assertEqual(after_a,GameState('T2','B',('T1','T3','T4'),2,0,'B'))
        after_b=self.game.transition(after_a,'T3')
        self.assertEqual(after_b,GameState('T2','T3',('T1','T4'),2,3,'A'))
        self.assertEqual(after_b.utility,-1)
        self.assertEqual(initial.remaining_treasures,('T1','T2','T3','T4'))
        alternative=self.game.transition(initial,'T1')
        self.assertEqual(alternative.remaining_treasures,('T2','T3','T4'))
        with self.assertRaises(FrozenInstanceError):
            initial.score_a=99

    def test_collected_treasure_remains_traversable(self):
        initial=self.game.initial_state()
        after=self.game.transition(initial,'T2')
        # 固定地形和距离表不随收集改变；两玩家都能经过该坐标。
        self.assertIs(self.game.distances,self.table)
        self.assertEqual(self.game.distances.distance('A','T2'),4)
        self.assertNotIn('T2',after.remaining_treasures)

    def test_negative_gain_and_utility(self):
        game=TreasureGame(self.small.distances,{'T1':0,'T2':0})
        result=minimax_treasure(game,1)
        self.assertEqual(result,{'best_target':'T1','best_value':-1})
        self.check_case(game,game.initial_state(),2)

    def test_depth_zero_and_no_remaining(self):
        for state,depth in ((GameState('A','B',('T1',),7,2,'B'),0),
                            (GameState('A','B',(),7,2,'A'),4)):
            for algorithm in (minimax_treasure,alphabeta_treasure):
                result,stats=algorithm(self.small,depth,state,return_stats=True)
                self.assertEqual(result,{'best_target':None,'best_value':5})
                self.assertEqual((stats.visited_nodes,stats.evaluated_leaf_nodes),(1,1))

    def test_depth_exceeds_remaining(self):
        state=GameState('A','B',('T1','T2'))
        self.check_case(self.small,state,9)
        for algorithm in (minimax_treasure,alphabeta_treasure):
            self.assertEqual(algorithm(self.small,9,state),algorithm(self.small,2,state))

    def test_action_order_direction_both_players(self):
        state=self.game.initial_state()
        self.assertEqual(self.game.actions(state),['T1','T2','T3','T4'])
        self.assertEqual(self.game.actions(state,'practical'),['T2','T1','T3','T4'])
        self.assertEqual(self.game.actions(state,'unfavorable'),['T1','T3','T4','T2'])
        for player in ('A','B'):
            state=GameState('A','B',('T4','T2','T1','T3'),current_player=player)
            for order,reverse in (('practical',True),('unfavorable',False)):
                actions=self.game.actions(state,order)
                gains=[self.game.gain(state,t) for t in actions]
                self.assertEqual(gains,sorted(gains,reverse=reverse))
                self.assertEqual(set(actions),set(state.remaining_treasures))

    def test_ties_keep_first_visited_optimum(self):
        game=TreasureGame(self.small.distances,{'T1':1,'T2':3})
        # A 的两个单步 gain 都是0，默认保留原顺序第一个。
        for algorithm in (minimax_treasure,alphabeta_treasure):
            self.assertEqual(algorithm(game,1),{'best_target':'T1','best_value':0})
        self.check_case(game,game.initial_state(),1)

    def test_search_never_calls_astar_or_precomputation(self):
        with patch('src.treasure_game.astar_distance',side_effect=AssertionError('A* in game search')):
            with patch('src.treasure_game.precompute_distances',side_effect=AssertionError('precompute in search')):
                self.check_case(self.game,self.game.initial_state(),4)

    def test_invalid_game_inputs(self):
        for algorithm in (minimax_treasure,alphabeta_treasure):
            for depth in (-1,1.5,True):
                with self.assertRaises(ValueError):
                    algorithm(self.game,depth)
            with self.assertRaises(ValueError):
                algorithm(self.game,2,order='oracle')
            with self.assertRaises(ValueError):
                algorithm(self.game,2,GameState('?', 'B',('T1',)))
            with self.assertRaises(ValueError):
                algorithm(self.game,2,GameState('A','B',('T9',)))
        with self.assertRaises(ValueError):
            self.game.transition(self.game.initial_state(),'unknown')
        for arguments in (('A','B',('T1','T1')),('A','B',(),0,0,'C')):
            with self.assertRaises(ValueError):
                GameState(*arguments)
        with self.assertRaises(ValueError):
            TreasureGame(DistanceTable(('A','B','T1'),((0,-1,1),(1,0,1),(1,1,0))),{'T1':1})

    def test_seeded_random_states_independent_reference(self):
        rng=random.Random(20261015)
        treasures=tuple(Q4_VALUES)
        for case in range(200):
            values={t:rng.randint(-5,12) for t in treasures}
            game=TreasureGame(self.table,values)
            remaining=tuple(t for t in treasures if rng.random()<0.65)
            state=GameState(rng.choice(self.table.labels),rng.choice(self.table.labels),remaining,
                            rng.randint(-10,10),rng.randint(-10,10),rng.choice(('A','B')))
            depth=rng.randint(0,6)
            with self.subTest(case=case):
                self.check_case(game,state,depth)


if __name__=='__main__':
    unittest.main()
