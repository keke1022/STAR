# Local ordinary-VM / SNP-VM pilot

Selected on 2026-10-25. This replaces the GCP pair for the first experiment;
cloud login, project and budget are not prerequisites. The guests have not yet
been measured. This is an exploratory experiment on a shared physical host.

## Preparation and evidence

- Use the existing complete BDGP6.54 reference, annotation and DRR129224 first
  100,000 paired reads in INPUTS.md and DROSOPHILA-PILOT.md. Do not mix the older
  partial-human-reference smoke data into these results.
- Run one guest at a time, initially at most 8 vCPU and 12 GiB per guest, subject
  to a fresh capacity check including QEMU overhead and a host memory reserve.
  Use independent writable disks derived from the same immutable image, with
  equal format, size, backing layout, cache mode and virtual storage interface.
  Never attach the same writable disk to both guests.
- Preserve existing workloads, devices, networks, storage pools and global
  host settings. Do not reclaim another VM's RAM for this experiment. If the
  selected guest size does not fit, reduce both sizes equally or stop launch.
- Record QEMU/firmware hashes, exact image/kernel, CPU model and exposed flags,
  vCPU topology/affinity, NUMA policy and disk settings for both guests. Record
  unavoidable differences, including SNP memory allocation and boot requirements.
- Capture guest evidence that SNP is active, plus the launch configuration.
  A VM name, host capability or the runner's `--environment snp` label is not
  evidence of activation. Boot/activation evidence is not independently verified
  remote attestation; retain that distinction in the report.
- Build one STAR binary on the pinned guest image, record compiler, flags and
  dynamic library versions, then copy the same binary and frozen index/inputs to
  the other guest. Do not assume the development host's binary is ABI-compatible.
  Run tools/collect-env.sh in each guest outside timed measurement, retaining raw
  results locally. Matching manifests cannot substitute for environment review.

## Execution

Both guests use the same repository commit and tools. Fill a separate
`local.workload.json` from the example with actual paths and provenance. Paths
may differ; binary, index, reads, arguments and build identity must agree.

Run the bounded observer **on the physical host** for each guest's whole window:

```sh
python3 tools/observe_host.py --seconds 1800 --out local.host-vm-window1.jsonl
```

Run this in a separate terminal or track its PID explicitly. It reads pressure,
memory, load and swap counters, changes no settings, and exits at the deadline
or on SIGINT/SIGTERM. Guest observations do not measure host pressure; retain both.
Missing files/counters mean unavailable evidence, not zero pressure. Swap counters
and PSI are system-wide signals, not per-STAR resource attribution.

Inside the ordinary guest, run these sequentially:

```sh
python3 tools/star_bench.py run --config local.workload.json \
  --environment vm --threads 1 --warmups 1 --repetitions 5 --out runs/vm-window1-1t
python3 tools/star_bench.py run --config local.workload.json \
  --environment vm --threads 4 --warmups 1 --repetitions 5 --out runs/vm-window1-4t
```

Repeat in the SNP guest with `--environment snp` and distinct output directories.
Always finish and stop the current guest before starting the other. A first
VM-then-SNP pass only establishes execution, output agreement and an exploratory
timing ratio. For an interpretable comparison, reverse the order in another
window (VM, SNP, SNP, VM overall), keeping the declared warm-up policy. Preserve
all raw samples and window identities; runs within a single boot are not
independent host allocations. More replications may be needed if noise is high.

Copy each whole result directory to the review machine. Compare like thread
counts, keeping the raw STAR files available for recomputation:

```sh
python3 tools/compare_batches.py runs/vm-window1-1t runs/snp-window1-1t
python3 tools/compare_batches.py runs/vm-window1-4t runs/snp-window1-4t
```

The checker requires five timed replicates by default, equal workload and runner
fingerprints, equal controlled parameters and successful runs. It recomputes
every output signature, rejects changed alignments/junctions/statistics, and
returns nonzero on failure. PASS means those checks passed. It does not certify
the hardware, SNP activation, fairness or a speedup. Each raw run records pressure
observations before and after timing, outside the timed interval. Compare tool
cost and sampling overhead equally across the two environments.

## Interpretation

Fingerprinting warms caches. These are fresh processes using NoSharedMemory,
uncontrolled filesystem cache after hashing, and SAM output; they are not cold
boot, already-loaded-index, sorted-BAM or isolated mapping measurements. Index
construction and profiling remain separate workloads.

Review host load/pressure/swap alongside guest observations and individual timings.
Retain slow samples and explain contamination; do not delete outliers because
they obscure a desired result. If interference dominates the observed difference,
report the comparison as inconclusive. Neither a matched configuration nor a
wall-time ratio establishes a memory-encryption mechanism. Actual tracing and
controlled changes follow the measured phases; GPU hardware is not used.

Commit only reviewed, curated summaries. Raw runs/launch configs/host observations
may contain local paths or machine metadata and remain outside version control.
