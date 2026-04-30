#!/bin/bash
RESULTS="/home/sang/SAMON/bench_results.csv"
FIO_FILE="/tmp/fio_bench"
DURATION=30
DEVICE="dm-0"

echo "test,rw,iops,bw_kib,lat_avg_us,lat_p99_us" > "$RESULTS"

run_fio() {
    local label=$1
    local rw=$2
    fio --name=bench --filename=$FIO_FILE --size=512M \
        --rw=$rw --bs=4k --direct=1 --numjobs=4 --runtime=$DURATION \
        --time_based --group_reporting --output-format=json 2>/dev/null | \
    python3 -c "
import json, sys
d = json.load(sys.stdin)
for jt in ['read', 'write']:
    j = d['jobs'][0][jt]
    if j['iops'] > 0:
        print('${label},${rw}_%s,%d,%d,%.1f,%.1f' % (
            jt, j['iops'], j['bw'], j['lat_ns']['mean']/1000, j['clat_ns']['percentile']['99.000000']/1000))
" >> "$RESULTS"
}

echo "=== 1/3: Native ==="
for rw in randread randwrite randrw; do
    echo "  $rw..."
    run_fio "native" "$rw"
    sync; echo 3 > /proc/sys/vm/drop_caches; sleep 2
done

echo "=== 2/3: blktrace ==="
for rw in randread randwrite randrw; do
    echo "  $rw + blktrace..."
    cd /tmp && blktrace -d /dev/$DEVICE -o bt_bench -w $((DURATION+5)) &
    BTPID=$!
    sleep 1
    run_fio "blktrace" "$rw"
    kill $BTPID 2>/dev/null; wait $BTPID 2>/dev/null
    rm -f /tmp/bt_bench.blktrace.* 2>/dev/null
    sync; echo 3 > /proc/sys/vm/drop_caches; sleep 2
done

echo "=== 3/3: SAMON ==="
for rw in randread randwrite randrw; do
    echo "  $rw + SAMON..."
    python3 /home/sang/SAMON/samon_monitor.py -i 1 -d $((DURATION+5)) -s 251658240 -o /dev/null -q &
    SPID=$!
    sleep 1
    run_fio "samon" "$rw"
    kill $SPID 2>/dev/null; wait $SPID 2>/dev/null
    sync; echo 3 > /proc/sys/vm/drop_caches; sleep 2
done

rm -f $FIO_FILE
echo ""
echo "=== Results ==="
column -t -s',' "$RESULTS"
echo ""
echo "Saved to $RESULTS"
