"""Render the two-page report from actual experiment results.

Requires reportlab and a CJK TrueType font. Example:
python build_report.py --font NotoSansSC-Regular.ttf --repo https://github.com/USER/REPO
"""
import argparse
from pathlib import Path
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--font', required=True)
parser.add_argument('--repo', default='待填入真实 GitHub 仓库链接（提交前补全）')
parser.add_argument('--output', default=str(ROOT/'report_draft.pdf'))
args=parser.parse_args()
pdfmetrics.registerFont(TTFont('CN',args.font))
W,H=A4
c=canvas.Canvas(args.output,pagesize=A4)
c.setTitle('实验一：基于 TF-IDF 的文本分类')
c.setAuthor('')
L=40; WIDTH=W-80; y=H-40
body=ParagraphStyle('body',fontName='CN',fontSize=9.3,leading=14.2,wordWrap='CJK',spaceAfter=4)
small=ParagraphStyle('small',parent=body,fontSize=8,leading=11.4)
head=ParagraphStyle('head',parent=body,fontSize=11,leading=16,spaceAfter=5)
notes=[]
def p(text,style=body):
    global y
    obj=Paragraph(text,style);_,h=obj.wrap(WIDTH,1000)
    assert y-h>34, ('Page overflow',text,y,h)
    obj.drawOn(c,L,y-h);y-=h+style.spaceAfter
    notes.append(text)
def section(text):
    global y
    y-=5;p(text,head)
def table(rows,widths):
    global y
    notes.append('\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows))
    cells=[[Paragraph(str(v),small) for v in row] for row in rows]
    t=Table(cells,colWidths=widths)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),
        ('LINEABOVE',(0,0),(-1,0),0.6,colors.black),
        ('LINEBELOW',(0,0),(-1,0),0.4,colors.black),
        ('LINEBELOW',(0,-1),(-1,-1),0.6,colors.black),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    _,h=t.wrap(WIDTH,1000);assert y-h>34;t.drawOn(c,L,y-h);y-=h+7
def footer(n):
    c.setFont('CN',8);c.drawCentredString(W/2,22,str(n))

r=pd.read_csv(ROOT/'results/experiments.csv')
p('实验一：基于 TF-IDF 的文本分类',ParagraphStyle('title',parent=body,fontSize=16,leading=23,spaceAfter=7))
p('代码仓库：'+escape(args.repo),small)
section('1  实验问题与设置')
p('本实验比较朴素贝叶斯、线性 SVM 和逻辑回归在英文文本十分类任务中的表现，并检验次线性词频、双词组合和邮件头清洗是否有效。预先以验证准确率为主指标，Macro-F1 为辅助指标，同时记录训练耗时。')
p('数据包含 7,368 条有标签文本和 2,457 条无标签测试文本，各类有标签样本数为 705～747。检查未发现空文本、集合内部完全重复文本或训练/测试文本的完全重合。按类别分层划分 5,894 条训练样本和 1,474 条验证样本，随机种子为 42。先划分，再仅在训练部分拟合词表和 IDF，验证集只做变换。')
p('TF-IDF 基线使用单词 unigram、最多 20,000 维、min_df=2、小写转换和 L2 归一化，不额外去停用词。运行环境为 Python 3.12.14、scikit-learn 1.8.0，Linux x86_64 CPU；数值库线程上限设为 2。完整依赖、数据哈希和划分行号保存在代码仓库中。')
section('2  模型与参数比较')
p('多项式朴素贝叶斯（NB）利用类别条件下的词特征分布，alpha 控制平滑；线性 SVM 寻找有间隔的分类边界，采用 LinearSVC 的平方 hinge 损失和一对其余多分类；逻辑回归（LR）通过交叉熵学习类别概率。SVM 和 LR 的 C 越小，正则化越强。各模型共享同一份稀疏特征，SVM/LR 最大迭代数分别为 5,000/2,000。')
rows=[['模型','alpha / C','训练准确率','验证准确率','Macro-F1','训练秒数']]
for _,v in r[r.stage=='model_parameter'].iterrows():
    rows.append([v.model,f'{v.parameter:g}',f'{v.train_accuracy*100:.2f}%',f'{v.accuracy*100:.2f}%',f'{v.macro_f1:.4f}',f'{v.fit_seconds:.3f}'])
