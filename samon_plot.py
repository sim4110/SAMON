#!/usr/bin/env python3
"""
SAMON - DAMON-style heatmap visualization from CSV log
X-axis: Time, Y-axis: LBA (sector address), Color: Access Intensity
Auto-zooms Y-axis to active LBA range. Uses percentile-based color scaling.
"""
import csv
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm
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

def get_value(r, mode):
    if mode == 'read': return r['reads']
    if mode == 'write': return r['writes']
    return r['reads'] + r['writes']

def plot(csv_path, output, mode):
    rows = load_csv(csv_path)
    if not rows:
        print("No data."); return

    time_groups = defaultdict(list)
    for r in rows:
        time_groups[r['elapsed']].append(r)
    times = sorted(time_groups.keys())

    # auto-zoom Y to active range
    active = [r for r in rows if get_value(r, mode) > 0]
    if not active:
        active = rows
    min_s = min(r['start'] for r in active)
    max_s = max(r['end'] for r in active)
    pad = max((max_s - min_s) // 20, 1000)
    min_s = max(0, min_s - pad)
    max_s = max_s + pad
    span = max(max_s - min_s, 1)

    nrows_y = 512
    ncols_x = len(times)
    heatmap = np.zeros((nrows_y, ncols_x))

    for ti, t in enumerate(times):
        for reg in time_groups[t]:
            val = get_value(reg, mode)
            if val == 0:
                continue
            y0 = int((reg['start'] - min_s) * nrows_y / span)
            y1 = int((reg['end'] - min_s) * nrows_y / span)
            y0 = max(0, min(y0, nrows_y - 1))
            y1 = max(y0 + 1, min(y1, nrows_y))
            for y in range(y0, y1):
                heatmap[y][ti] += val / max(y1 - y0, 1)

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

    colors = ['#000000', '#1a0000', '#4d0000', '#990000',
              '#cc2200', '#ee5500', '#ff8800', '#ffbb00',
              '#ffee00', '#ffffff']
    cmap = LinearSegmentedColormap.from_list('damon', colors, N=256)

    # log scale: makes low values visible while still showing hot spots
    # mask zeros so they stay black
    heatmap_masked = np.ma.masked_where(heatmap == 0, heatmap)
    cmap.set_bad(color='black')

    nonzero = heatmap[heatmap > 0]
    if len(nonzero) > 0:
        vmin = 0.5
        vmax = np.percentile(nonzero, 95)  # clip top 5% to spread color range
        vmax = max(vmax, 1)
    else:
        vmin, vmax = 0.5, 1

    extent = [times[0], times[-1], min_s, max_s]
    im = ax.imshow(heatmap_masked, aspect='auto', cmap=cmap, origin='lower',
                   extent=extent, norm=LogNorm(vmin=vmin, vmax=vmax),
                   interpolation='bilinear')

    ax.set_xlabel('Time (s)', color='white', fontsize=12)
    ax.set_ylabel('LBA (sector)', color='white', fontsize=12)

    title_map = {'total': 'Total I/O', 'read': 'Read', 'write': 'Write'}
    ax.set_title(f'SAMON Storage Access Heatmap ({title_map.get(mode, mode)})',
                 color='white', fontsize=14, fontweight='bold')

    ax.tick_params(colors='white', labelsize=9)
    ax.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
    ax.yaxis.get_offset_text().set_color('white')

    for spine in ax.spines.values():
        spine.set_color('#333333')

    cbar = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cbar.set_label('Access Intensity', color='white', fontsize=11)
    cbar.ax.tick_params(colors='white', labelsize=9)

    plt.tight_layout()
    plt.savefig(output, dpi=150, facecolor='black', edgecolor='none')
    print(f"Saved: {output}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("-o", "--output", default="samon_heatmap.png")
    p.add_argument("-m", "--mode", choices=["total", "read", "write"], default="total")
    args = p.parse_args()
    plot(args.csv, args.output, args.mode)
