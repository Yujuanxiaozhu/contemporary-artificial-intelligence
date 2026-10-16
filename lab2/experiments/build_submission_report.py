"""从既有正式数据生成五页报告的Markdown和HTML，不测量或改写实验数据。"""
import re

from experiments.build_report import REPORT, rows, mdtable, number, ms, render_html as full_html

GITHUB = 'https://github.com/Yujuanxiaozhu/contemporary-artificial-intelligence'


def submission_tables():
    q1, q2 = rows('q1/summary.csv'), rows('q2/summary.csv')
    q3, q4 = rows('q3/results.csv'), rows('q4/results.csv')
    cache = rows('q4/cache_comparison.csv')

    def find(collection, **match):
        return next(row for row in collection if all(row[k] == str(v) for k, v in match.items()))

    tables = {}
    values = []
    for group, size, density in [('20x20_p20', '20×20', '20%'), ('40x40_p20', '40×40', '20%'),
                                 ('80x80_p20', '80×80', '20%'), ('40x40_p10', '40×40', '10%'),
                                 ('40x40_p30', '40×40', '30%')]:
        a = find(q1, group=group, heuristic='zero')
        b = find(q1, group=group, heuristic='manhattan')
        values.append([size, density, number(a['median_solution_cost']),
                       number(a['median_expanded_nodes']), number(b['median_expanded_nodes'])])
    tables['q1'] = mdtable(['尺寸', '障碍概率', '最短步数', 'h=0 expanded', 'Manhattan expanded'], values)
    values = []
    for group, size in [('20x20_p20', '20×20'), ('40x40_p20', '40×40')]:
        a = find(q2, group=group, heuristic='zero')
        b = find(q2, group=group, heuristic='admissible')
        values.append([size, number(a['median_solution_cost']), number(a['median_expanded_nodes']),
                       number(b['median_expanded_nodes']), ms(a['median_elapsed_time']), ms(b['median_elapsed_time'])])
    tables['q2'] = mdtable(['尺寸', '最小费用', 'h=0扩展', '修正h扩展', 'h=0/ms', '修正h/ms'], values)
    tables['q3_official'] = mdtable(['算法', 'visited', 'leaf', 'cutoff'], [
        [label, *[find(q3, case='official', algorithm=alg, order='original')[key]
                  for key in ('visited_nodes', 'evaluated_leaf_nodes', 'prune_events')]]
        for label, alg in [('Minimax', 'minimax'), ('Alpha-Beta', 'alphabeta')]])
    search_orders = [('minimax', 'original'), ('alphabeta', 'original'),
                     ('alphabeta', 'favorable'), ('alphabeta', 'unfavorable')]
    tables['q3_trees'] = mdtable(['深度', 'Minimax', 'AB original', 'AB oracle', 'AB unfavorable'], [
        [depth, *[find(q3, case=f'b3_d{depth}', algorithm=alg, order=order)['visited_nodes']
                  for alg, order in search_orders]] for depth in (4, 6)])
    from experiments.build_report import DATA
    import json
    matrix = json.loads((DATA / 'q4/distance_matrix.json').read_text(encoding='utf-8'))
    tables['matrix'] = mdtable(['', *matrix['labels']], [[label, *values]
                               for label, values in zip(matrix['labels'], matrix['matrix'])])
    branches = rows('q4/decision_branches.csv')
    tables['branches'] = mdtable(['A首步', 'H=2', 'H=4'], [
        [target, *[find(branches, first_move=target, depth=depth)['minimax_value'] for depth in (2, 4)]]
        for target in ('T1', 'T2', 'T3', 'T4')])
    q4_orders = [('minimax', 'original'), ('alphabeta', 'original'),
                 ('alphabeta', 'practical'), ('alphabeta', 'unfavorable')]
    tables['q4_search'] = mdtable(['H', 'Minimax original', 'AB original', 'AB practical', 'AB unfavorable'], [
        [depth, *[find(q4, depth=depth, algorithm=alg, order=order)['visited_nodes']
                  for alg, order in q4_orders]] for depth in (2, 4)])
    tables['q4_detail'] = mdtable(['顺序', 'visited', 'leaf', 'cutoff', 'pruned children'], [
        [order, *[find(q4, depth=4, algorithm='alphabeta', order=order)[key]
                  for key in ('visited_nodes', 'evaluated_leaf_nodes', 'prune_events', 'pruned_children')]]
        for order in ('original', 'practical')])
    tables['cache'] = mdtable(['情形', 'A*次数', '博弈visited/leaf', '时间/ms'], [
        [label, row['astar_calls'], row['visited_nodes'] + '/' + row['evaluated_leaf_nodes'], ms(row['median_elapsed_time'])]
        for label, mode in [('首次：预计算＋构建＋搜索', 'cached_one_shot_total'),
                            ('无缓存：每步重新A*', 'uncached_search'),
                            ('已有矩阵后的搜索', 'cached_reused_search')]
        for row in [find(cache, mode=mode)]])
    return tables


