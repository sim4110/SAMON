#!/usr/bin/env python3
from bcc import BPF
from time import strftime

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/blk_types.h>

struct event_t {
    u64 ts;
    u64 sector;
    u32 len;
    u32 pid;
    u8 rwflag;
    char comm[16];
};

BPF_PERF_OUTPUT(events);

int trace_bio(struct pt_regs *ctx, struct bio *bio) {
    struct event_t event = {};
    event.ts = bpf_ktime_get_ns();
    event.sector = bio->bi_iter.bi_sector;
    event.len = bio->bi_iter.bi_size;
    event.pid = bpf_get_current_pid_tgid() >> 32;
    event.rwflag = (bio->bi_opf & 1) ? 1 : 0;
    bpf_get_current_comm(&event.comm, sizeof(event.comm));
    events.perf_submit(ctx, &event, sizeof(event));
    return 0;
}
"""

b = BPF(text=bpf_text)
b.attach_kprobe(event="blk_mq_submit_bio", fn_name="trace_bio")

print("%-18s %-6s %-16s %-4s %-14s %s" %
      ("TIMESTAMP", "PID", "COMM", "R/W", "SECTOR", "BYTES"))

def print_event(cpu, data, size):
    e = b["events"].event(data)
    rw = "W" if e.rwflag else "R"
    print("%-18s %-6d %-16s %-4s %-14d %d" %
          (strftime("%H:%M:%S"), e.pid, e.comm.decode('utf-8', 'replace'),
           rw, e.sector, e.len))

b["events"].open_perf_buffer(print_event)
print("Tracing block I/O... Ctrl+C to stop.\n")
while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
