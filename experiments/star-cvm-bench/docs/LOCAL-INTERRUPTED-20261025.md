# Interrupted local pilot — 2026-10-25

**No VM/SNP performance comparison was obtained.** The first ordinary-VM
window ran on a shared host with conflicting CPU affinities and rapidly changing
memory availability. Measurement was stopped before any timed SNP window.
All completed samples are retained; this batch is excluded from future timing
comparisons, including its faster samples.

## Completed evidence

The workload was STAR 2.7.11b, the complete BDGP6.54 index and the first 100,000
DRR129224 read pairs. The runner was commit
`f634f8c76a107074037137166c543429cf203c3a`. The ordinary VM had 8 vCPUs and 10 GiB
configured memory. The one-thread batch completed one warm-up and five timed runs.

| Run | Process wall time (seconds) |
| --- | ---: |
| Warm-up | 18.043218 |
| 1 | 28.842401 |
| 2 | 28.692245 |
| 3 | 14.086530 |
| 4 | 28.744161 |
| 5 | 14.633158 |

After copying the complete batch out of the guest, `inspect_batch(..., "vm", 5)`
recomputed all six raw output signatures successfully: 220,318 SAM records and
10,290 splice-junction rows, with matching alignments, junctions and non-time
statistics. This establishes repeatability within this batch. It does not
establish a useful performance baseline. The four-thread batch was interrupted;
its partial files remain on the retained guest disk and have not been retrieved
or validated. There are zero timed SNP runs.

The curated [machine-readable record](../results/local-interrupted-20261025.json)
contains unrounded timings and hashes of the retained local evidence. Raw SAM,
launch configuration, guest environment and host logs remain outside Git.

## Why the experiment stopped

A contemporaneous host review found other QEMU threads pinned to overlapping
physical CPUs, including experiment vCPU and emulator CPU assignments. Host-wide
memory counters also changed substantially during the window. The 376 host
observations from 20:02:47 to 20:09:03 UTC recorded MemAvailable falling from
442,465,992 KiB to 165,279,516 KiB and Unevictable increasing from 118,434,172 KiB
to 391,695,912 KiB. These are whole-host observations across the window, not
per-run attribution. They do not prove the cause of the roughly twofold spread.
Guest observations alone did not reveal this host allocation problem.

The original launch check considered global MemAvailable and missed the
constraint imposed by strict NUMA placement. Later, at 20:15:46 UTC, the proposed
replacement node had only 1,260,588 KiB free, while host-wide MemAvailable was
23,839,244 KiB. Moving CPU affinity did not provide adequate RAM on that node.

Shutdown also needed follow-up: the normal shutdown wait expired, guest SSH was
unresponsive, and a force-stop request reported that it could not terminate the
process. A subsequent independent state check confirmed the process had exited
and both experiment domains were shut off. The specific cause of the delayed
exit has not been established. Other workloads and host-wide settings were not
modified, and both experiment disks were retained.

## Prepared continuation

Only the two stopped experiment domains were reconfigured. The existing full
inactive XML was retained, changing only vCPU affinity, emulator affinity and
the strict NUMA node. The complete readback matched the intended configuration;
UUIDs, devices, disks and memory size remained unchanged. Both guests stayed off.
Read-only launch checks rejected both guests because the target node had about
1.2 GiB free, below the 14 GiB required by the current 10 GiB + 4 GiB rule.

Before resuming, recheck current resource allocation and the latest operating
instructions. Adequate target-node headroom and a usable measurement window are
required; changing affinity alone is insufficient. Follow the updated
[local protocol](LOCAL-PAIR.md), use fresh window identifiers, and keep the
interrupted batch excluded. Global free memory, one successful preflight or a
correct output signature alone is not evidence of a fair VM/SNP comparison.