def submission_markdown():
    text = (REPORT / 'submission_text.md').read_text(encoding='utf-8')
    for name, table in submission_tables().items():
        text = text.replace('{{' + name + '}}', table)
    if '{{' in text:
        raise AssertionError('unresolved submission table')
    return text


def render_html(markdown):
    # 共用长版的轻量Markdown解析器，只替换版式并明确五个分页边界。
    blocks = markdown.split('<!-- pagebreak -->')
    if len(blocks) != 5:
        raise AssertionError('submission must have five page sections')
    pages = []
    for i, block in enumerate(blocks, 1):
        body = full_html(block).split('<main>', 1)[1].split('</main>', 1)[0]
        pages.append(f'<section class="page" aria-label="第{i}页">{body}'
                     f'<footer>实验二：搜索算法 <span>{i} / 5</span></footer></section>')
    css = '''
@page { size: A4; margin: 14mm 15mm; }
* { box-sizing: border-box; }
body { margin: 0; color: #1c2530; font-family: "Microsoft YaHei", "SimSun", sans-serif;
       font-size: 10.5pt; line-height: 1.24; background: #e9edf0; }
main { margin: 0 auto; }
.page { position: relative; width: 210mm; min-height: 297mm; padding: 14mm 15mm 23mm;
        background: white; margin: 7mm auto; }
h1 { font-size: 19pt; text-align: center; margin: 0 0 3mm; }
.page:first-child > p:first-of-type { font-size: 15pt; text-align: center; margin: 0 0 4mm; }
h2 { font-size: 14pt; line-height: 1.25; margin: 4mm 0 3mm; padding-bottom: 2mm;
     border-bottom: .4mm solid #365c74; break-after: avoid; }
.page:not(:first-child) > h2:first-child { margin-top: 0; }
h3 { font-size: 11.2pt; margin: 3.6mm 0 2mm; break-after: avoid; }
p { margin: 2.4mm 0; text-align: justify; orphans: 2; widows: 2; }
code { font-family: Consolas, "Microsoft YaHei", monospace; font-size: .94em; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; line-height: 1.2;
        margin: 2.5mm 0 3mm; font-variant-numeric: tabular-nums; break-inside: avoid; }
th, td { padding: 1.7mm 1.5mm; border: .2mm solid #a8b6c1; text-align: center; }
thead { background: #edf2f5; display: table-header-group; }
tr { break-inside: avoid; }
img { display: block; width: 100%; max-height: 69mm; object-fit: contain; margin: 2mm auto; }
a { color: #234d70; text-decoration: none; overflow-wrap: anywhere; }
footer { position: absolute; bottom: 5mm; left: 15mm; right: 15mm; padding-top: 2mm;
         border-top: .2mm solid #c9d2d9; color: #52616e; font-size: 8pt; }
footer span { float: right; }
@media print {
  body { background: white; }
  .page { width: auto; min-height: 267mm; padding: 0 0 10mm; margin: 0;
          break-after: page; }
  .page:last-child { break-after: auto; }
  footer { bottom: 0; left: 0; right: 0; }
  a { color: inherit; }
}
'''
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>实验二：搜索算法</title><style>' + css + '</style></head><body><main>'
            + ''.join(pages) + '</main></body></html>')


def validate_submission(text):
    if text != submission_markdown():
        raise AssertionError('submission Markdown differs from template/source data')
    forbidden = r'ChatGPT|Codex|Agent|硬性验收|证据链|交接|审计|阶段\s*[1-5]|(?<![A-Za-z])[A-Za-z]:[\\/]'
    if re.search(forbidden, text, re.I) or '班级' in text:
        raise AssertionError('forbidden wording in submission')
    for value in ['姓名：刘毅', '学号：10245501453', GITHUB, 'lab2/', '7步', '**16**', '**13**',
                  'minimum cost = 7', 'min_positive_terrain_cost', '[3, 3, E]', 'Minimax = 5',
                  'H=2：T2 / -1', 'H=4：T3 / 3', '9.023 ms', '0.0921 ms',
                  '1.4914 ms', '2.8066 ms', '0.1810 ms', '62 tests passed']:
        if value not in text:
            raise AssertionError('missing required result: ' + value)
    return {'chinese_characters': len(re.findall(r'[\u4e00-\u9fff]', text)),
            'nonwhitespace_characters': len(re.sub(r'\s', '', text)),
            'tables': len(submission_tables()), 'images': 1}


def main():
    text = submission_markdown()
    stats = validate_submission(text)
    (REPORT / 'experiment2_report.md').write_text(text, encoding='utf-8')
    (REPORT / 'experiment2_report.html').write_text(render_html(text), encoding='utf-8')
    print(stats)


if __name__ == '__main__':
    main()
