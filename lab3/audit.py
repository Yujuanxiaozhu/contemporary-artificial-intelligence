"""Validate that a full run's recorded metrics, loss tie-break, and errors agree."""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(path):
    runs = ('baseline', 'augmented')
    configs, best = {}, {}
    for run in runs:
        cfg = configs[run] = read_json(path / run / 'config.json')
        with (path / run / 'history.csv').open(encoding='utf-8', newline='') as f:
            rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
        require([r['epoch'] for r in rows] == list(range(1, cfg['epochs'] + 1)), f'{run}: epoch sequence')
        require(all(math.isfinite(value) for r in rows for value in r.values()), f'{run}: nonfinite history')
        require(all(0 <= r[k] <= 1 for r in rows for k in ('train_acc', 'val_acc')), f'{run}: invalid accuracy')
        require((cfg['train_size'], cfg['val_size']) == (45000, 5000), f'{run}: sample counts')
        winner = max(rows, key=lambda r: (r['val_acc'], -r['val_loss']))
        require((winner['epoch'], winner['val_acc'], winner['val_loss']) ==
                (cfg['best_epoch'], cfg['best_val_acc'], cfg['best_val_loss']), f'{run}: incorrect best epoch')
        best[run] = (winner['val_acc'], -winner['val_loss'])
    for key in ('seed', 'epochs', 'batch_size', 'lr', 'weight_decay', 'train_size', 'val_size',
                'mean', 'std', 'parameters', 'device', 'torch', 'amp', 'deterministic'):
        require(configs[runs[0]][key] == configs[runs[1]][key], f'Runs differ on {key}')
    test = read_json(path / 'test.json')
    require(test['selected'] == max(runs, key=best.get), 'Test model is not the validation winner')
    require(test['selected_epoch'] == configs[test['selected']]['best_epoch'], 'Incorrect test checkpoint epoch')
    require(not test['smoke'] and test['test_size'] == 10000, 'Not a full test run')
    require(math.isfinite(test['test_loss']) and test['test_loss'] >= 0, 'Invalid test loss')
    cm = test['confusion']
    require(len(test['classes']) == len(set(test['classes'])) == len(cm) == len(test['per_class_acc']) == 10,
            'Expected ten classes')
    for i, row in enumerate(cm):
        require(len(row) == 10 and all(isinstance(c, int) and c >= 0 for c in row) and sum(row) == 1000,
                f'Invalid confusion row {i}')
        require(math.isclose(row[i] / sum(row), test['per_class_acc'][i]), f'Wrong class accuracy {i}')
    diagonal = sum(cm[i][i] for i in range(10))
    require(math.isclose(diagonal / 10000, test['test_acc']), 'Wrong test accuracy')
    errors = test['errors']
    require(len(errors) == len({r['index'] for r in errors}) == 10000 - diagonal, 'Wrong error count')
    require(all(0 <= r['index'] < 10000 and 0.099999 <= r['confidence'] <= 1 and r['true'] != r['pred']
                for r in errors), 'Invalid error record')
    actual = Counter((r['true'], r['pred']) for r in errors)
    require(actual == Counter({(i, j): cm[i][j] for i in range(10) for j in range(10) if i != j and cm[i][j]}),
            'Errors disagree with confusion matrix')
    print(f'Audit passed: {test["selected"]}, epoch {test["selected_epoch"]}, {diagonal}/10000 correct')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    audit(parser.parse_args().run_dir)
