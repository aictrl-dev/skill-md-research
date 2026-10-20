#!/bin/sh
# measure.sh <sample:0|1> <trace:0|1> -- cmd args...
#
# Writes the harness config (BENCH_CFG{1,2}_PATH / _B64) into the empty HOME, then runs the
# command once. Markers on stdout: "@@RUN" before the start, "@@EXIT <code>" after. On stderr:
#   @@TIME <max RSS kB of the largest process, /usr/bin/time -v>
#   @@PEAK <cgroup memory.peak bytes for the whole container>
#   MEM <epoch ms> <cgroup memory.current bytes> <summed RSS kB of all processes>   (sample=1, every 250 ms)
#   @@NET <strace line>   (trace=1: every connect/sendto/sendmsg/sendmmsg not on a unix/netlink socket)
sample=$1; trace=$2; shift 3
for metric in memory.current memory.peak; do
  if [ ! -r "/sys/fs/cgroup/$metric" ]; then
    echo "@@MEASUREMENT_ERROR cgroup v2 $metric unavailable" >&2
    exit 125
  fi
done
trap '[ -z "${sampler:-}" ] || kill "$sampler" 2>/dev/null || :' EXIT
for n in 1 2; do
  eval "p=\${BENCH_CFG${n}_PATH:-}; b=\${BENCH_CFG${n}_B64:-}"
  if [ -n "$p" ]; then mkdir -p "$(dirname "$p")" && echo "$b" | base64 -d > "$p"; fi
done
if [ "$sample" = 1 ]; then
  ( while :; do
      echo "MEM $(date +%s%3N) $(cat /sys/fs/cgroup/memory.current) $(ps -e -o rss= | awk '{s+=$1} END {print s}')" >&2
      sleep 0.25
    done ) &
  sampler=$!
fi
echo "@@RUN"
if [ "$trace" = 1 ]; then
  strace -f -qq -s 256 -e trace=connect,sendto,sendmsg,sendmmsg -e signal=none -o /tmp/strace.out "$@"
  code=$?
else
  /usr/bin/time -v -o /tmp/time.txt "$@"
  code=$?
fi
echo "@@EXIT $code"
[ -n "$sampler" ] && kill $sampler
[ -f /tmp/time.txt ] && grep -E "Maximum resident set size" /tmp/time.txt | sed "s/.*: */@@TIME /" >&2
echo "@@PEAK $(cat /sys/fs/cgroup/memory.peak)" >&2
[ -f /tmp/strace.out ] && grep -v -E 'AF_UNIX|AF_NETLINK|resumed>' /tmp/strace.out | sed "s/^/@@NET /" >&2
exit 0
