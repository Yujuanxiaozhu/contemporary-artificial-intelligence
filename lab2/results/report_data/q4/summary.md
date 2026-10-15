# Q4 正式实验素材

| H | 算法 | 顺序 | 首步/U | visited | leaf | events | pruned children | median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | minimax | original | T2/-1 | 17 | 12 | 0 | 0 | 0.044600 |
| 2 | alphabeta | original | T2/-1 | 13 | 8 | 2 | 4 | 0.036700 |
| 2 | alphabeta | practical | T2/-1 | 11 | 6 | 3 | 6 | 0.036900 |
| 2 | alphabeta | unfavorable | T2/-1 | 16 | 11 | 1 | 1 | 0.049100 |
| 4 | minimax | original | T3/3 | 65 | 24 | 0 | 0 | 0.170900 |
| 4 | alphabeta | original | T3/3 | 47 | 16 | 5 | 6 | 0.135900 |
| 4 | alphabeta | practical | T3/3 | 37 | 12 | 6 | 8 | 0.127200 |
| 4 | alphabeta | unfavorable | T3/3 | 53 | 19 | 2 | 3 | 0.176200 |

每组1001次；全部保持H=2为T2/-1，H=4为T3/3。距离预计算排除在搜索计时之外；实际practical排序计入搜索时间。
四首步素材在results/q4_decision_trace.md，排序素材在results/q4_ordering_analysis.md，缓存见本目录cache_analysis.md。
