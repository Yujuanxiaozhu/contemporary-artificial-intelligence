# 距离缓存事实素材

全部为H=4、纯Minimax、original。无缓存类仅在experiments/report_support.py，共享正式转移/搜索；仅持有坐标/标签，不持有矩阵，每次Gain都实际跑A*。

| 模式 | target/U | A*次数 | 累计A*expanded | 累计A*generated | game visited | leaf | median(ms) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cached_reused_search | T3/3 | 0 | 0 | 0 | 65 | 24 | 0.181000 |
| uncached_search | T3/3 | 64 | 670 | 1049 | 65 | 24 | 2.806600 |
| cached_one_shot_total | T3/3 | 36 | 329 | 503 | 65 | 24 | 1.491400 |

一次预计算重复101次的median为1.182800ms，36次A*、累计expanded=329、generated=503。

reused仅测已有表的后续查询，准备成本单列，不能当成消失。one_shot_total外层直接计时，包含完整预计算、构建game和一次搜索；没有把两个median相加当成实测总时间。
uncached的65个访问对应64条行动边，各边跑一次A*。各模式决策、U和博弈访问量完全相同，缓存只减少距离获取的重复工作。
search-only两组已有game对象的初始化都排除；uncached带调用/节点计数，有少量记录开销。
同地图多个深度、算法或反复查询能复用一次矩阵。本次one-shot也低于uncached，但不推广到所有地图。重复预计算只是估计一次成本，不表示正式每次查询都重建。
