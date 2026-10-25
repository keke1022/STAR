#!/bin/sh
# Read-only environment capture for the STAR VM vs CVM comparison .
# Runs unprivileged on a host or inside a guest; it does not change system settings. Some fields need
# root inside a guest (dmesg, debugfs); without it they are reported as "unavailable".
# Usage: collect-env.sh [OUT_DIR]   (default: ./env-<utc time>)
set -u
out=${1:-./env-$(date -u +%Y%m%dT%H%M%SZ)}
mkdir -p "$out"
cap() { name=$1; shift; { "$@"; } >"$out/$name.txt" 2>&1 || echo "(exit $?)" >>"$out/$name.txt"; }
val() { [ -r "$1" ] && cat "$1" 2>/dev/null || echo unavailable; }

# --- identity and platform ---------------------------------------------------------------
cap uname uname -srmo
cap os-release cat /etc/os-release
cap lscpu lscpu
cap cmdline cat /proc/cmdline
cap virt sh -c 'systemd-detect-virt 2>/dev/null || echo none; systemd-detect-virt --cvm 2>/dev/null || echo "cvm: none or unknown"'
cap dmi sh -c 'for f in sys_vendor product_name product_version bios_version; do printf "%s: " $f; cat /sys/class/dmi/id/$f 2>/dev/null || echo unavailable; done'

# --- memory encryption / confidential computing --------------------------------------------
cap cpu-flags-sev sh -c 'grep -m1 -o -w -E "sev|sev_es|sev_snp|sme|tsc_scale|vmmcall|hypervisor" /proc/cpuinfo | sort -u'
cap sev-devices sh -c 'ls -l /dev/sev /dev/sev-guest /dev/tpm0 /dev/tpmrm0 2>&1'
cap kvm-amd sh -c 'for p in sev sev_es sev_snp; do printf "kvm_amd.%s: " $p; cat /sys/module/kvm_amd/parameters/$p 2>/dev/null || echo unavailable; done'
cap dmesg-cc sh -c 'if log=$(dmesg 2>&1); then printf "%s\n" "$log" | grep -i -E "memory encryption|sev|snp|swiotlb|bounce|tdx" | head -50; else printf "%s\n" "$log"; exit 1; fi'
cap swiotlb sh -c 'cat /sys/kernel/debug/swiotlb/io_tlb_nslabs /sys/kernel/debug/swiotlb/io_tlb_used 2>/dev/null || echo "debugfs swiotlb unavailable (needs root)"'

# --- memory, NUMA, paging -----------------------------------------------------------------
cap meminfo cat /proc/meminfo
cap numa sh -c 'numactl --hardware 2>/dev/null || lscpu | grep -i numa'
cap thp sh -c 'printf "enabled: "; cat /sys/kernel/mm/transparent_hugepage/enabled; printf "defrag: "; cat /sys/kernel/mm/transparent_hugepage/defrag'
cap hugepages sh -c 'grep -i huge /proc/meminfo'
cap unaccepted sh -c 'grep -i unaccepted /proc/meminfo || echo "no Unaccepted field (kernel without lazy acceptance, or not a CVM)"'

# --- CPU frequency, clocks ------------------------------------------------------------------
cap clocksource sh -c 'cat /sys/devices/system/clocksource/clocksource0/current_clocksource /sys/devices/system/clocksource/clocksource0/available_clocksource 2>&1'
cap cpufreq sh -c 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>&1 || echo unavailable'

# --- storage --------------------------------------------------------------------------------
cap lsblk lsblk -o NAME,SIZE,TYPE,ROTA,MODEL,FSTYPE,MOUNTPOINT
cap df df -hT
cap scheduler sh -c 'for d in /sys/block/*/queue/scheduler; do echo "$d: $(cat $d)"; done'

# --- profiling capability -------------------------------------------------------------------
{
  echo "perf_event_paranoid: $(val /proc/sys/kernel/perf_event_paranoid)"
  echo "kptr_restrict: $(val /proc/sys/kernel/kptr_restrict)"
  for tool in perf bpftrace valgrind gprof strace ltrace numactl pidstat iostat vmstat mpstat; do
    printf "%s: " "$tool"; command -v "$tool" || echo missing
  done
  if command -v perf >/dev/null 2>&1; then
    for ev in task-clock page-faults context-switches cpu-clock:u cycles:u instructions:u cache-misses:u dTLB-load-misses:u; do
      if perf stat -x, -e "$ev" true >/dev/null 2>"$out/.perf-$ev.err"; then
        echo "perf event $ev: ok"
      else
        echo "perf event $ev: unavailable ($(tr '\n' ' ' <"$out/.perf-$ev.err" | cut -c1-120))"
      fi
      rm -f "$out/.perf-$ev.err"
    done
    # Sampling is probed per event class on a short CPU loop, and counts as available only if
    # samples were actually recorded: software (cpu-clock, works without a PMU) and hardware
    # (cycles, needs a PMU) are reported separately.
    probe_dir=$(mktemp -d)
    for ev in cpu-clock:u cycles:u; do
      if perf record -q -o "$probe_dir/p.data" -e "$ev" -F 999 -g -- \
           sh -c 'i=0; while [ $i -lt 400000 ]; do i=$((i+1)); done' >/dev/null 2>"$probe_dir/err"; then
        n=$(perf script -i "$probe_dir/p.data" 2>/dev/null | grep -c -E "^ *sh +[0-9]+")
        if [ "${n:-0}" -gt 0 ]; then echo "perf record -e $ev: ok ($n samples)"
        else echo "perf record -e $ev: ran but recorded no samples"; fi
      else
        echo "perf record -e $ev: unavailable ($(tr '\n' ' ' <"$probe_dir/err" | cut -c1-120))"
      fi
      rm -f "$probe_dir/p.data" "$probe_dir/p.data.old"
    done
    rm -rf "$probe_dir"
  fi
  ls /sys/bus/event_source/devices/ 2>/dev/null | tr '\n' ' ' | sed 's/^/PMU devices: /'; echo
} >"$out/profiling.txt" 2>&1

# --- load at capture time (so a busy host is visible) ----------------------------------------
cap load sh -c 'cat /proc/loadavg; free -g'

# --- summary --------------------------------------------------------------------------------
{
  echo "captured: $(date -u +%FT%TZ)"
  echo "cpu: $(lscpu | sed -n 's/^Model name: *//p')"
  echo "virt: $(head -1 "$out/virt.txt")  cvm: $(sed -n 2p "$out/virt.txt")"
  echo "sev flags: $(tr '\n' ' ' <"$out/cpu-flags-sev.txt")"
  echo "kernel: $(uname -r)"
  echo "memory: $(awk '/MemTotal/{t=$2}/MemAvailable/{a=$2}END{printf "%.0f GiB total, %.0f GiB available", t/1048576, a/1048576}' /proc/meminfo)"
  echo "thp: $(sed -n 1p "$out/thp.txt")"
  echo "clocksource: $(head -1 "$out/clocksource.txt")"
  grep -E "perf_event_paranoid|perf event|perf record" "$out/profiling.txt"
  echo "note: software sampling (cpu-clock) and hardware events are probed separately; a missing PMU"
  echo "      does not make software sampling unavailable."
} >"$out/SUMMARY.txt"
cat "$out/SUMMARY.txt"
echo "full capture: $out"
