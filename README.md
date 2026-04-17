# SAMON - Storage Access MONitor

eBPF-based storage I/O access pattern monitoring and visualization tool, inspired by DAMON (Data Access MONitor).

## Overview

SAMON monitors block device I/O patterns by attaching eBPF kprobes to the Linux kernel's block layer (`blk_mq_submit_bio`), providing DAMON-style adaptive region-based monitoring for storage devices.

## Components

| File | Description |
|------|-------------|
| `samon_probe.py` | Raw I/O event tracer — prints individual block I/O events |
| `samon_heatmap.py` | Simple terminal-based LBA heatmap |
| `samon_monitor.py` | Main monitor with adaptive regioning + CSV logging |
| `samon_plot.py` | Matplotlib heatmap visualization from CSV logs |

## Usage

```bash
# Raw I/O tracing
sudo python3 samon_probe.py

# Terminal heatmap
sudo python3 samon_heatmap.py

# Full monitoring with CSV output (2s interval, 60s duration)
sudo python3 samon_monitor.py -i 2 -d 60 -o samon_log.csv

# Generate heatmap image from CSV
python3 samon_plot.py samon_log.csv -o heatmap.png
```

## Requirements

- Linux kernel 5.15+ with BPF support
- python3-bpfcc (BCC Python bindings)
- matplotlib (for visualization)

## License

MIT