table(rows,[61,60,100,100,100,WIDTH-421])
p('NB 在 alpha=0.1 时达到 91.93%，训练仅约 0.015 秒，是很便宜的基线；过强平滑使验证表现下降。SVM 在 C=1 时为 93.55%，C=10 时训练准确率升至 99.98%，验证准确率却降至 93.35%，说明更贴合训练集不一定更好。LR 随 C 增大持续改善，C=10 达到 93.15%，接近 SVM，但本次训练耗时更长。')
p('以上时间只含分类器 fit，不含特征提取和预测，单次计时仅供本环境比较。正式运行没有收敛警告。最初尝试的 SVC 线性核配置因运行成本中止，未纳入比较；LinearSVC 与 SVC 的损失和多分类策略不同。',small)
footer(1);c.showPage();y=H-38
section('3  特征对照与稳定性')
p('固定基线最佳模型 LinearSVC（C=1），每次只改一个特征因素，另测试双词组合与次线性 TF 的组合。次线性 TF 将正词频 tf 替换为 1+ln(tf)，降低重复词的权重；邮件头清洗保留 Subject，移除识别到的其余头部，正文保持不变。')
rows=[['特征设置（均为 20,000 维）','验证准确率','Macro-F1']]
for feature,label in [('baseline','基线'),('bigrams','加入 bigram'),('sublinear','次线性 TF'),('clean_headers','清洗邮件头，保留主题'),('combined','bigram + 次线性 TF')]:
    v=r[(r.model=='SVM')&(r.parameter==1)&(r.feature==feature)].iloc[0]
    rows.append([label,f'{v.accuracy*100:.2f}%',f'{v.macro_f1:.4f}'])
table(rows,[WIDTH-190,95,95])
p('次线性 TF 将准确率从 93.55% 提升到 94.17%，验证集多判对 9 条；邮件头清洗也略有改善。bigram 没有带来收益，组合后同样下降。一种可能是固定 20,000 维预算下，双词特征与单词竞争词表位置且更稀疏，但本次实验不足以单独证明这一原因。因此最终选择次线性 TF，不叠加其余处理。')
p('在另外两个分层划分（种子 17、2026）上，基线准确率为 93.89%、94.57%，次线性 TF 为 94.44%、94.78%。包含主划分的三次均值±样本标准差分别为 94.01%±0.52 和 94.46%±0.31 个百分点。改进方向一致，但同一数据的重复划分并非独立测试，不能据此声称显著提升。',small)
section('4  分类结果与错误分析')
# Place figure and a compact analysis side by side.
figw=252; figh=206
c.drawImage(str(ROOT/'results/confusion_matrix.png'),L,y-figh,width=figw,height=figh,mask='auto')
analysis=('最终配置在主验证集上判对 1,388/1,474 条，Macro-F1 为 0.9417。左图为混淆矩阵（行是真实类别，列是预测类别）。<br/><br/>'
          '类别 2、7 的 F1 较低，分别为 0.8649、0.8759；7→2 有 10 条，2→7 有 7 条。错分样本涉及 protected mode、IBM-PC 等相近技术词，词面重叠可能造成混淆。<br/><br/>'
          '另一个样本正文仅为“hello testing”，由类别 3 错判为 8，几乎没有主题信息。继续增加模型复杂度也未必能解决这种信息不足。标签没有官方名称映射，故只使用编号。')
obj=Paragraph(analysis,body);_,h=obj.wrap(WIDTH-figw-12,1000);assert h<=figh+5
notes.append(analysis)
obj.drawOn(c,L+figw+12,y-h);y-=max(figh,h)+4
section('5  结论与局限')
p('高维稀疏 TF-IDF 已能提供较强区分信息，线性模型在本次数据上取得较好效果。最终使用全部 7,368 条有标签数据重新拟合词表、IDF 和 LinearSVC，输出按测试原顺序排列的 2,457 行 prediction.csv（无表头、无索引）。另起进程完整复现后，13 组配置的主要指标和最终预测文件均一致。')
p('主验证集参与了多次选择，最高分可能偏乐观；近重复文本和讨论线程未做完整分组排查。测试集无标签，不能报告测试准确率。本次未运行 MLP；更大网络存在过拟合和计算成本风险。后续可另设对照研究 Word2Vec 或 BERT 等表示，但不能从本次结果推断其效果。',small)
footer(2);c.save()
(ROOT/'report_text.md').write_text('\n\n'.join(notes),encoding='utf-8')
print(args.output)
