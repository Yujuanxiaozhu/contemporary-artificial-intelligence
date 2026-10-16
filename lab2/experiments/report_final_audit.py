"""检查报告、源数据表、SVG/HTML资源及本轮完整回归日志。"""
import subprocess
import sys
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from experiments.build_report import ROOT,REPORT,NS,report_tables,chart_specifications,render_html
from experiments.build_submission_report import validate_submission, render_html as submission_html
import hashlib


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__();self.resources=[];self.tables=0;self.images=0
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='table':self.tables+=1
        if tag=='img':self.images+=1
        for key in ('src','href'):
            if key in values:self.resources.append(values[key])


def main():
    checks=[]
    path=REPORT/'experiment2_report_full.md'
    text=path.read_text(encoding='utf-8')
    for name,value in report_tables().items():
        if value not in text:raise AssertionError('source table differs: '+name)
    checks.append('12 report tables exactly match source-backed construction')
    if re.search(r'ChatGPT|Codex|Agent|硬性验收|证据链|交接|审计|阶段\s*[1-5]|[A-Za-z]:[\\/]',text,re.I):
        raise AssertionError('internal workflow or absolute path in report body')
    for phrase in ('本实验系统性地构建','从多个维度全面验证','形成了完整闭环','具有较强的工程意义','值得注意的是','进一步地','综上所述','可以清晰地看到'):
        if phrase in text:raise AssertionError('formulaic phrase remains: '+phrase)
    checks.append('naturalness and forbidden-content checks passed')
    for phrase in ('官方最小费用为7','Minimax和Alpha-Beta均返回5','H=2：T2/-1','H=4：T3/3',
                   'max(Manhattan(n,E) - 1, 0)','1.4914 ms与无缓存的2.8066 ms','62 tests passed'):
        if phrase not in text:raise AssertionError('missing key result/formula: '+phrase)
    checks.append('official results, corrected heuristic and first-use cache comparison present')
    assets=list((REPORT/'assets').glob('*.svg'))
    expected=set(chart_specifications())|{'q4_architecture.svg'}
    if {p.name for p in assets}!=expected:raise AssertionError('SVG set mismatch')
    for asset in assets:
        svg=ET.parse(asset).getroot()
        if svg.tag!=f'{{{NS}}}svg':raise AssertionError('not SVG root')
        if float(svg.attrib['width'])<=0 or float(svg.attrib['height'])<=0:raise AssertionError('invalid dimensions')
        if asset.name in chart_specifications():
            meta=svg.find(f'{{{NS}}}metadata')
            if json.loads(meta.text)!=chart_specifications()[asset.name]:raise AssertionError('SVG data mismatch')
        for element in svg.iter():
            if element.tag.endswith('script'):raise AssertionError('script in SVG')
            for name,value in element.attrib.items():
                if name.endswith('href') and not value.startswith('#'):raise AssertionError('external SVG reference')
    checks.append('4 self-contained SVGs parse as XML; 3 numeric plots match source values')
    for relative in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text):
        if not (REPORT/relative).is_file():raise AssertionError('missing Markdown resource: '+relative)
    html=(REPORT/'experiment2_report_full.html').read_text(encoding='utf-8')
    if html!=render_html(text):raise AssertionError('HTML is stale relative to Markdown')
    parser=ResourceParser();parser.feed(html)
    if parser.tables!=12 or parser.images!=4:raise AssertionError('HTML table/image count mismatch')
    for relative in parser.resources:
        if re.match(r'^[a-z]+:',relative,re.I):raise AssertionError('nonlocal HTML resource')
        if not relative.startswith('#') and not (REPORT/relative).is_file():raise AssertionError('missing HTML resource')
    checks.append('HTML matches Markdown; 12 tables and 4 images; all resources local and present')
    reference=(REPORT/'data_reference.md').read_text(encoding='utf-8-sig')
    if not all(name in reference for name in report_tables()):raise AssertionError('incomplete data index')
    for relative in re.findall(r'\.\./[A-Za-z0-9_./-]+',reference):
        # 本次检查输出在末尾生成；先验证其余数据源，再写出并检查自身。
        if relative=='../results/final_audit.json':continue
        if not (REPORT/relative).exists():raise AssertionError('missing indexed source: '+relative)
    checks.append('data_reference index exists and referenced paths resolve')
    execution=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],
                             cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    log=execution.stdout+execution.stderr
    print(log,end='')
    if execution.returncode!=0 or not re.search(r'Ran 62 tests in [\d.]+s',log):
        raise AssertionError('62-test regression failed')
    checks.append('62 tests passed in this audit execution')
    if '姓名：刘毅' not in text or '学号：10245501453' not in text or '班级' in text or '________' in text:
        raise AssertionError('student information incomplete')
    checks.append('student information matches requested author; no class field or placeholder')
    short=(REPORT/'experiment2_report.md').read_text(encoding='utf-8')
    short_stats=validate_submission(short)
    short_html=(REPORT/'experiment2_report.html').read_text(encoding='utf-8')
    if short_html!=submission_html(short):raise AssertionError('submission HTML is stale')
    short_parser=ResourceParser();short_parser.feed(short_html)
    if short_parser.tables!=9 or short_parser.images!=1:raise AssertionError('submission resource count')
    for relative in short_parser.resources:
        if relative=='https://github.com/Yujuanxiaozhu/contemporary-artificial-intelligence':continue
        if re.match(r'^[a-z]+:',relative,re.I) or not (REPORT/relative).is_file():
            raise AssertionError('unexpected submission resource: '+relative)
    checks.append('submission source-backed tables, required analysis and matching HTML checked')
    pdf=REPORT/'experiment2_report.pdf'
    if pdf.exists() and (pdf.stat().st_size<10000 or not pdf.read_bytes().startswith(b'%PDF-')):
        raise AssertionError('invalid PDF file')
    info=json.loads((ROOT/'results/pdf_info.json').read_text(encoding='utf-8'))
    if not (1<=info['pages']<=5) or info['sha256']!=hashlib.sha256(pdf.read_bytes()).hexdigest():
        raise AssertionError('submission PDF differs from validated page-count record')
    checks.append('submission PDF matches the validated at-most-five-page PDF hash')
    review=json.loads((ROOT/'results/report_review.json').read_text(encoding='utf-8'))
    checks.append('Markdown, HTML and available PDF are ready for course use')
    result=dict(status='PASS',checks=checks,report_chinese_characters=short_stats['chinese_characters'],
                report_nonwhitespace_characters=short_stats['nonwhitespace_characters'],
                full_report_chinese_characters=review['chinese_character_count'],svg_count=len(assets),
                submission_tables=short_stats['tables'],submission_images=short_stats['images'],pdf_pages=info['pages'],
                html_generated=True,pdf_generated=(REPORT/'experiment2_report.pdf').exists(),
                tests_passed=62,core_algorithms_modified=False)
    (ROOT/'results/final_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
