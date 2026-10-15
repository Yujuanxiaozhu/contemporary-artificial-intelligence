# Q4 practical ordering事实素材

| H | 算法 | 顺序 | 首步/U | visited | leaf | events | pruned children | median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | alphabeta | original | T2/-1 | 13 | 8 | 2 | 4 | 0.036700 |
| 2 | alphabeta | practical | T2/-1 | 11 | 6 | 3 | 6 | 0.036900 |
| 4 | alphabeta | original | T3/3 | 47 | 16 | 5 | 6 | 0.135900 |
| 4 | alphabeta | practical | T3/3 | 37 | 12 | 6 | 8 | 0.127200 |

按当前玩家自己的即时Gain降序，B自身Gain提高会降低U，因此B也降序。没有未来Minimax排序信息；每次排序成本包含在搜索时间。

- H=2：visited 13→11，leaf 8→6，events 2→3，pruned child 4→6；median 0.036700→0.036900 ms。
- H=4：visited 47→37，leaf 16→12，events 5→6，pruned child 6→8；median 0.135900→0.127200 ms。

本次H=2节点更少但时间略高，约0.2μs差值受排序开销和系统噪声影响，不下稳定速度结论；H=4节点与本次时间均下降。
practical是启发式，不保证任何地图、深度、状态都得到最大剪枝或更快。原始样本见report_data/q4/timings.csv。
