"""读取已有正式数据生成完整长版和标准库SVG，不覆盖五页提交版。"""
import csv
from html import escape
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/report_data'
REPORT=ROOT/'report'
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)


def rows(name):
    with (DATA/name).open(encoding='utf-8') as f:
        return list(csv.DictReader(f))


def mdtable(headers,values):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in values])


def number(value):
    return f'{float(value):g}'


def ms(value):
    return f'{float(value)*1000:.4f}'


def report_tables():
    q1=rows('q1/summary.csv');q2=rows('q2/summary.csv');q3=rows('q3/results.csv');q4=rows('q4/results.csv')
    cache=rows('q4/cache_comparison.csv')
    def find(collection,**match):
        return next(r for r in collection if all(r[k]==str(v) for k,v in match.items()))
    t={}
    t['表1']=mdtable(['验证内容','Python版本','范围'],[
        ['题目一、二的初次验证','3.11.9','20个自动测试'],
        ['四题完整验证','3.12.14','62个自动测试'],
        ['本文正式性能对照','3.12.14','地图、博弈树、综合题及缓存实验']])
    t['表2']=mdtable(['指标','定义'],[
        ['expanded_nodes','有效出队并扫描邻居的次数，不含目标和过期条目'],
        ['generated_nodes','入堆次数，含起点和改善g后的再次入堆'],
        ['visited_nodes','实际递归进入次数，含根、内部节点和终止状态'],
        ['evaluated_leaf_nodes','读取叶值或计算终止状态U的次数'],
        ['prune_events','确实跳过后续子节点的剪枝事件次数'],
        ['pruned_children','直接跳过的子节点数，不累计其全部后代'],
        ['elapsed_time','perf_counter测得的墙钟秒数，报告换算为ms']])
    q1v=[]
    for group,size,p in [('20x20_p20','20×20','20%'),('40x40_p20','40×40','20%'),
                         ('80x80_p20','80×80','20%'),('40x40_p10','40×40','10%'),('40x40_p30','40×40','30%')]:
        a=find(q1,group=group,heuristic='zero');b=find(q1,group=group,heuristic='manhattan')
        q1v.append([size,p,number(a['median_solution_cost']),number(a['median_expanded_nodes']),number(b['median_expanded_nodes'])])
    t['表3']=mdtable(['尺寸','目标障碍概率','最短步数中位数','h=0扩展中位数','Manhattan扩展中位数'],q1v)
    q2v=[]
    for group,size in [('20x20_p20','20×20'),('40x40_p20','40×40')]:
        a=find(q2,group=group,heuristic='zero');b=find(q2,group=group,heuristic='admissible')
        q2v.append([size,number(a['median_solution_cost']),number(a['median_expanded_nodes']),number(b['median_expanded_nodes']),ms(a['median_elapsed_time']),ms(b['median_elapsed_time'])])
    t['表4']=mdtable(['尺寸','最小费用中位数','h=0扩展','修正h扩展','h=0时间/ms','修正h时间/ms'],q2v)
    t['表5']=mdtable(['算法／访问顺序','visited','leaf','剪枝事件'],[
        [label,find(q3,case='official',algorithm=alg,order=order)['visited_nodes'],
         find(q3,case='official',algorithm=alg,order=order)['evaluated_leaf_nodes'],
         find(q3,case='official',algorithm=alg,order=order)['prune_events']]
        for label,alg,order in [('Minimax／原顺序','minimax','original'),('Alpha-Beta／原顺序','alphabeta','original'),
                                ('Alpha-Beta／理论较优顺序','alphabeta','favorable'),('Alpha-Beta／不利顺序','alphabeta','unfavorable')]])
    t['表6']=mdtable(['深度','最终值','Minimax叶数','AB原顺序叶数','AB理论较优叶数','AB不利叶数'],[
        [depth,find(q3,case=f'b3_d{depth}',algorithm='minimax',order='original')['best_value'],
         *[find(q3,case=f'b3_d{depth}',algorithm=alg,order=order)['evaluated_leaf_nodes'] for alg,order in
           [('minimax','original'),('alphabeta','original'),('alphabeta','favorable'),('alphabeta','unfavorable')]]] for depth in (4,6)])
    t['表7']=mdtable(['位置','坐标(row,col)','宝藏价值'],[
        ['A','(0,0)','—'],['B','(6,6)','—'],['T1','(0,6)',9],['T2','(2,2)',6],['T3','(4,4)',7],['T4','(6,0)',7]])
    matrix=json.loads((DATA/'q4/distance_matrix.json').read_text(encoding='utf-8'))
    t['表8']=mdtable(['起点／终点',*matrix['labels']],[[label,*row] for label,row in zip(matrix['labels'],matrix['matrix'])])
    branches=rows('q4/decision_branches.csv')
    t['表9']=mdtable(['A首步','即时Gain','H=2的Minimax值','H=4的Minimax值'],[
        [target,find(branches,first_move=target,depth=2)['initial_gain'],find(branches,first_move=target,depth=2)['minimax_value'],
         find(branches,first_move=target,depth=4)['minimax_value']] for target in ('T1','T2','T3','T4')])
    t['表10']=mdtable(['H','算法／顺序','首步/U','visited','时间中位数/ms'],[
        [r['depth'],('Minimax' if r['algorithm']=='minimax' else 'Alpha-Beta')+'／'+{'original':'原顺序','practical':'即时收益降序','unfavorable':'即时收益升序'}[r['order']],
         r['best_target']+'/'+r['best_value'],r['visited_nodes'],ms(r['median_elapsed_time'])] for r in q4])
    t['表11']=mdtable(['H','顺序','visited','leaf','剪枝事件','直接跳过child'],[
        [r['depth'],{'original':'原顺序','practical':'即时收益降序'}[r['order']],r['visited_nodes'],r['evaluated_leaf_nodes'],r['prune_events'],r['pruned_children']]
        for r in q4 if r['algorithm']=='alphabeta' and r['order'] in ('original','practical')])
    labels={'cached_reused_search':'已有矩阵后的搜索','uncached_search':'无缓存，每次行动重新A*','cached_one_shot_total':'首次使用：预计算＋构建＋搜索'}
    t['表12']=mdtable(['情形','A*调用次数','A*累计扩展','博弈visited/leaf','时间中位数/ms'],[
        [labels[r['mode']],r['astar_calls'],r['astar_expanded'],r['visited_nodes']+'/'+r['evaluated_leaf_nodes'],ms(r['median_elapsed_time'])] for r in cache])
    return t


