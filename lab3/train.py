"""Train CIFAR-10 CNN augmentation ablations, then evaluate the validation winner."""
import argparse
import csv
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torchvision.datasets import CIFAR10


class CNN(nn.Sequential):
    def __init__(self):
        blocks = []
        cin = 3
        for cout in (48, 96, 192):
            for _ in range(2):
                blocks += [nn.Conv2d(cin, cout, 3, padding=1, bias=False),
                           nn.BatchNorm2d(cout), nn.ReLU(inplace=True)]
                cin = cout
            blocks.append(nn.MaxPool2d(2))
        super().__init__(*blocks, nn.AdaptiveAvgPool2d(1), nn.Flatten(),
                         nn.Dropout(0.2), nn.Linear(192, 10))


def stratified_split(labels, seed):
    rng = np.random.default_rng(seed)
    train, val = [], []
    for label in range(10):
        shuffled = rng.permutation(np.flatnonzero(labels == label))
        val.extend(shuffled[:500])
        train.extend(shuffled[500:])
    return np.sort(train), np.sort(val)


def training_stats(raw, train):
    # Accumulate in float64 in chunks; do not inspect validation or test pixels.
    total = np.zeros(3)
    squares = np.zeros(3)
    for part in np.array_split(train, 45):
        x = raw[part].astype(np.float64) / 255.0
        total += x.sum(axis=(0, 1, 2))
        squares += np.square(x).sum(axis=(0, 1, 2))
    n = len(train) * 32 * 32
    mean = total / n
    return mean.tolist(), np.sqrt(squares / n - mean**2).tolist()


def device_data(ds, device):
    return (torch.from_numpy(np.ascontiguousarray(ds.data)).to(device),
            torch.tensor(ds.targets, dtype=torch.long, device=device))


class Preprocess:
    def __init__(self, mean, std, device):
        self.mean = torch.tensor(mean, device=device)
        self.std = torch.tensor(std, device=device)
        self.n = torch.arange(32, device=device)
        self.reflect = torch.cat((self.n[1:5].flip(0), self.n, self.n[-5:-1].flip(0)))

    def __call__(self, x, rng=None):
        if rng is not None:
            b = len(x)
            oy, ox = torch.randint(9, (2, b), generator=rng, device=x.device)
            flip = torch.rand(b, generator=rng, device=x.device) < 0.5
            rows = self.reflect[oy[:, None] + self.n]
            cols = self.reflect[ox[:, None] + torch.where(flip[:, None], 31 - self.n, self.n)]
            x = x[torch.arange(b, device=x.device)[:, None, None], rows[:, :, None], cols[:, None, :]]
        return ((x.float() / 255.0 - self.mean) / self.std).permute(0, 3, 1, 2)


def batches(ids, size):
    # Merge a singleton tail so BatchNorm remains usable in tiny smoke runs.
    parts = list(ids.split(size))
    if len(parts) > 1 and len(parts[-1]) == 1:
        parts[-2:] = [torch.cat(parts[-2:])]
    return parts


@torch.no_grad()
def evaluate(model, x, y, ids, transform, size, amp, save_predictions=False):
    model.eval()
    total = torch.zeros(2, device=x.device)
    predictions, scores = [], []
    for ix in batches(ids, size):
        with torch.autocast(x.device.type, dtype=torch.float16, enabled=amp):
            logits = model(transform(x[ix]))
        logits = logits.float()
        pred = logits.argmax(1)
        total += torch.stack((nn.functional.cross_entropy(logits, y[ix], reduction='sum'),
                              (pred == y[ix]).sum()))
        if save_predictions:
            predictions.append(pred.cpu())
            scores.append(logits.softmax(1).amax(1).cpu())
    loss, acc = (total / len(ids)).cpu().tolist()
    return loss, acc, predictions, scores


