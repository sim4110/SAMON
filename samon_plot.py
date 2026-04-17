#!/usr/bin/env python3
"""
SAMON - Heatmap visualization from CSV log
"""
import csv
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from collections import defaultdict

def load_csv(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append({
                'elapsed': float(row['elapsed_s']),
                'start': int(row['start_sector']),
                'end': int(row['end_sector']),
                'reads': int(row['reads']),
                'writes': int(row['writes']),
            })
    return rows

def build_heatmap(rows, mode, ncols=256):
    time_groups = defaultdict(list)
    for r in rows:
        time_groups[r['elapsed']].append(r)
    times = sorted(time_groups.keys())

    # auto-zoom: find active sector range
    active = [r for r in rows if r['reads'] + r['writes'] > 0]
    if not active:
        active = rows
    min_s = min(r['start'] for r in active)
    max_s = max(r['end'] for r in active)
    # add 10% padding
    pad = max((max_s - min_s) // 10, 1000)
    min_s = max(0, min_s - pad)
    max_s = max_s + pad
    span = max(max_s - min_s, 1)

    heatmap = np.zeros((len(times), ncols))
    for ti, t in enumerate(times):
        for reg in time_groups[t]:
            if mode == 'read':
                val = reg['reads']
            elif mode == 'write':
                val = reg['writes']
            else:
                val = reg['reads'] + reg['writes']
            if val == 0:
                continue
            c0 = int((reg['start'] - min_s) * ncols / span)
            c1 = int((reg['end'] - min_s) * ncols / span)
            c0 = max(0, min(c0, ncols - 1))
            c1 = max(c0 + 1, min(c1, ncols))
            for c in range(c0, c1):
                heatmap[ti][c] += val / max(c1 - c0, 1)

    return heatmap, times, min_s, max_s

def plot(csv_path, output, mode):
    rows = load_csv(csv_path)
    if not rows:
        print("No data."); return

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [1, 1, 1]})
    fig.suptitle('SAMON - Storage Access MONitor', fontsize=14, fontweight='bold')

    for ax, m, title in zip(axes, ['total', 'read', 'write'],
                             ['Total I/O', 'Reads Only', 'Writes Only']):
        hmap, times, min_s, max_s = build_heatmap(rows, m)
        vmax = max(hmap.max(), 1)
        # log scale with floor at 0.5 so zeros stay black
        hmap_log = np.where(hmap > 0, hmap, 0)
        im = ax.imshow(hmap_log, aspect='auto', cmap='inferno',
                       norm=LogNorm(vmin=0.5, vmax=vmax) if vmax > 1 else None,
                       interpolation='nearest')
        ax.set_title(title, fontsize=11)
        ax.set_ylabel('Time (s)')

        # y ticks
        if len(times) > 20:
            step = max(len(times) // 10, 1)
            yt = list(range(0, len(times), step))
        else:
            yt = list(range(len(times)))
        ax.set_yticks(yt)
        ax.set_yticklabels([f"{times[i]:.0f}" for i in yt], fontsize=8)

        # x ticks
        nc = hmap.shape[1]
        xt = list(range(0, nc, nc // 8))
        ax.set_xticks(xt)
        span = max(max_s - min_s, 1)
        ax.set_xticklabels([f"{int(min_s + x * span / nc):,}" for x in xt],
                           rotation=45, fontsize=7)
        plt.colorbar(im, ax=ax, label='I/O count', shrink=0.8)

    axes[-1].set_xlabel('LBA (sector)')
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    print(f"Saved: {output}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("-o", "--output", default="samon_heatmap.png")
    args = p.parse_args()
    plot(args.csv, args.output, "total")