def svg_element(parent,tag,**attrs):
    return ET.SubElement(parent,f'{{{NS}}}{tag}',{k.replace('_','-'):str(v) for k,v in attrs.items()})


def chart_specifications():
    q1=rows('q1/summary.csv');q3=rows('q3/results.csv');q4=rows('q4/results.csv')
    def find(collection,**match):
        return next(r for r in collection if all(r[k]==str(v) for k,v in match.items()))
    return {
        'q1_expanded.svg':dict(title='Q1：20%障碍下的扩展节点数',ylabel='扩展节点数（10张地图的中位数）',groups=['20×20','40×40','80×80'],
            series=['h=0','Manhattan'],values=[[float(find(q1,group=f'{size}x{size}_p20',heuristic=h)['median_expanded_nodes']) for h in ('zero','manhattan')] for size in (20,40,80)]),
        'q3_ordering.svg':dict(title='Q3：访问顺序与剪枝',ylabel='实际递归访问次数（次）',groups=['三叉树，深度4','三叉树，深度6'],
            series=['Minimax','AB原顺序','AB理论较优','AB不利顺序'],values=[[int(find(q3,case=f'b3_d{depth}',algorithm=alg,order=order)['visited_nodes']) for alg,order in
                [('minimax','original'),('alphabeta','original'),('alphabeta','favorable'),('alphabeta','unfavorable')]] for depth in (4,6)]),
        'q4_search_nodes.svg':dict(title='Q4：搜索深度与节点访问',ylabel='实际递归访问次数（次）',groups=['H=2','H=4'],
            series=['Minimax原顺序','AB原顺序','AB即时收益降序','AB即时收益升序'],values=[[int(find(q4,depth=depth,algorithm=alg,order=order)['visited_nodes']) for alg,order in
                [('minimax','original'),('alphabeta','original'),('alphabeta','practical'),('alphabeta','unfavorable')]] for depth in (2,4)])}


