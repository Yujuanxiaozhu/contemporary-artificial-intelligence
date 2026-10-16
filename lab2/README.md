# Experiment 2 - Search Algorithms

当代人工智能实验课实验二：实现A*、Minimax、Alpha-Beta，并结合寻路与博弈搜索解决竞争宝藏分配。

姓名：刘毅　学号：10245501453

## 实现与结构

| 题目 | 实现 | 官方结果 |
| --- | --- | --- |
| 迷宫寻路 | src/astar.py：astar_maze | 最短7步 |
| 加权地形 | src/astar.py：astar_weighted | 最小费用7，进入E免费 |
| 给定博弈树 | src/minimax.py | Minimax与Alpha-Beta均为5 |
| 竞争宝藏分配 | src/treasure_game.py | H=2为T2/-1，H=4为T3/3 |

```text
lab2/
├─ main.py
├─ src/           四题算法与统一统计
├─ tests/         62个自动测试
├─ experiments/   样例、独立参考算法、可复现实验和报告工具
├─ results/       正式实验数据与分析素材
└─ report/        五页提交报告、完整长版和四张SVG
```

## 环境

核心算法和实验脚本只依赖Python标准库，不需要pip安装。
题一、二的初次20个测试在Python 3.11.9验证；后续四题62个测试与正式实验在Python 3.12.14验证。两者不是所有测试都完整执行过的两个环境。
建议使用Python 3.12，从本目录执行以下命令。

## 运行四题

```bash
python main.py --question 1
python main.py --question 2
python -m experiments.q3_baseline --output-dir results/q3_rerun
python -m experiments.q4_baseline --output-dir results/q4_rerun
```

Q3默认按原始children顺序搜索；顺序对照另明确区分理论较优排序。
Q4按A、B、T1、T2、T3、T4顺序输出完整距离矩阵；A/B/T格进入费用均为1，不能沿用Q2终点免费的规则。

## 测试与报告检查

```bash
python -m unittest discover -s tests -v
python -m experiments.report_final_audit
```

报告检查核对长版和五页版的源数据表、SVG XML、资源、作者信息及关键结果，并实际运行62个测试。PDF通过其内容哈希与已验证页数记录核对，结果写入results/final_audit.json。
测试包含边界情况、独立BFS/Dijkstra/Bellman-Ford对照、固定种子随机树与博弈状态一致性检查。

## 复现实验数据

```bash
python -m experiments.report_benchmarks --map-repeats 31 --search-repeats 1001 --cache-repeats 101 --output-dir results/report_data_rerun
```

正式保存的数据在results/report_data/：输入、种子、每次时间和汇总均保留。新计时建议写入独立目录；相同输入的最优费用和逻辑节点数应相同，运行时间会有噪声。

如需重新生成正式目录的摘要或检查其原始时间：

```bash
python -m experiments.report_materials
python -m experiments.report_audit
```

节点数取单次逻辑执行；时间以重复运行的中位数比较。Q3理论较优排序使用完整Minimax值，准备时间另列；Q4实际排序只根据当前即时收益。
缓存对照区分已有表后的搜索、首次完整预计算加搜索、无缓存重新A*，避免漏计首次成本。

## 报告

- [Markdown主稿](report/experiment2_report.md)
- [HTML浏览版](report/experiment2_report.html)
- [正式提交PDF（5页）](report/experiment2_report.pdf)
- [完整长版Markdown](report/experiment2_report_full.md)、[HTML](report/experiment2_report_full.html)、[PDF（12页）](report/experiment2_report_full.pdf)
- [四张SVG](report/assets/)
- [表图来源索引](report/data_reference.md)
- [正式数据摘要](results/report_data/summary.md)

正式提交版按最新不超过5页的要求重组，第一页显示仓库完整URL，代码位于lab2/。完整长版保留详细讨论和四张图。
从已有数据重新生成正式提交版Markdown和HTML：

```bash
python -m experiments.build_submission_report
```

短版文字源在report/submission_text.md，9张数据表由正式CSV/JSON生成。
重新生成完整长版Markdown、HTML和四张SVG（不会覆盖提交版）：

```bash
python -m experiments.build_report
```

生成器使用已有正式结果，不进行新性能测量。PDF由已有本地浏览器离线打印对应HTML生成；重新编辑后须再次导出、读取实际页数并逐页检查，提交版必须不超过5页。课程ZIP只需该PDF，代码和数据继续保留在本仓库。