def train_variant(args, variant, device, x, y, train_ids, val_ids, prep, mean, std):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    shuffle = torch.Generator(device=device).manual_seed(args.seed + 1)
    augment = torch.Generator(device=device).manual_seed(args.seed + 2)
    model = CNN().to(device=device, memory_format=torch.channels_last)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs, eta_min=args.lr * 0.01)
    amp = device.type == 'cuda' and not args.no_amp
    scaler = torch.amp.GradScaler(device.type, enabled=amp)
    dest = args.run_dir / variant
    dest.mkdir(parents=True, exist_ok=True)
    best = (-math.inf, -math.inf)
    start = time.perf_counter()
    with (dest / 'history.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['epoch', 'train_loss', 'train_acc', 'val_loss', 'val_acc', 'lr'])
        for epoch in range(1, args.epochs + 1):
            model.train()
            order = train_ids[torch.randperm(len(train_ids), device=device, generator=shuffle)]
            total = torch.zeros(2, device=device)
            rate = opt.param_groups[0]['lr']
            for ix in batches(order, args.batch_size):
                inputs = prep(x[ix], augment if variant == 'augmented' else None)
                target = y[ix]
                opt.zero_grad(set_to_none=True)
                with torch.autocast(device.type, dtype=torch.float16, enabled=amp):
                    logits = model(inputs)
                    loss = nn.functional.cross_entropy(logits, target)
                scaler.scale(loss).backward()
                scaler.step(opt)
                scaler.update()
                total += torch.stack((loss.detach() * len(ix), (logits.detach().argmax(1) == target).sum()))
            train_loss, train_acc = (total / len(train_ids)).cpu().tolist()
            val_loss, val_acc, _, _ = evaluate(model, x, y, val_ids, prep, args.batch_size, amp)
            writer.writerow([epoch, train_loss, train_acc, val_loss, val_acc, rate])
            f.flush()
            if (val_acc, -val_loss) > best:
                best = (val_acc, -val_loss)
                best_epoch = epoch
                torch.save(model.state_dict(), dest / 'checkpoint.pt')
            sched.step()
            print(f'{variant} {epoch:02}/{args.epochs} train loss {train_loss:.4f} acc {train_acc:.2%} | '
                  f'val loss {val_loss:.4f} acc {val_acc:.2%} | {time.perf_counter()-start:.1f}s', flush=True)
    config = dict(seed=args.seed, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                  weight_decay=args.weight_decay, train_size=len(train_ids), val_size=len(val_ids),
                  mean=mean, std=std, parameters=sum(p.numel() for p in model.parameters()),
                  seconds=time.perf_counter()-start, device=torch.cuda.get_device_name(device) if amp or device.type == 'cuda' else 'CPU',
                  torch=str(torch.__version__), amp=amp, best_epoch=best_epoch, best_val_acc=best[0],
                  best_val_loss=-best[1], deterministic=True)
    dump(dest / 'config.json', config)
    return best, config


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir', type=Path, default=Path('data'))
    p.add_argument('--run-dir', type=Path, default=Path('runs/main'))
    p.add_argument('--epochs', type=int, default=22)
    p.add_argument('--batch-size', type=int, default=256)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--lr', type=float, default=0.002)
    p.add_argument('--weight-decay', type=float, default=0.01)
    p.add_argument('--device', choices=['auto', 'cuda', 'cpu'], default='auto')
    p.add_argument('--no-amp', action='store_true')
    p.add_argument('--download', action='store_true')
    p.add_argument('--smoke', action='store_true', help='run a small, one-epoch integration check; not report data')
    args = p.parse_args()
    if args.epochs < 1 or args.batch_size < 2 or args.lr <= 0 or args.weight_decay < 0:
        p.error('require positive epochs and lr, batch-size >= 2 and nonnegative weight-decay')
    if (args.run_dir / 'test.json').exists() or any(args.run_dir.glob('*/history.csv')):
        p.error('run directory already contains experiment results; choose a fresh directory')
    if args.smoke:
        args.epochs = 1
    import os
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    device = torch.device(('cuda' if torch.cuda.is_available() else 'cpu') if args.device == 'auto' else args.device)
    if device.type == 'cuda' and not torch.cuda.is_available():
        p.error('CUDA requested but not available')
    train_ds = CIFAR10(args.data_dir, train=True, download=args.download)
    labels = np.asarray(train_ds.targets)
    train_ids, val_ids = stratified_split(labels, args.seed)
    if args.smoke:
        train_ids, val_ids = train_ids[:512], val_ids[:256]
    mean, std = training_stats(train_ds.data, train_ids)
    train_ids, val_ids = (torch.tensor(ids, device=device) for ids in (train_ids, val_ids))
    x, y = device_data(train_ds, device)
    del train_ds
    prep = Preprocess(mean, std, device)
    variants = ('baseline', 'augmented')
    results = {name: train_variant(args, name, device, x, y, train_ids, val_ids, prep, mean, std)
               for name in variants}
    selected = max(variants, key=lambda name: results[name][0])
    config = results[selected][1]
    del x, y
    test_ds = CIFAR10(args.data_dir, train=False, download=False)
    test_x, test_y = device_data(test_ds, device)
    test_ids = torch.arange(256 if args.smoke else len(test_ds), device=device)
    model = CNN().to(device=device, memory_format=torch.channels_last)
    model.load_state_dict(torch.load(args.run_dir / selected / 'checkpoint.pt', map_location=device,
                                     weights_only=True))
    loss, acc, predictions, scores = evaluate(model, test_x, test_y, test_ids, prep,
                                               args.batch_size, config['amp'], save_predictions=True)
    true = test_y[test_ids].cpu()
    pred = torch.cat(predictions)
    cp = torch.cat(scores)
    confusion = torch.bincount(true * 10 + pred, minlength=100).reshape(10, 10)
    counts = confusion.sum(1)
    errors = [dict(index=i, true=int(true[i]), pred=int(pred[i]), confidence=float(cp[i]))
              for i in torch.where(true != pred)[0].tolist()]
    dump(args.run_dir / 'test.json', dict(selected=selected, classes=test_ds.classes,
         test_acc=int(confusion.trace()) / len(true), test_loss=loss, test_size=len(true),
         confusion=confusion.tolist(), per_class_acc=(confusion.diag().double()/counts.clamp(min=1)).tolist(),
         errors=errors, smoke=args.smoke, selected_epoch=config['best_epoch']))
    print(f'Selected {selected} epoch {config["best_epoch"]} by validation; test {acc:.2%} ({len(true)} images)', flush=True)


if __name__ == '__main__':
    main()
