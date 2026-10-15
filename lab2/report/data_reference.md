# 报告表图来源索引

本文件用于维护报告，不是正式报告正文。路径相对本文件所在report目录。
报告所有性能数字采用现有results/report_data正式采集结果，未重新测量或替换。CSV时间字段单位为秒，报告乘1000并保留4位小数作为ms；组中位数的生成过程见run_config.json与各timings.csv。

| 报告项目 | 原始来源 | 选择与处理 |
| --- | --- | --- |
| 表1 环境 | ../results/report_data/run_config.json、../README.md | 初次Q1/2与完整四题的验证范围分开说明；正式运行版本另见../results/report_data/run_config.json |
| 表2 指标 | ../src/metrics.py、../src/astar.py、../src/minimax.py、../src/treasure_game.py | 按源码的计数时点描述，不混合expanded/visited |
| 表3 Q1规模/密度 | ../results/report_data/q1/summary.csv | 五个随机配置，zero/manhattan，费用与expanded的median；每配置10实例 |
| 表4 Q2随机图 | ../results/report_data/q2/summary.csv | 20/40尺寸，zero/admissible；费用、expanded及时间median |
| 表5 Q3官方树 | ../results/report_data/q3/results.csv | case=official，原Minimax及AB三顺序；visited/leaf/prune_events |
| 表6 Q3自设树 | ../results/report_data/q3/results.csv | b3_d4、b3_d6；值和各方法叶评估数 |
| 表7 地标 | ../experiments/q4_cases.py | 坐标、价值逐项对应课程PDF第14页 |
| 表8 距离矩阵 | ../results/report_data/q4/distance_matrix.json | 按labels顺序直接使用matrix；36项独立验证另见../results/q4_astar_pairs.csv |
| 表9 四首步 | ../results/report_data/q4/decision_branches.csv | first_move×depth=2/4的精确Minimax分支值与初始Gain |
| 表10 Q4搜索 | ../results/report_data/q4/results.csv | 8组正式数据，首步、值、visited、median_elapsed_time |
| 表11 实际排序 | ../results/report_data/q4/results.csv | algorithm=alphabeta且order为original/practical；不改统计口径 |
| 表12 缓存 | ../results/report_data/q4/cache_comparison.csv | 3个计时范围分列，不以复用时间冒充首次使用 |
| 图1 q1_expanded.svg | ../results/report_data/q1/summary.csv | 20%障碍、20/40/80尺寸、median_expanded_nodes |
| 图2 q3_ordering.svg | ../results/report_data/q3/results.csv | 自设depth4/6；Minimax原顺序与AB三顺序的visited_nodes |
| 图3 q4_architecture.svg | ../src/treasure_game.py | 结构示意，不含新测量数字；对应地图→距离→状态→搜索 |
| 图4 q4_search_nodes.svg | ../results/report_data/q4/results.csv | H2/H4每4组的visited_nodes |

## 正文其他数字

- Q1官方路径与16/13：../experiments/cases.py、../results/report_data/q1/summary.csv。
- Q1规模的绝对节省88.5、467、1789.5：表3中两个扩展中位数直接相减，不是逐实例节省的中位数。
- Q2官方费用7与费用路径：课程PDF第7页、../experiments/cases.py、../results/report_data/q2/summary.csv。
- Q2反例与安全下界：../results/report_data/q2/heuristic_counterexample.json；零权回退行为见../src/astar.py。
- Q2最小普通权1、40图起点估计77：../results/report_data/q2/inputs.json；费用组中位数284.5见summary.csv。
- Q3叶值/结构/种子：../results/report_data/q3/custom_trees.json；理论较优准备9.0229ms、搜索0.0921ms来自results.csv的b3_d6/alphabeta/favorable行。
- Q4两条具体行动链：../results/q4_decision_trace.md、../results/report_data/q4/decision_branches.csv；全部B回应见min_responses.csv。
- practical的H2时间0.0367/0.0369ms、H4时间0.1359/0.1272ms来自Q4正式results.csv，不混入缓存批次的时间。
- 距离准备1.1828ms与36次调用、329次扩展：../results/report_data/q4/precomputation.json。
- 缓存三组的65节点/24叶与0/64/36次A*：cache_comparison.csv；每次时间见cache_timings.csv。
- 总计62 tests passed：../results/final_audit.json；原62个测试的源码未改变。

## 检查与生成

experiments/build_report.py读取这些CSV/JSON形成12张表，图1/2/4在SVG metadata中保留所用数据，图中柱顶标明数值。HTML仅由同一Markdown生成，资源均为相对路径，不引用网络字体、脚本或图片。
内容检查先于表达修改；修改记录在../results/report_review.json。最终资源、数字表格、XML、关键结果检查记录于../results/final_audit.json。
