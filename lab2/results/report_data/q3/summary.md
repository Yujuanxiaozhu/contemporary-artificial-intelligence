# Q3 正式剪枝素材

| 输入 | 算法 | 顺序 | value | visited | leaf | events | pruned children | median(ms) | 准备median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| official | minimax | original | 5 | 15 | 8 | 0 | 0 | 0.007400 | 0.048500 |
| official | alphabeta | original | 5 | 14 | 7 | 1 | 1 | 0.009400 | 0.048500 |
| official | minimax | favorable | 5 | 15 | 8 | 0 | 0 | 0.007500 | 0.072000 |
| official | alphabeta | favorable | 5 | 11 | 5 | 2 | 2 | 0.007800 | 0.072000 |
| official | minimax | unfavorable | 5 | 15 | 8 | 0 | 0 | 0.007400 | 0.068900 |
| official | alphabeta | unfavorable | 5 | 15 | 8 | 0 | 0 | 0.009800 | 0.068900 |
| b3_d4 | minimax | original | -11 | 121 | 81 | 0 | 0 | 0.058900 | 0.488200 |
| b3_d4 | alphabeta | original | -11 | 93 | 56 | 12 | 19 | 0.062900 | 0.488200 |
| b3_d4 | minimax | favorable | -11 | 121 | 81 | 0 | 0 | 0.058600 | 0.859200 |
| b3_d4 | alphabeta | favorable | -11 | 37 | 17 | 12 | 24 | 0.027100 | 0.859200 |
| b3_d4 | minimax | unfavorable | -11 | 121 | 81 | 0 | 0 | 0.058400 | 0.848700 |
| b3_d4 | alphabeta | unfavorable | -11 | 119 | 79 | 2 | 2 | 0.075900 | 0.848700 |
| b3_d6 | minimax | original | -14 | 1093 | 729 | 0 | 0 | 0.571800 | 4.610000 |
| b3_d6 | alphabeta | original | -14 | 359 | 197 | 73 | 128 | 0.254800 | 4.610000 |
| b3_d6 | minimax | favorable | -14 | 1093 | 729 | 0 | 0 | 0.569400 | 9.022900 |
| b3_d6 | alphabeta | favorable | -14 | 125 | 53 | 46 | 92 | 0.092100 | 9.022900 |
| b3_d6 | minimax | unfavorable | -14 | 1093 | 729 | 0 | 0 | 0.567000 | 9.329500 |
| b3_d6 | alphabeta | unfavorable | -14 | 1011 | 654 | 53 | 61 | 0.674400 | 9.329500 |

搜索1001次取median；复制/排序准备31次取median，排除在搜索时间外，original也有复制成本。
favorable/unfavorable均使用完整Minimax值进行正/反排序，属于oracle/theoretical对照，不是免费实际优化。
完整三叉树depth=4有121节点/81叶，depth=6有1093节点/729叶；同树Minimax三顺序访问数相同。
depth=6的Alpha-Beta原顺序359次、oracle较优125次、不利1011次。不利顺序仍可能发生剪枝。
完整自设树见custom_trees.json，仅两棵固定树，不代表所有输入。
