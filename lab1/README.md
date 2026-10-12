# 实验一：基于 TF-IDF 的文本十分类

比较多项式朴素贝叶斯、线性核 SVM 和逻辑回归，在相同验证集上进行参数与特征对照，最后生成无标签测试集预测。

## 运行

本次使用 Python 3.12.14；建议 Python 3.12，依赖版本见 `requirements.txt`。从老师提供的 `data-Project1.zip` 中取出 `train_data.csv` 和 `test_data_unlabeled.csv`，放到 `data/` 下。原始数据不上传 GitHub。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

也可指定路径：

```bash
python main.py --data-dir /path/to/data --output-dir results_new
```

程序支持 CPU 运行，不需要 GPU 或额外数据下载。程序逐配置打印 JSON 结果；运行结束时打印 `DONE`。相同环境下预测应可复现，耗时会随机器和负载变化。

## 实验设计

- 使用分层 80/20 划分，主实验随机种子为 42；每个配置使用完全相同的划分。
- TF-IDF 基线：最多 20,000 个特征，`min_df=2`，单词 unigram，默认小写和 L2 归一化；不额外删除停用词。
- NB 的 `alpha` 和 SVM、LR 的 `C` 都比较 0.1、1、10。SVM 使用 `LinearSVC(max_iter=5000)`，默认 L2 正则化、squared hinge 损失和 one-vs-rest 多分类；LR 使用 `max_iter=2000`。
- 初次尝试参考实现 `SVC(kernel='linear', C=0.1)`，运行约两分钟仍未完成该配置的训练和评估，因时间成本终止。正式实验统一改用 LinearSVC；二者损失和多分类策略不同，不混用结果，未完成尝试不计入性能表。
- 以验证准确率为主指标、Macro-F1 为次指标。先确定基线最佳模型和参数，再固定它们进行特征对照。
- 分别尝试 unigram+bigram、次线性 TF、移除部分邮件头；另比较 bigram 与次线性 TF 的组合。特征上限保持一致，因此 bigram 结果包含同一维度预算下的词表竞争影响。
- 头部清洗保留 Subject，只处理识别到邮件头的文本；不删除正文引用、签名，也不声称完成了全部噪声清洗。
- 将基线最佳配置和最终候选在种子 17、2026 下重复划分评估，仅检查敏感性，不用这两次结果继续搜索参数。这些重划分复用了同一数据集，不构成独立测试。
- 每次先划分数据，再在训练部分拟合词表和 IDF。验证集只用于选择，不参与该次拟合。最终配置锁定后，在全部有标签数据上重新拟合特征和模型。
- 无标签测试集仅做格式检查和最终预测，不参与参数选择；没有测试准确率。

## 输出

`results/` 中包括：

- `experiments.csv`：9 组模型参数和 4 组特征对照；包含训练/验证指标、耗时、特征维度和警告。
- `sensitivity.csv`：候选配置在另外两个种子下的结果。
- `selection.json`、`final_training.json`：选定配置与最终训练摘要。
- `split_seed42.csv`、`validation_predictions.csv`：原始零起始行号、划分和逐样本验证预测。
- `classification_report.json`、`confusion_matrix.csv/png`、`parameter_comparison.png`：分类指标与图表。
- `errors.csv`：验证集错分样本，仅本地分析，不随公开代码包上传原始正文。
- `data_audit.json`：数据摘要、SHA-256 和实际运行环境。
- `prediction.csv`：2,457 行，单列，无表头和索引，顺序对应原测试集。

最终课程提交包中仅放两页以内的报告 PDF 和 `prediction.csv`，不套外层目录。报告首页必须填入真实 GitHub 仓库链接。代码包与课程提交包用途不同。

`build_report.py` 是可选的报告排版脚本，不影响实验运行。它另需 `reportlab==4.4.9` 以及支持中文的 TrueType 字体，通过 `--font` 指定字体路径、`--repo` 指定真实仓库 URL。提供的 `report_text.md` 用于查看报告文字，PDF 是排版版本。

## 解释范围

所给材料没有标签编号与新闻类别名称的映射，统一使用类别 0～9。主验证集被反复用于模型选择，最高验证分数可能乐观。文本之间的近重复、同主题讨论线程未做完整分组识别，随机分层划分不能排除这些相关性。
