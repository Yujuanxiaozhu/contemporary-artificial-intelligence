"""Render the five-page CIFAR-10 lab report from completed run artifacts."""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
from collections import Counter
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import PDFError
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


URL = "https://github.com/Yujuanxiaozhu/contemporary-artificial-intelligence/tree/main/lab3"
VARIANTS = {"baseline": "基线", "augmented": "训练增强"}
ZH = dict(zip(
    "airplane automobile bird cat deer dog frog horse ship truck".split(),
    "飞机 汽车 鸟 猫 鹿 狗 青蛙 马 船 卡车".split(),
))
W, H = A4
M = 44
CW = W - 2 * M
INK = HexColor("#14283C")
TEXT = HexColor("#304661")
MUTED = HexColor("#526981")
TEAL = HexColor("#007D71")
PAPER = HexColor("#F6F9FC")
LINE = HexColor("#DFE8F1")
FONT = "Lab3CJK"


def register_font(choice: str, index: int) -> str:
    """Register an embeddable, TrueType-outline CJK font (including TTC)."""
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = {
        "simhei": [windows / "simhei.ttf"],
        "yahei": [windows / "msyh.ttc"],
        "cjk": [windows / "simsun.ttc",
                Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
                Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
                Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf")],
    }
    if choice == "auto":
        paths = [path for group in candidates.values() for path in group]
    else:
        paths = candidates.get(choice, [Path(choice).expanduser()])
    failures = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            font = TTFont(FONT, str(path), subfontIndex=index)
            if any(ord(ch) not in font.face.charWidths for ch in "卷积训练验证测试增强混淆"):
                raise ValueError("字体缺少报告所需的简体中文字形")
            pdfmetrics.registerFont(font)
            return path.name
        except (OSError, ValueError, IndexError, PDFError) as exc:
            failures.append(f"{path}: {exc}")
    extra = f"（{'；'.join(failures)}）" if failures else ""
    raise ValueError(f"没有可嵌入的中文字体{extra}；用 --font 指定中文 TrueType .ttf/.ttc 路径。")


def read_json(path: Path):
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def proportion(value, label: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise ValueError(f"{label} 应为 [0, 1] 内的小数：{value}")
    return number


def finite(value, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} 应为有限数值：{value}")
    return number


def quality(row) -> tuple[float, float]:
    return row["val_acc"], -row["val_loss"]


def best_epoch(rows):
    return max(rows, key=lambda row: (*quality(row), -row["epoch"]))


def read_history(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = [dict(epoch=int(row["epoch"]),
                     **{k: proportion(row[k], f"{path.name}:{k}") for k in ("train_acc", "val_acc")},
                     **{k: finite(row[k], f"{path.name}:{k}") for k in ("train_loss", "val_loss", "lr")})
                for row in csv.DictReader(f)]
    if not rows or len({r['epoch'] for r in rows}) != len(rows):
        raise ValueError(f"{path}: 历史为空或 epoch 重复")
    return sorted(rows, key=lambda r: r["epoch"])


def read_observations(path: Path | None) -> dict[int, str]:
    observations = {}
    if path is None:
        return observations
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        index, tab, note = line.partition("\t")
        if not tab or not note.strip():
            raise ValueError(f"{path}:{n}: 需要 index<TAB>实际视觉观察")
        key = int(index)
        if key in observations:
            raise ValueError(f"{path}:{n}: 重复的样本编号 {key}")
        observations[key] = note.strip()
    return observations


def load_run(root: Path, observations_path: Path | None) -> dict:
    histories = {name: read_history(root / name / "history.csv") for name in VARIANTS}
    configs = {name: read_json(root / name / "config.json") for name in VARIANTS}
    for name, cfg in configs.items():
        if (cfg["train_size"], cfg["val_size"]) != (45000, 5000):
            raise ValueError(f"{name}: 训练/验证规模应为 45,000 / 5,000")
        if any(len(cfg[k]) != 3 for k in ("mean", "std")):
            raise ValueError(f"{name}: mean 和 std 均须包含三个 RGB 通道值")
    winners = {name: best_epoch(rows) for name, rows in histories.items()}
    test = read_json(root / "test.json")
    selected = test["selected"]
    if selected not in VARIANTS:
        raise ValueError(f"test.json: 未知的入选方案 {selected!r}")
    if quality(winners[selected]) < max(map(quality, winners.values())):
        raise ValueError("test.json 的入选方案与历史中的验证准确率/损失排序不一致")
    if "selected_epoch" in test:
        candidates = [row for row in histories[selected] if row["epoch"] == test["selected_epoch"]]
        if not candidates or quality(candidates[0]) != quality(winners[selected]):
            raise ValueError("test.json 的入选轮次与历史中的验证准确率/损失排序不一致")
        winners[selected] = candidates[0]  # Preserve the actual choice on a complete tie.
    if test.get("smoke") or test.get("test_size", 10000) != 10000:
        raise ValueError("正式报告需要 10,000 张官方测试图像的非 smoke 运行")
    classes = test["classes"]
    if not isinstance(classes, list) or len(classes) != 10 or len(set(classes)) != 10:
        raise ValueError("test.json: classes 应为 10 个不同类别的有序列表")
    matrix = test["confusion"]
    if (len(matrix) != 10 or any(len(row) != 10 for row in matrix)
            or any(type(n) is not int or n < 0 for row in matrix for n in row)
            or sum(map(sum, matrix)) != 10000):
        raise ValueError("test.json: confusion 应为包含 10,000 个样本的 10×10 非负整数矩阵")
    if len(test["per_class_acc"]) != 10:
        raise ValueError("test.json: per_class_acc 应包含 10 项")
    per_class = [proportion(n, "per_class_acc") for n in test["per_class_acc"]]
    accuracy = proportion(test["test_acc"], "test_acc")
    loss = finite(test["test_loss"], "test_loss")
    if not math.isclose(accuracy, sum(matrix[i][i] for i in range(10)) / 10000, abs_tol=5.1e-5):
        raise ValueError("test.json: 整体准确率与混淆矩阵不一致")
    if any(not sum(row) or not math.isclose(a, row[i] / sum(row), abs_tol=5.1e-5)
           for i, (a, row) in enumerate(zip(per_class, matrix))):
        raise ValueError("test.json: 逐类别准确率与混淆矩阵不一致")
    examples = read_json(root / "error_examples.json")
    observed = read_observations(observations_path)
    for record in examples:
        for key in ("true", "pred"):
            if type(record[key]) is not int or not 0 <= record[key] < 10:
                raise ValueError(f"error_examples.json: 非法类别 {record[key]!r}")
        proportion(record["confidence"], "confidence")
    unknown_indices = observed.keys() - {r["index"] for r in examples}
    if unknown_indices:
        raise ValueError(f"观察文件包含不在图版中的样本编号：{sorted(unknown_indices)}")
    order = Counter({(i, j): n for i, row in enumerate(matrix) for j, n in enumerate(row)
                     if i != j and n})
    errors = test["errors"]
    if not isinstance(errors, list):
        raise ValueError("test.json: errors 应为误判记录列表")
    return dict(histories=histories, configs=configs, selected=selected, winners=winners,
                classes=classes, matrix=matrix, per_class=per_class, accuracy=accuracy,
                loss=loss, errors=len(errors), pairs=order, examples=examples, observations=observed,
                figures={key: ImageReader(str(root / f"{key}.png"))
                         for key in ("curves", "confusion", "errors")})


def pct(value) -> str:
    return f"{value:.2%}"


class Report:
    def __init__(self, output: Path, run: dict, font: str, author: str):
        self.c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
        self.c.setTitle("CIFAR-10 图像分类｜训练增强消融")
        self.c.setAuthor(author)
        self.r = run
        self.font = font
        self.author = author
        self.page = 0

    def box(self, x, y, w, h, fill=PAPER, radius=8):
        self.c.setFillColor(fill)
        self.c.roundRect(x, H - y - h, w, h, radius, stroke=0, fill=1)

    def rule(self, x, y, w, color=LINE):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(0.65)
        self.c.line(x, H - y, x + w, H - y)

    def line(self, text, y, *, x=M, size=11, color=INK, right=False):
        self.c.setFillColor(color)
        self.c.setFont(FONT, size)
        draw = self.c.drawRightString if right else self.c.drawString
        draw(x, H - y - size, str(text))

    def para(self, text, y, *, x=M, w=CW, size=11, leading=None, color=TEXT, draw=True):
        p = Paragraph(html.escape(str(text)), ParagraphStyle(
            "cjk", fontName=FONT, fontSize=size, leading=leading or size * 1.52,
            textColor=color, wordWrap="CJK", alignment=TA_LEFT,
        ))
        _, h = p.wrap(w, H)
        if draw:
            p.drawOn(self.c, x, H - y - h)
        return h

    def start(self, section, title, subtitle):
        self.page += 1
        self.line(f"LAB 03   /   CIFAR-10     ·     {section}", 32, color=TEAL, size=10)
        self.rule(M, 54, CW)
        self.line(title, 67, size=27)
        self.line(subtitle, 106, color=MUTED, size=10.5)

    def end(self):
        self.rule(M, 796, CW)
        self.line("当代人工智能  /  CIFAR-10 消融实验", 806, size=9, color=MUTED)
        self.line(f"{self.page:02d} / 05", 806, x=W - M, size=9, color=TEAL, right=True)
        self.c.showPage()

    def heading(self, title, y, x=M):
        self.line(title, y, x=x, size=14, color=TEAL)

    def label(self, i):
        name = self.r["classes"][i]
        return ZH.get(name.lower(), name)

    def image(self, key, x, y, w, h):
        img = self.r["figures"][key]
        iw, ih = img.getSize()
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        self.c.drawImage(img, x + (w - dw) / 2, H - y - (h + dh) / 2, dw, dh, mask="auto")

    def card(self, title, value, x, y, w, *, sub=None, size=22):
        self.box(x, y, w, 79)
        self.line(title, y + 9, x=x + 13, size=10, color=MUTED)
        self.line(value, y + 25, x=x + 13, size=size, color=TEAL)
        if sub:
            self.line(sub, y + 56, x=x + 13, size=9, color=TEXT)

    def table(self, headers, rows, widths, y, *, x=M, size=10, row_h=23):
        w = sum(widths)
        self.box(x, y, w, row_h, INK, radius=4)
        for n, row in enumerate([headers, *rows]):
            if n and n % 2:
                self.box(x, y, w, row_h, radius=3)
            dx = x
            for cell, width in zip(row, widths):
                self.line(cell, y + (row_h - size) / 2 - 1, x=dx + 8, size=size,
                          color=white if n == 0 else TEXT)
                dx += width
            y += row_h
        return y

    def cover(self):
        self.page = 1
        self.line(URL, 32, size=9.8, color=TEAL)
        link_width = pdfmetrics.stringWidth(URL, FONT, 9.8)
        self.rule(M, 45, link_width, TEAL)
        self.c.linkURL(URL, (M, H - 48, M + link_width, H - 30), relative=0, thickness=0)
        if self.author:
            self.line(self.author, 54, size=12)
        self.box(M, 90, CW, 217, INK, radius=14)
        self.line("LAB 03   /   课程实验报告", 111, x=M + 25, size=11, color=HexColor("#87E4D2"))
        self.line("CIFAR-10 图像分类", 141, x=M + 25, size=34, color=white)
        self.line("训练数据增强消融", 195, x=M + 25, size=26, color=white)
        self.para("固定网络和训练流程，仅比较是否在训练阶段进行随机裁剪与水平翻转。",
                  252, x=M + 26, w=CW - 52, size=11, color=HexColor("#D5E4F2"))
        w = (CW - 20) / 3
        for i, (label, value, sub) in enumerate([
            ("训练集", "45,000", "从官方训练集抽取"),
            ("验证集", "5,000", "按类别分层留出"),
            ("官方测试集", "10,000", "锁定方案与轮次后使用"),
        ]):
            self.card(label, value, M + i * (w + 10), 327, w, sub=sub)
        self.heading("01  /  模型路径", 439)
        self.para("输入为 32×32 的 RGB 图像。三个块依次使用 48、96、192 个输出通道；每个块均为两次 3×3 卷积、批归一化（BN）与 ReLU，随后接一次最大池化。",
                  469)
        xw = (CW - 20) / 3
        for i, channels in enumerate((48, 96, 192)):
            x = M + i * (xw + 10)
            self.box(x, 524, xw, 76)
            self.line(f"块 {i + 1}   /   {channels} 通道", 535, x=x + 10, size=12, color=TEAL)
            self.line("(Conv 3×3–BN–ReLU) × 2", 555, x=x + 10, size=9)
            self.line("最大池化", 572, x=x + 10, size=9)
        self.para("全局平均池化（GAP）→ Dropout（p = 0.2）→ 线性层（10 类 logits）。GAP 将每个通道汇聚成一个数值，使分类头无需展开整个空间特征图。",
                  622)
        self.rule(M, 682, CW)
        self.para("阅读顺序：实验配置 → 验证与选模 → 官方测试 → 误判分析与复现。", 703, color=MUTED)
        self.end()

    def settings(self):
        self.start("实验配置", "只改变训练数据增强", "相同的网络、划分与优化协议；验证与测试不做随机增强。")
        self.heading("预处理与训练协议", 147)
        y = 173
        for title, desc in (
            ("基线", "不做随机裁剪和镜像；将图像转换为张量，并使用训练划分的 RGB 均值与标准差逐通道标准化。"),
            ("训练增强", "先做反射填充（四周各 4 像素），随机裁剪回 32×32，以 p = 0.5 水平翻转，再使用训练划分的通道统计量标准化。"),
            ("评估与优化", "验证集和测试集均只做确定性预处理；训练使用 AdamW 优化器、余弦学习率调度和交叉熵损失。"),
        ):
            self.line(title, y, size=11, color=TEAL)
            h = self.para(desc, y - 1, x=M + 84, w=CW - 84, size=10.5)
            y += max(34, h + 11)
        self.heading("运行配置与环境（config.json）", 325)
        cfgs = self.r["configs"]
        rows = []
        for label, key, fmt in [
            ("随机种子", "seed", str), ("配置训练轮数", "epochs", str),
            ("批量大小", "batch_size", str), ("初始学习率", "lr", lambda v: f"{v:.6g}"),
            ("权重衰减", "weight_decay", lambda v: f"{v:.6g}"),
            ("训练 / 验证", "train_size", lambda v: f"{v:,} / 5,000"),
            ("均值（R, G, B）", "mean", lambda v: " / ".join(f"{n:.5f}" for n in v)),
            ("标准差（R, G, B）", "std", lambda v: " / ".join(f"{n:.5f}" for n in v)),
            ("参数量", "parameters", lambda v: f"{v:,}"),
            ("运行耗时", "seconds", lambda v: f"{v:,.1f} s"),
            ("设备", "device", str), ("PyTorch", "torch", str),
            ("自动混合精度 AMP", "amp", lambda v: "启用" if v is True else "关闭" if v is False else str(v)),
        ]:
            rows.append([label, *(fmt(cfg[key]) for cfg in cfgs.values())])
        mismatches = []
        # Time and runtime environment are reported above, not interpreted as treatment levels.
        for label, key in (("种子", "seed"), ("轮数", "epochs"), ("批量", "batch_size"),
                           ("初始学习率", "lr"), ("权重衰减", "weight_decay"),
                           ("均值", "mean"), ("标准差", "std"), ("参数量", "parameters"),
                           ("设备", "device"), ("PyTorch", "torch"), ("AMP", "amp")):
            if cfgs["baseline"][key] != cfgs["augmented"][key]:
                mismatches.append(label)
        y = self.table(["项目", *VARIANTS.values()], rows, [140, 181, CW - 321], 353, row_h=24)
        note = ("元数据还记录到以下差异，不能将结果差异完全归因于增强：" + "、".join(mismatches) + "。"
                if mismatches else "两组记录的种子、主要超参数、通道统计量、参数量及训练环境一致；训练耗时单独列出。")
        self.para(note, y + 16, size=10, color=MUTED)
        self.end()

    def validation(self):
        self.start("训练与验证", "用验证集选模型与轮次", "准确率优先；验证准确率相同再比较验证损失。")
        r = self.r
        self.image("curves", M, 133, CW, 310)
        self.para("图 1　两组训练／验证曲线，数据来自各自的 history.csv。训练增强组的训练指标按增强后的输入统计，不能直接视作干净样本上的指标。",
                  450, size=10, color=MUTED)
        self.heading("每个方案的最佳验证记录", 488)
        rows = [[VARIANTS[k], str(v["epoch"]), pct(v["train_acc"]), f'{v["train_loss"]:.4f}',
                 pct(v["val_acc"]), f'{v["val_loss"]:.4f}', f'{v["lr"]:.4g}']
                for k, v in r["winners"].items()]
        self.table(["方案", "Epoch", "训练准确率", "训练损失", "验证准确率", "验证损失", "学习率"],
                   rows, [82, 48, 79, 76, 79, 76, CW - 440], 515, size=9.4)
        base, aug = (r["winners"][k] for k in VARIANTS)
        chosen = r["winners"][r["selected"]]
        delta = (aug["val_acc"] - base["val_acc"]) * 100
        gap_base, gap_aug = ((row["train_acc"] - row["val_acc"]) * 100 for row in (base, aug))
        self.box(M, 600, CW, 169)
        self.line(f"入选：{VARIANTS[r['selected']]}  /  Epoch {chosen['epoch']}", 610, x=M + 14, size=15, color=TEAL)
        self.para(f"各自最佳轮次：增强组验证准确率较基线变化 {delta:+.2f} 个百分点，"
                  f"验证损失变化 {aug['val_loss'] - base['val_loss']:+.4f}。"
                  "仅对锁定的入选模型做一次官方测试，不用测试结果选模。",
                  637, x=M + 14, w=CW - 28, size=10.5)
        self.para(f"最佳轮次的训练减验证准确率：基线 {gap_base:+.2f}、增强 {gap_aug:+.2f} 个百分点；"
                  "训练输入口径不同，差值不能单独证明泛化差距缩小或扩大。",
                  674, x=M + 14, w=CW - 28, size=10.5)
        trend = []
        for key, name in VARIANTS.items():
            history = r["histories"][key]
            first, last = history[0], history[-1]
            trend.append(f"{name} {pct(first['val_acc'])} → {pct(last['val_acc'])}"
                         f"（末轮损失 {last['val_loss']:.4f}）")
        self.para(f"首轮至末轮的验证准确率：{'；'.join(trend)}。单次曲线不代表多次训练。",
                  711, x=M + 14, w=CW - 28, size=10.5)
        self.end()

    def testing(self):
        self.start("官方测试", "整体表现与十类准确率", "只报告入选模型的官方测试，不把验证差值解释成测试增益。")
        r = self.r
        w = (CW - 20) / 3
        self.card("入选方案", VARIANTS[r["selected"]], M, 144, w,
                  sub=f'Epoch {r["winners"][r["selected"]]["epoch"]}')
        self.card("官方测试准确率", pct(r["accuracy"]), M + w + 10, 144, w, sub="10,000 张图像")
        self.card("官方测试损失", f'{r["loss"]:.4f}', M + (w + 10) * 2, 144, w, sub="交叉熵")
        self.heading("混淆矩阵与各类别准确率", 244)
        counts = r["matrix"]
        self.image("confusion", M, 268, CW, 287)
        self.para("图 2　行是真实类别，列是预测类别；格内为样本计数，色深按真实类别归一。"
                  "对角线为正确预测；各类别准确率以该类真实样本为分母。",
                  560, size=10, color=MUTED)
        a = r["per_class"]
        tile_width = (CW - 32) / 5
        for i, value in enumerate(a):
            row, col = divmod(i, 5)
            x, y = M + col * (tile_width + 8), 601 + row * 49
            self.box(x, y, tile_width, 41, radius=5)
            self.line(self.label(i), y + 6, x=x + 9, size=9.4, color=MUTED)
            self.line(pct(value), y + 19, x=x + 9, size=13, color=TEAL)
        high, low = max(a), min(a)
        highest = "、".join(self.label(i) for i, v in enumerate(a) if v == high)
        lowest = "、".join(self.label(i) for i, v in enumerate(a) if v == low)
        diag = sum(counts[i][i] for i in range(10))
        self.box(M, 706, CW, 72)
        self.heading("从矩阵读到什么", 713, x=M + 14)
        self.para(f"对角线合计 {diag:,} 张，非对角线合计 {10000 - diag:,} 张。"
                  f"准确率最高：{highest}（{pct(high)}）；最低：{lowest}（{pct(low)}），"
                  f"相差 {(high - low) * 100:.2f} 个百分点。",
                  735, x=M + 14, w=CW - 28, size=10)
        self.end()

    def errors(self):
        self.start("误判与复现", "误判证据与解读边界", "方向写作「真实 → 预测」。同一对类别的反方向独立计数。")
        r = self.r
        parts = [f"{self.label(i)} → {self.label(j)}：{n:,}（反向 {r['pairs'][(j, i)]:,}）"
                 for (i, j), n in sorted(r["pairs"].items(), key=lambda it: (-it[1], *it[0]))[:3]]
        ranking = "；".join(parts) if parts else "没有非对角线计数"
        self.para(f"矩阵中误判最多的三个方向：{ranking}。测试记录包含 {r['errors']:,} 条误判。", 134, size=10)
        rows = []
        for n, rec in enumerate(r["examples"], 1):
            index = rec["index"]
            case = (f"{n:02d}   #{index}   {self.label(rec['true'])} → {self.label(rec['pred'])}"
                    f"   {pct(float(rec['confidence']))}")
            note = r["observations"].get(index, "未提供逐图观察")
            rows.append((case, note))
        y0 = 431
        for size in (9.3, 8.7, 8.2):
            heights = [max(self.para(col, 0, w=width, size=size, leading=size + 2, draw=False)
                           for col, width in ((case, 202), (note, CW - 218))) + 5
                       for case, note in rows]
            # Give back some montage space to unusually detailed observations.
            y0 = max(346, min(431, 612 - sum(heights)))
            if y0 + sum(heights) <= 612:
                break
        else:
            raise ValueError("误判观察文字过多；请缩短 --observations 中的逐图记录，以适配五页版面。")
        self.image("errors", M, 176, CW, y0 - 223)
        self.para("图 3　按图版顺序列出样本。每个方向最多两例（先最高、再中位置信度），并非随机抽样。",
                  y0 - 42, size=9.3, color=MUTED)
        self.rule(M, y0 - 24, CW)
        self.line("位置 / 测试索引 / 方向 / 预测置信度", y0 - 20, size=9, color=TEAL)
        self.line("逐图视觉观察", y0 - 20, x=M + 207, size=9, color=TEAL)
        y = y0
        for i, ((case, note), h) in enumerate(zip(rows, heights)):
            if i % 2 == 0:
                self.box(M, y, CW, h, radius=3)
            self.para(case, y + 2, x=M + 4, w=202, size=size, leading=size + 2)
            self.para(note, y + 2, x=M + 207, w=CW - 218, size=size, leading=size + 2,
                      color=TEXT if note != "未提供逐图观察" else MUTED)
            y += h
        if not rows:
            self.para("图版无误判样本。", y, size=9.3, color=MUTED)
        if r.get("error_discussion"):
            text = r["error_discussion"]
            if y + 9 + self.para(text, 0, size=9.3, draw=False) > 614:
                raise ValueError("误判小结文字过多；请缩短 --error-discussion 以适配五页版面。")
            self.para(text, y + 9, size=9.3)
        self.heading("局限与个人核验", 624)
        self.para("单次种子对照不能估计随机波动；可在预先固定的多种子协议下复验。裁剪与翻转绑定，不能分辨各自作用；增强也改变了训练输入分布与训练指标的可比性。置信度未经校准，不代表预测正确的概率；图版样本亦不代表全部错误。",
                  648, size=10)
        self.para("AI 协助编写代码与组织报告。作者须亲自复现实验，核验划分与选模规则、日志、测试输出和图表，并自行检查误判原图；未提供观察处不推测图像内容。",
                  707, size=10)
        self.line(f"嵌入字体：{self.font}", 763, size=8.5, color=MUTED)
        self.end()

    def render(self):
        self.cover()
        self.settings()
        self.validation()
        self.testing()
        self.errors()
        self.c.save()


def main(argv=None):
    parser = argparse.ArgumentParser(description="由 CIFAR-10 实验工件生成五页中文 PDF")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--author", default="", help="封面及 PDF 元数据中的作者标识（如姓名与学号；默认留空）")
    parser.add_argument("--observations", type=Path, help="UTF-8 文本，每行 index<TAB>实际视觉观察")
    parser.add_argument("--font", default="auto", help="auto、simhei、yahei、cjk，或中文 TrueType 字体路径")
    parser.add_argument("--font-index", type=int, default=0, help="TTC 内的字体索引（默认 0）")
    parser.add_argument("--error-discussion", type=Path, help="可选的 UTF-8 误判小结文本")
    args = parser.parse_args(argv)
    try:
        font = register_font(args.font, args.font_index)
        run = load_run(args.run_dir, args.observations)
        if args.error_discussion is not None:
            run["error_discussion"] = args.error_discussion.read_text(encoding="utf-8-sig").strip()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        Report(args.output, run, font, args.author).render()
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"生成报告失败：{exc}\n")
    print(f"已生成：{args.output}（5 页）")


if __name__ == "__main__":
    main()
