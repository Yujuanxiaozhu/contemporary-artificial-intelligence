# 实验三：CIFAR-10 图像分类

用 PyTorch 训练一个六层卷积网络，以单因素对照比较有无训练增强。官方训练集按类别固定抽取 500 张为验证集，剩余 45,000 张用于训练；官方 10,000 张测试集仅用于评估验证表现最佳的模型。

## 环境

使用 Python 3.11。建议在虚拟环境中安装依赖。以下命令从本目录运行：

```bash
python -m venv .venv
# 先激活环境：Windows PowerShell: .venv\Scripts\Activate.ps1；Linux: source .venv/bin/activate
# 有 NVIDIA GPU 时，先安装与驱动匹配的 PyTorch（此处为 CUDA 12.8）：
python -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
```

CPU 用户可改用 PyTorch 的 CPU 索引 `https://download.pytorch.org/whl/cpu` 安装前两项；完整训练在 CPU 上会明显较慢。若已有 [CIFAR-10 Python 版](https://www.cs.toronto.edu/~kriz/cifar.html)，将 `cifar-10-batches-py/` 放在 `data/` 下并省略 `--download`。归档 `cifar-10-python.tar.gz` 的 MD5 为 `c58f30108f718f92721af3b95e74349a`。

## 复现

```bash
python -m unittest -v
python train.py --data-dir data --run-dir runs/smoke --download --smoke
python train.py --data-dir data --run-dir runs/main --epochs 22 --batch-size 256 --seed 42 --lr 0.002 --weight-decay 0.01
python audit.py --run-dir runs/main
python visualize.py --data-dir data --run-dir runs/main
```

`--smoke` 只用小样本做一轮端到端检查，不产生可用于报告的正式结果。每次完整运行请指定新的输出目录；默认自动使用 CUDA（开启 FP16 混合精度）或 CPU。可用 `--device cpu` 或 `--no-amp` 覆盖。脚本固定划分、初始化、批次顺序和增强随机种子，并开启确定性算法；不同设备、软件版本或精度下仍可能有差异。

- 输入处理：像素转浮点除以 255，再按训练划分计算的通道均值与标准差归一化；仅增强组在训练时使用反射填充 4 像素后随机裁剪和概率 0.5 的水平翻转。
- 网络：三个卷积块，通道 48/96/192，每块含两次 `Conv3×3 → BatchNorm → ReLU` 和一次 2×2 最大池化；最后是全局平均池化、Dropout(0.2)、10 类线性层。
- 优化：交叉熵、AdamW、逐轮余弦退火；除训练增强外，两组的设置相同。每组先按验证准确率最高（相同时损失最低）保存检查点，再用同一规则选组，最后只测试选中检查点。
- 输出：两组的 `history.csv`、`config.json` 和 `checkpoint.pt`，加上 `test.json`（混淆计数、逐类准确率、错误索引及最大 softmax 概率）、训练曲线、混淆矩阵和误分样本图。检查点与数据集不随源码提交。

## 实测结果

使用 RTX 4070 Laptop GPU、PyTorch 2.8.0+cu128 和 AMP，两组各训练 22 轮：

| 方案 | 最佳轮次 | 验证准确率 | 验证交叉熵 |
| --- | ---: | ---: | ---: |
| 基线 | 21 | 86.92% | 0.5224 |
| 随机裁剪 + 水平翻转 | 21 | 89.88% | 0.3129 |

选中增强组第 21 轮权重后，在官方测试集得到 **88.32%（8,832 / 10,000）**，交叉熵 0.3398。基线未跑官方测试，2.96 个百分点是这一次对照的验证集差值，不是测试增益。

## 生成实验报告

完成正式训练、审计和绘图后，可用以下命令生成报告。`observations.tsv` 为 UTF-8 文本，每行以制表符分隔测试索引与该图的观察；索引见 `error_examples.json`。如默认找不到可嵌入的中文字体，用 `--font` 指定中文 `.ttf` 或 `.ttc` 路径。

```bash
python build_report.py --run-dir runs/main --output runs/main/report.pdf --observations observations.tsv --author "姓名 学号"
```

实验代码、可视化和报告初稿有 AI 辅助。若用于课程提交，请自行复现实验、核对误分样本并遵循课程关于独立完成和 AI 使用的规定。
