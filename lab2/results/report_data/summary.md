# 正式实验报告数据摘要（非最终实验报告）

## 方法和环境

本阶段Python 3.12.14；所有原代码、测试、旧数据原样保留。matplotlib缺失，无安装或下载，不生成PNG。
计数取单次执行；计时两次预热后重复取median，组内方法循环轮换先后。地图31次，小树/博弈1001次，缓存/准备101次，组内相同次数；Q3排序准备31次。
地图时间先每实例取median再组内10图取median；数据生成和独立验证排除，生产算法自己的检查/启发计算保留。Q3 oracle准备单列，Q4实际practical排序计入搜索。
BFS/Dijkstra独立核对所有接受输入费用，Q3用独立穷举定义核对值，Q4官方值和全部36个距离仍核对。所有重复执行检查结果/节点不变。

## Q1

| 组 | h | n | cost mean/median | expanded median [min,max] | expanded IQR | generated median | time median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| official | zero | 1 | 7/7 | 16 [16,16] | [16,16] | 18 | 0.029700 |
| official | manhattan | 1 | 7/7 | 13 [13,13] | [13,13] | 16 | 0.027400 |
| 20x20_p20 | zero | 10 | 38/38 | 320.5 [306,330] | [314.25,325.25] | 321.5 | 0.585500 |
| 20x20_p20 | manhattan | 10 | 38/38 | 232 [143,287] | [190.5,250.25] | 263.5 | 0.469700 |
| 40x40_p20 | zero | 10 | 78.2/78 | 1277 [1252,1300] | [1256.75,1294] | 1278.0 | 2.445100 |
| 40x40_p20 | manhattan | 10 | 78.2/78 | 810 [567,904] | [701.5,861.5] | 901.5 | 1.786750 |
| 80x80_p20 | zero | 10 | 158/158 | 5122.5 [5035,5177] | [5097.5,5149.75] | 5123.5 | 10.413700 |
| 80x80_p20 | manhattan | 10 | 158/158 | 3333 [2582,3543] | [3213,3414.75] | 3611.5 | 7.700150 |
| 40x40_p10 | zero | 10 | 78/78 | 1441 [1431,1470] | [1436.25,1458.25] | 1442.0 | 2.828250 |
| 40x40_p10 | manhattan | 10 | 78/78 | 1270 [1188,1402] | [1239,1291.5] | 1335.5 | 2.734850 |
| 40x40_p30 | zero | 10 | 80/80 | 1063.5 [1017,1097] | [1050.5,1075.75] | 1067.0 | 1.967200 |
| 40x40_p30 | manhattan | 10 | 80/80 | 400.5 [235,598] | [345.5,449] | 470.5 | 0.899550 |

## Q2

| 组 | h | n | cost mean/median | expanded median [min,max] | expanded IQR | generated median | time median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| official | zero | 1 | 7/7 | 14 [14,14] | [14,14] | 24 | 0.034800 |
| official | admissible | 1 | 7/7 | 10 [10,10] | [10,10] | 19 | 0.032600 |
| 20x20_p20 | zero | 10 | 134/132 | 311 [292,328] | [298.5,317] | 313.5 | 0.640000 |
| 20x20_p20 | admissible | 10 | 134/132 | 299 [250,322] | [291.5,311] | 316.5 | 0.726400 |
| 40x40_p20 | zero | 10 | 281.8/284.5 | 1256 [1236,1307] | [1244.25,1275.75] | 1260.5 | 2.818100 |
| 40x40_p20 | admissible | 10 | 281.8/284.5 | 1251.5 [1198,1295] | [1238.25,1274.25] | 1311.0 | 3.249400 |

| 题 | 组 | zero expanded median | heuristic expanded median | 中位数之比的下降 |
| --- | --- | --- | --- | --- |
| 1 | 20x20_p20 | 320.5 | 232.0 | 27.61% |
| 1 | 40x40_p10 | 1441.0 | 1270.0 | 11.87% |
| 1 | 40x40_p20 | 1277.0 | 810.0 | 36.57% |
| 1 | 40x40_p30 | 1063.5 | 400.5 | 62.34% |
| 1 | 80x80_p20 | 5122.5 | 3333.0 | 34.93% |
| 1 | official | 16 | 13 | 18.75% |
| 2 | 20x20_p20 | 311.0 | 299.0 | 3.86% |
| 2 | 40x40_p20 | 1256.0 | 1251.5 | 0.36% |
| 2 | official | 14 | 10 | 28.57% |

下降百分比为两个组内节点中位数之比，不是每实例降幅的median，也不是普遍保证。

## Q3

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

## Q4

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

## 首步分支值

| A首步 | 即时Gain | H=2最优MIN后U | H=4完整Minimax U |
| --- | --- | --- | --- |
| T1 | -1 | -4 | -5 |
| T2 | 2 | -1 | 1 |
| T3 | -1 | -2 | 3 |
| T4 | -1 | -4 | -7 |

## 缓存

| 模式 | target/U | A*次数 | 累计A*expanded | 累计A*generated | game visited | leaf | median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cached_reused_search | T3/3 | 0 | 0 | 0 | 65 | 24 | 0.181000 |
| uncached_search | T3/3 | 64 | 670 | 1049 | 65 | 24 | 2.806600 |
| cached_one_shot_total | T3/3 | 36 | 329 | 503 | 65 | 24 | 1.491400 |

预计算median另为1.182800ms；one-shot总时间已直接包含预计算。

## 文件入口

- q1/summary.md、q2/summary.md：地图表和E=0说明；inputs.json是完整输入，generation_attempts.csv包括拒绝记录。
- q3/summary.md：全部树/顺序，custom_trees.json是自设树；preparation_timings.csv含准备开销。
- q4/summary.md、q4/cache_analysis.md：综合题和缓存；每次计时保留在各timings.csv。
- ../q4_decision_trace.md、../q4_ordering_analysis.md：首步解释及practical事实素材。
- seeds.md、run_config.json：随机种子、环境、重复次数和范围。
- analysis_notes.md：报告建议结构对应的事实和限制。

不编写最终报告，不制作提交压缩包。