def bar_chart(path,spec):
    width,height=960,510
    svg=ET.Element(f'{{{NS}}}svg',dict(width=str(width),height=str(height),viewBox=f'0 0 {width} {height}',role='img'))
    svg_element(svg,'title').text=spec['title']
    svg_element(svg,'desc').text=spec['ylabel']+'；柱顶标注原始数值。'
    svg_element(svg,'metadata').text=json.dumps(spec,ensure_ascii=False)
    svg_element(svg,'rect',width=width,height=height,fill='white')
    font='Microsoft YaHei, Noto Sans CJK SC, sans-serif'
    def text(x,y,value,size=15,anchor='start',fill='#243444',**attrs):
        node=svg_element(svg,'text',x=x,y=y,font_family=font,font_size=size,text_anchor=anchor,fill=fill,**attrs);node.text=str(value)
    text(480,35,spec['title'],22,'middle')
    colors=['#47657a','#c27b45','#6b8b68','#8a7798']
    x0,y0,plotw,ploth=105,100,810,300
    maximum=max(max(row) for row in spec['values'])
    top=maximum*1.17
    for tick in range(6):
        y=y0+ploth-tick*ploth/5
        svg_element(svg,'line',x1=x0,y1=y,x2=x0+plotw,y2=y,stroke='#e3e7eb')
        text(x0-12,y+5,f'{top*tick/5:.0f}',13,'end')
    svg_element(svg,'line',x1=x0,y1=y0+ploth,x2=x0+plotw,y2=y0+ploth,stroke='#526576')
    groupw=plotw/len(spec['groups']);count=len(spec['series']);barw=min(62,groupw*.72/count)
    for g,(label,values) in enumerate(zip(spec['groups'],spec['values'])):
        center=x0+(g+.5)*groupw
        for s,value in enumerate(values):
            x=center-count*barw/2+s*barw+3;h=value/top*ploth;y=y0+ploth-h
            svg_element(svg,'rect',x=x,y=y,width=barw-6,height=h,fill=colors[s])
            text(x+(barw-6)/2,y-8,number(value),14,'middle')
        text(center,y0+ploth+27,label,16,'middle')
    text(25,250,spec['ylabel'],14,'middle',transform='rotate(-90 25 250)')
    step=width/(count+1)
    for i,label in enumerate(spec['series']):
        x=step*(i+.5)
        svg_element(svg,'rect',x=x,y=463,width=15,height=15,fill=colors[i])
        text(x+22,476,label,14)
    ET.ElementTree(svg).write(path,encoding='utf-8',xml_declaration=True)


def architecture(path):
    svg=ET.Element(f'{{{NS}}}svg',dict(width='960',height='390',viewBox='0 0 960 390',role='img'))
    svg_element(svg,'title').text='Q4：路径搜索与博弈搜索的连接'
    svg_element(svg,'rect',width=960,height=390,fill='white')
    def text(x,y,value,size=17):
        svg_element(svg,'text',x=x,y=y,text_anchor='middle',font_family='Microsoft YaHei, Noto Sans CJK SC, sans-serif',font_size=size,fill='#243444').text=value
    text(480,35,'Q4：路径搜索与博弈搜索的连接',22)
    items=[('地图与进入费用',80),('A*距离预计算',140),('6×6距离矩阵',200),('GameState状态与行动',260),('Minimax / Alpha-Beta',320)]
    for label,y in items:
        svg_element(svg,'rect',x=285,y=y-24,width=390,height=43,rx=5,fill='#eef3f6',stroke='#78909f')
        text(480,y+4,label)
        if y!=320:
            svg_element(svg,'line',x1=480,y1=y+19,x2=480,y2=y+33,stroke='#526576',stroke_width=2)
            svg_element(svg,'path',d=f'M 475 {y+29} L 480 {y+35} L 485 {y+29}',fill='none',stroke='#526576',stroke_width=2)
    text(480,376,'距离表按地图构建一次，后续行动直接查表',15)
    ET.ElementTree(svg).write(path,encoding='utf-8',xml_declaration=True)


def inline(value):
    parts=[]
    token=re.compile(r'(`[^`]+`|\*\*.+?\*\*|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\))')
    for segment in token.split(value):
        if segment.startswith('`') and segment.endswith('`'):
            parts.append('<code>'+escape(segment[1:-1])+'</code>')
        elif segment.startswith('**') and segment.endswith('**'):
            parts.append('<strong>'+escape(segment[2:-2])+'</strong>')
        elif segment.startswith('!['):
            match=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',segment)
            parts.append(f'<img alt="{escape(match[1],quote=True)}" src="{escape(match[2],quote=True)}">')
        elif segment.startswith('['):
            match=re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)',segment)
            parts.append(f'<a href="{escape(match[2],quote=True)}">{escape(match[1])}</a>')
        else:
            parts.append(escape(segment))
    return ''.join(parts)


