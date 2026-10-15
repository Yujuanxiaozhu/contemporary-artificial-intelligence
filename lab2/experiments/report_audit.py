"""核对正式实验原始计时、汇总中位数与输入记录的对应关系。"""
import csv
import hashlib
import json
from pathlib import Path
from statistics import median


def load(path):
    with path.open(encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    root=Path(__file__).resolve().parents[1]
    data=root/'results/report_data'
    checks=[]
    total_samples=0
    for question in (1,2):
        folder=data/f'q{question}'
        inputs=json.loads((folder/'inputs.json').read_text(encoding='utf-8'))
        results=load(folder/'instances.csv')
        raw=load(folder/'timings.csv')
        timing={}
        for row in raw:
            timing.setdefault((row['case'],row['method']),[]).append(float(row['elapsed_time']))
        if len(results)!=len(inputs)*2:
            raise AssertionError('missing input/algorithm comparison')
        for row in results:
            key=(row['group']+'_'+row['instance'],row['heuristic'])
            samples=timing[key]
            if len(samples)!=int(row['timing_repeats']) or median(samples)!=float(row['median_elapsed_time']):
                raise AssertionError(f'Q{question} timing mismatch {key}')
            if row['solution_cost']!=row['oracle_cost']:
                raise AssertionError('cost oracle mismatch')
        if question==2:
            minima=[min(cell for r in item['grid'] for cell in r if type(cell) is int)
                    for item in inputs if item['group']!='official']
            if set(minima)!={1}:
                raise AssertionError('analysis claim about minimum ordinary terrain needs update')
        for summary in load(folder/'summary.csv'):
            rows=[r for r in results if r['group']==summary['group'] and r['heuristic']==summary['heuristic']]
            for field,source in [('median_expanded_nodes','expanded_nodes'),('median_generated_nodes','generated_nodes'),
                                 ('median_solution_cost','solution_cost'),('median_elapsed_time','median_elapsed_time')]:
                if median(float(r[source]) for r in rows)!=float(summary[field]):
                    raise AssertionError('group summary mismatch')
        attempts=load(folder/'generation_attempts.csv')
        accepted_seeds={r['seed'] for r in attempts if r['reachable']=='True'}
        if accepted_seeds!={str(r['seed']) for r in inputs if r['seed'] is not None}:
            raise AssertionError('seed provenance mismatch')
        total_samples+=len(raw)
        checks.append(dict(question=question,input_count=len(inputs),algorithm_rows=len(results),
                           raw_time_samples=len(raw),rejected_maps=sum(r['reachable']=='False' for r in attempts),status='PASS'))
    for folder_name,result_file,timing_file in [('q3','results.csv','timings.csv'),('q4','results.csv','timings.csv'),
                                                ('q4','cache_comparison.csv','cache_timings.csv')]:
        folder=data/folder_name
        results=load(folder/result_file)
        raw=load(folder/timing_file)
        timing={}
        for row in raw:
            timing.setdefault((row['case'],row['method']),[]).append(float(row['elapsed_time']))
        for row in results:
            if result_file=='cache_comparison.csv':
                key=('H4_minimax_original',row['mode'])
            elif folder_name=='q3':
                key=(row['case'],row['algorithm']+':'+row['order'])
            else:
                key=('official',row['depth']+':'+row['algorithm']+':'+row['order'])
            samples=timing[key]
            if len(samples)!=int(row['timing_repeats']) or median(samples)!=float(row['median_elapsed_time']):
                raise AssertionError(f'median mismatch {key}')
        total_samples+=len(raw)
        checks.append(dict(section=folder_name+'/'+result_file,algorithm_rows=len(results),raw_time_samples=len(raw),status='PASS'))
    prep=load(data/'q3/preparation_timings.csv')
    for row in load(data/'q3/results.csv'):
        samples=[float(t['elapsed_time']) for t in prep if t['case']==row['case'] and t['order']==row['order']]
        if len(samples)!=int(row['preparation_repeats']) or median(samples)!=float(row['median_order_preparation_time']):
            raise AssertionError('Q3 preparation median mismatch')
    total_samples+=len(prep)
    prep=load(data/'q4/precomputation_timings.csv')
    metadata=json.loads((data/'q4/precomputation.json').read_text(encoding='utf-8'))
    if len(prep)!=metadata['repeats'] or median(float(r['elapsed_time']) for r in prep)!=metadata['median_precomputation_time']:
        raise AssertionError('Q4 precomputation median mismatch')
    total_samples+=len(prep)
    result=dict(status='PASS',checks=checks,all_raw_time_samples=total_samples,
                notes='Includes search samples, Q3 ordering preparation and Q4 matrix preparation; excludes warmups.')
    (data/'data_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
