# Experiment protocol v1

## Question and scope

Measure whether STAR has a reproducible confidential-VM penalty on the selected
workload, identify the responsible execution phases, and reduce that penalty
while preserving alignment behavior. Repository age alone is not evidence of a
missing optimization: upstream already has optimized compilation, SIMD,
parallelism and index memory/speed tradeoffs.

- [Upstream build](https://github.com/alexdobin/STAR/blob/2.7.11b/source/Makefile)
- [Upstream parameters](https://github.com/alexdobin/STAR/blob/2.7.11b/source/parametersDefault)

Start with paired-end bulk RNA-seq. Single-cell, long-read and two-pass modes are
different workloads, not pooled samples. Pin a release, commit, compiler, flags,
binary SHA-256, input/reference/annotation hashes, index parameters and RNG seed.
An index built for one configuration must not silently substitute for another.
Build the canonical guest binary on the pinned guest image, record its dynamic
library versions, and copy that binary to both guests. A development-host binary
may depend on a newer libc/libstdc++ and is not automatically portable.

## Workloads and correctness

1. Tiny deterministic synthetic data: validate tools, failures and reproducibility.
2. Public reads with their matching complete small reference: pilot experiments.
3. Representative human RNA-seq and full matching reference/annotation: main
   result if resources permit; specify accessions and deterministic read selection.

A single human chromosome paired with unfiltered human reads measures a different
mapping workload. It can test execution but does not stand in for human-genome
performance. Download/setup and index generation are measured separately from
alignment. Record read pairs, read length, mapping categories and multimapping.

Require equivalent alignments (including positions, CIGAR, flags, scores and tags),
splice-junction output and relevant quantification outputs. Preserve duplicates;
do not compare BAM hashes that change due to compression or command metadata.
If an optimization deliberately changes accuracy, stop the equivalent-output
comparison and define a separate accuracy/performance study before accepting it.

## Matched environments

Use ordinary VM and SNP VM on the same CPU generation, instance size, vCPU/SMT
topology, memory, zone, exact OS image and kernel, disk type/size/interface, STAR
binary/index/inputs, filesystem and command. Record CPU model/features and actual
disk paths inside both guests. Matching a machine name alone is insufficient.
Record encrypted-memory mode and collect supported attestation evidence; a
user-supplied `snp` label does not prove a confidential guest.

The two cloud instances need not share a physical host. Alternate measurements
and, for a publication, repeat allocations to assess host-placement variance.
The shared development server also hosts the approved local exploratory VM/SNP
pair (see LOCAL-PAIR.md). Native-host runs remain smoke tests. Record interference
from unrelated workloads; do not modify existing VMs, global caches, kernel
settings or NUMA placement of unrelated workloads.

## Measurement matrix

The key matrix has four cells: ordinary VM/upstream, CVM/upstream,
ordinary VM/optimized, CVM/optimized. Use at least five timed replicates after a
declared warm-up policy, alternating cells in reproducible randomized blocks.
Report individual samples, median and spread; preserve slow runs and explain
exclusions. Profiled and unprofiled runs are separate because profiling perturbs
execution. Short smoke runs validate plumbing, not performance.

- Confidential overhead: `T(CVM, upstream) / T(VM, upstream) - 1`.
- CVM speedup: `T(CVM, upstream) / T(CVM, optimized)`.
- Ordinary-VM speedup: `T(VM, upstream) / T(VM, optimized)`.
- Preferential CVM improvement: ratio of the two speedups, with uncertainty.

A general optimization can improve both environments and still be useful; it
does not by itself establish a CVM-specific mechanism. Also report throughput,
CPU time, peak RSS, page faults, context switches, storage I/O and billed cost
where measurable. No numerical speedup or completion time is promised upfront.

## Phases and cache conditions

Separate reference indexing, process/index load, mapping, sorting/compression and
output. STAR log timestamps are coarse; add monotonic phase timestamps if needed,
measure their overhead, and do not attribute sub-second changes from whole-second
logs. Keep instrumentation in an isolated commit/build.

Distinguish VM boot/attestation, first process, fresh private pages, filesystem
page cache, and process-shared indices. Repeated process execution can warm the
filesystem cache while still faulting fresh guest-private pages. Hashing inputs
also warms caches. Cold experiments require a recorded dedicated-guest cache/reset
protocol after fingerprinting; never clear caches on the shared host.

Measure useful output workloads separately: SAM correctness lane, sorted BAM
end-to-end lane, and optional output-free diagnostic lane. A no-output benchmark
cannot be presented as faster completion of the original BAM-producing job.

## Trace-driven hypotheses

Start with STAR logs, GNU time and guest process/I/O counters. Probe actual guest
permissions and supported events before using perf. Root does not guarantee PMU
availability; unavailable hardware counters are missing data, never zero. Use
frame-pointer software stack sampling if supported. User-space instrumentation
is the fallback; gprof/callgrind results are diagnostic, not native run timings.

Candidate explanations include memory traffic and cache locality, private-page
initialization, I/O bouncing, scheduler/interrupt overhead, and NUMA placement.
Evidence must distinguish them: phase timing, available counters, stack samples,
I/O toggles and controlled microbenchmarks. Do not claim guest counters expose
host VM exits, or that an encryption/page-acceptance mechanism was measured when
only wall time increased.

Change one factor at a time, rerun correctness and all four matrix cells, and
retain an ablation. Candidate optimizations follow the measured bottleneck; SIMD,
I/O batching, decompression, index layout or worker scheduling are not selected
before evidence. Security mode remains enabled; disabling protection is not an
acceptable CVM optimization.

## Resource decision

Prepare exact resources, image, disk size, lifetime, cost bound and cleanup scope
before provisioning. Local smoke preparation proceeds independently. Actual
measurement still needs a dedicated VM/CVM pair; this repository does not create
or delete cloud or local virtual machines by running a benchmark.