def render_html(markdown):
    lines=markdown.splitlines();body=[];i=0;headings=[]
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            block=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]);i+=1
            body.append('<pre><code>'+escape('\n'.join(block))+'</code></pre>');i+=1;continue
        match=re.match(r'^(#{1,3}) (.+)$',line)
        if match:
            level=len(match[1]);anchor='sec-'+str(len(headings));headings.append((level,match[2],anchor))
            body.append(f'<h{level} id="{anchor}">'+inline(match[2])+f'</h{level}>');i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].startswith('|'):
                block.append([c.strip() for c in lines[i].strip('|').split('|')]);i+=1
            cells=lambda row,tag:'<tr>'+''.join(f'<{tag}>'+inline(c)+f'</{tag}>' for c in row)+'</tr>'
            body.append('<table><thead>'+cells(block[0],'th')+'</thead><tbody>'+''.join(cells(r,'td') for r in block[2:])+'</tbody></table>');continue
        if line.startswith('- '):
            items=[]
            while i<len(lines) and lines[i].startswith('- '):
                items.append('<li>'+inline(lines[i][2:])+'</li>');i+=1
            body.append('<ul>'+''.join(items)+'</ul>');continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,3} |\||```|- )',lines[i]):
            paragraph.append(lines[i]);i+=1
        body.append('<p>'+inline(' '.join(paragraph))+'</p>')
    css='''@page{size:A4;margin:18mm 17mm}*{box-sizing:border-box}body{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;color:#202c36;line-height:1.75;font-size:15px;margin:0;background:#edf0f2}main{max-width:900px;margin:32px auto;padding:45px 58px;background:white}h1{text-align:center;font-size:29px;margin:0 0 18px}h2{font-size:22px;margin:32px 0 12px;border-bottom:1px solid #d8dfe4;padding-bottom:7px}h3{font-size:17px;margin:22px 0 9px}p{margin:10px 0}table{border-collapse:collapse;width:100%;font-size:12px;line-height:1.6;margin:14px 0}th,td{border:1px solid #b7c1c8;padding:6px 7px;text-align:left}thead{background:#edf2f5}tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f6;padding:13px;font-size:12px;line-height:1.55}code{font-family:Consolas,monospace;font-size:.93em}img{max-width:100%;height:auto;display:block;margin:15px auto}a{color:#345f7a}nav{padding:14px 18px;background:#f2f5f7}nav ul{columns:2;margin:0}figure{margin:0} @media print{body{background:white;font-size:10.5pt;line-height:1.65}main{max-width:none;margin:0;padding:0}h1{font-size:22pt}h2{font-size:15pt}h3{font-size:12pt}table{font-size:8.4pt}pre{font-size:8.2pt}img{max-height:78mm;object-fit:contain;break-inside:avoid}h2,h3{break-after:avoid}p{orphans:3;widows:3}thead{display:table-header-group}nav{display:none}}'''
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>当代人工智能实验课：实验二 搜索算法</title><style>'+css+'</style></head><body><main>'+''.join(body)+'</main></body></html>'


def main():
    REPORT.mkdir(exist_ok=True);(REPORT/'assets').mkdir(exist_ok=True)
    for name,spec in chart_specifications().items():bar_chart(REPORT/'assets'/name,spec)
    architecture(REPORT/'assets/q4_architecture.svg')
    t=report_tables()
    text=(ROOT/'experiments/report_text.md').read_text(encoding='utf-8-sig')
    for name,value in t.items():text=text.replace('{{'+name+'}}',value)
    if '{{' in text:raise AssertionError('unresolved report placeholder')
    # 内容核对先于表达修改，所有表格逐行来自已存在的CSV/JSON。
    if any(value not in text for value in t.values()):raise AssertionError('missing source-backed table')
    content_pass=True
    edits=[('值得注意的是，',''),('进一步地，',''),('综上所述，',''),
           ('从多个维度比较这些结果后可以发现，','从这些结果看，')]
    changes=[]
    for old,new in edits:
        count=text.count(old)
        if count:
            text=text.replace(old,new);changes.append(dict(original=old,replacement=new,count=count))
    (REPORT/'experiment2_report_full.md').write_text(text,encoding='utf-8')
    (REPORT/'experiment2_report_full.html').write_text(render_html(text),encoding='utf-8')
    review=dict(content_tables_checked=len(t),content_check_before_style=content_pass,
                style_changes=changes,chinese_character_count=len(re.findall(r'[\u4e00-\u9fff]',text)),
                non_whitespace_character_count=len(re.sub(r'\s','',text)),
                pdf_generated=(REPORT/'experiment2_report_full.pdf').exists())
    (ROOT/'results/report_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(review,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
