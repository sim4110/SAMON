#!/usr/bin/env python3
"""
SAMON - Storage Access MONitor
Phase 1: LBA region heatmap with DAMON-style sampling intervals
"""
from bcc import BPF
from time import sleep, strftime
import sys

# --- Configuration (DAMON-style intervals) ---
NR_REGIONS = 64
AGGR_INTERVAL = 2

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/blk_types.h>

#define NR_REGIONS 64

BPF_ARRAY(read_counts, u64, NR_REGIONS);
BPF_ARRAY(write_counts, u64, NR_REGIONS);

int trace_bio(struct pt_regs *ctx, struct bio *bio) {
    u64 sector = bio->bi_iter.bi_sector;
    int rw = bio->bi_opf & 1;

    // simple fixed mapping: assume ~240GB device (500M sectors)
    u64 max_s = 500000000ULL;
    u32 region = (u32)((sector * NR_REGIONS) / max_s);
    if (region >= NR_REGIONS)
        region = NR_REGIONS - 1;

    if (rw) {
        write_counts.atomic_increment(region);
    } else {
        read_counts.atomic_increment(region);
    }
    return 0;
}
"""

b = BPF(text=bpf_text)
b.attach_kprobe(event="blk_mq_submit_bio", fn_name="trace_bio")

def render(reads, writes):
    blocks = " ░▒▓█"
    max_val = max(max(reads), max(writes), 1)

    print(f"\n===== SAMON [{strftime('%H:%M:%S')}] =====")
    print(f"Reads: {sum(reads)}  Writes: {sum(writes)}  Interval: {AGGR_INTERVAL}s")

    sys.stdout.write("R |")
    for v in reads:
        idx = min(int(v * (len(blocks)-1) / max_val), len(blocks)-1) if max_val else 0
        sys.stdout.write(blocks[idx])
    print("|")

    sys.stdout.write("W |")
    for v in writes:
        idx = min(int(v * (len(blocks)-1) / max_val), len(blocks)-1) if max_val else 0
        sys.stdout.write(blocks[idx])
    print("|")

    combined = [(reads[i]+writes[i], i) for i in range(NR_REGIONS)]
    combined.sort(reverse=True)
    hot = [(c, i) for c, i in combined[:5] if c > 0]
    if hot:
        print("Hot:", ", ".join(f"R{i}({c})" for c, i in hot))
    sys.stdout.flush()

print("SAMON starting...")

while True:
    try:
        sleep(AGGR_INTERVAL)
        reads = [b["read_counts"][i].value for i in range(NR_REGIONS)]
        writes = [b["write_counts"][i].value for i in range(NR_REGIONS)]
        render(reads, writes)
        b["read_counts"].clear()
        b["write_counts"].clear()
    except KeyboardInterrupt:
        print("\nStopped.")
        exit()
