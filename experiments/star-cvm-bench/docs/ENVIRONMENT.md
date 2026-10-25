# STAR VM vs CVM: environment, fair comparison and sampling plan

Status: draft, 2026-10-25. Nothing has been created or changed; every command below is a draft.
Resource names use the `bio-star-` prefix. STAR build and data provenance are recorded separately in this experiment directory.

## 1. Development-host limits

Local smoke tests share a development host with other workloads. Use low thread
counts, preserve existing virtual machines and global kernel settings, and check
available memory before a run. Do not treat native-host timings as VM measurements.
The local capability probe found `perf_event_paranoid=4` and denied both software
sampling and hardware counters. That is a permission result, not proof that the
hardware lacks a PMU. Keep raw environment inventories outside Git.

## 2. Two ways to get a fair VM / CVM pair

Rules for either: same CPU platform, same vCPU count and memory, same image and kernel, same disk
type and size, same zone/host, same STAR binary (task #2 pins it) and inputs; run the two
alternately, at least 5 timed repetitions each after declared warm-ups, reporting median and spread.
Fresh boot, cold filesystem cache, warm filesystem cache and an already loaded
process index are distinct conditions; see PROTOCOL.md.

### Option A: GCP N2D pair (recommended for the main result)

From the official supported-configurations page: SEV-SNP Confidential VM is **N2D only, AMD Milan
only**, in asia-southeast1 (a,b,c), europe-west2 (b,c), europe-west3 (a,b,c), europe-west4 (a,b,c)
and us-central1 (a,b,c). Images must be tagged `SEV_SNP_CAPABLE`; no live migration (set
`--maintenance-policy=TERMINATE`), no kdump, no reservations; Confidential VMs need the NVMe disk
interface. Google notes that guest kernel updates between August and November 2026 may change
boot time and performance, so pin and record the image and kernel.

PMU: Compute Engine offers a PMU only on A4X, C4A, C4 and M4; it is off by default and **not
available on N2D**. Both sides therefore get software events only (`cpu-clock`, `task-clock`,
`page-faults`, context switches, tracepoints, kprobes/uprobes as root); no hardware counters on
either side. That keeps the comparison symmetric but rules out cycle, cache and TLB counts there.

#### Concrete configuration (draft for the resource decision; `gcp-plan-a.sh`)

| Item | Both machines | Notes |
|---|---|---|
| Names | `bio-star-vm-<RUN_ID>`, `bio-star-snp-<RUN_ID>` | requested configurations differ by `--confidential-compute-type=SEV_SNP`; actual parity remains to be checked |
| Zone | `us-central1-a` | any SEV-SNP zone works; both in the same zone |
| Machine | `n2d-highmem-8` (8 vCPU, 64 GB) | human index about 32 GB plus 8 mapping threads |
| CPU platform | `--min-cpu-platform="AMD Milan"` | SEV-SNP is Milan-only; this is a minimum-platform constraint, not an exact pin; compare actual CPU platforms before accepting a pair |
| Image | family `ubuntu-2404-lts-amd64`, project `ubuntu-os-cloud`; **not yet pinned**. The read-only lookup (`gcp-plan-a.sh preflight`) failed on 2026-10-25: the available gcloud login needs interactive renewal. Pin the exact image name only after the lookup shows `SEV_SNP_CAPABLE` in its features | Ubuntu documents 24.04 LTS as a full SEV-SNP guest, but no public page lists the GCE tag per image, so the tag must be read from the image itself |
| Kernel | whatever the pinned image ships; recorded (`uname -r`) on both before any run | SNP needs 6.1 or later; 24.04 ships 6.8+ |
| Boot disk | 300 GB `pd-ssd`, auto-delete, `--boot-disk-interface=NVME` on **both** | N2D supports `pd-ssd` (machine-series docs). Confidential VMs require NVMe. gcloud 590.0.1 has `--boot-disk-interface` (SCSI or NVME), but no page found states that a plain N2D VM accepts an NVMe boot disk: **unverified**. The interface is read back after creation. If the plain VM cannot use NVMe, the interface differs, which is a confounder (see below) |
| Maintenance | `TERMINATE` on both | required for SEV-SNP |
| Lifetime | `--max-run-duration=6h --instance-termination-action=DELETE` as a **backstop only** | both flags exist in gcloud 590.0.1 (GA); the documented restrictions (stop or delete only, 30 s to 120 days, no legacy preemptible VMs, may run up to 30 s late) do not mention Confidential VM, but compatibility is **not verified**. Explicit cleanup and `verify-clean` after every session stay mandatory regardless |
| Access | OS Login; no new firewall rules; an ephemeral external IP for the data downloads (released with the instance) | if the project's network needs an IAP SSH rule, it would be one rule named `bio-star-iap-ssh`, deleted at cleanup |
| Labels | `experiment=bio-star`, `run=<RUN_ID>` | used by `verify-clean` |

If the disk interfaces cannot be made equal, the comparison is not "only SNP differs": the
interface is listed as a confounder, and every measurement is also run in a memory-resident,
low-I/O variant (inputs and index on tmpfs, outputs to tmpfs) to assess sensitivity to the storage path. A tmpfs control still includes copying,
faults and memory pressure; it does not by itself isolate memory-encryption cost.
Only use it when index, inputs, outputs and STAR memory fit comfortably in RAM.

First-session proposal: two machines, at most six hours each, followed by
explicit deletion of the two instances and their auto-delete boot disks. No
bucket, snapshots, images, static IPs or extra disks are included. Resource
cleanup checks are restricted to the exact pair's names and project/zone;
remaining resources cause `verify-clean` to fail.

Current public list-price arithmetic is about $6.64 for this six-hour pair,
excluding transfer and tax. See [the cost proposal](COSTS.md) for source rates
and the proposed $15 operating limit. No resources have been authorized yet.

### Option B: a local pair on this host (cheap, same silicon, small inputs only)

A local SNP-capable host can support a sequential ordinary/SNP guest pair for
small-genome experiments. Capacity and placement must be checked immediately
before launch; reserve memory for other workloads. It must not disturb the existing VMs. Whether the KVM
vPMU works inside an SNP guest on this kernel is not established and would have to be tried.
Needs explicit authorization to define and start guests on this machine.

## 3. What to sample (both sides identical)

1. **Phase times**: STAR's own `Log.progress.out` and `Log.final.out` timestamps (genome load,
   mapping, sorting/output), plus wall time of `genomeGenerate`.
2. **Process totals**: `/usr/bin/time -v` (elapsed, user/system time, max RSS, minor/major page
   faults, voluntary/involuntary context switches, file system inputs/outputs).
3. **System time series at 1 s**: `vmstat`, `mpstat -P ALL`, `iostat -x`, `pidstat -u -r -d -w`.
4. **Counter deltas**: `/proc/vmstat` (pgfault, pgmajfault, thp_*), `/proc/meminfo`
   (`Unaccepted` in a CVM, if the kernel reports it), `/proc/interrupts`.
5. **Software profiling as root in the guest**: `perf stat -e task-clock,page-faults,context-switches,cpu-migrations`;
   `perf record -e cpu-clock -g` (needs a separately recorded frame-pointer build); `perf trace -s` for
   system call summaries.
6. **Hardware counters**: only where a PMU exists (not on N2D); reported separately from software
   sampling and never mixed into one table.
7. **Environment capture**: `collect-env.sh` at the start of every session on every machine.

## 4. Hypotheses to test (not assumed to be the bottleneck)

| # | Hypothesis | Measurement that would show it |
|---|---|---|
| H1 | First touch of the large genome index costs more in a CVM (page validation/acceptance) | genome load time cold vs warm; with and without prefaulting (`--genomeLoad` modes, `MAP_POPULATE`-style preload); minor faults per second |
| H2 | Disk and network I/O cost more through bounce buffers | inputs from tmpfs vs disk; output to tmpfs vs disk; `iostat` throughput; system time share |
| H3 | VM exits and interrupts grow with threads | scaling 1, 2, 4, 8 threads; system time, context switches, interrupts per second |
| H4 | NUMA and vCPU topology differ | `lscpu`/`numactl` in both guests; pinned vs unpinned runs |
| H0 | No measurable difference beyond noise | the repetitions' spread |

## 5. What I need to proceed

- A choice of option A, B or both, and authorization for the resources (project, zone, budget,
  maximum hours, and that I may create and delete the two `bio-star-*` instances). For option B,
  authorization to define and start local guests, with a memory cap.
- The pinned STAR build (with a frame-pointer variant) and the dataset sizes, to
  settle disk and memory per VM.

## Interpretation and documentation

Page faults, context switches and elapsed time are indirect evidence. They do not
measure host VM exits or prove a page-acceptance/bounce-buffer mechanism. Use
controlled interventions and available stack samples to distinguish causes.

The following provider documentation was consulted on 2026-10-25; recheck at
provisioning because availability and prices can change:

- [Confidential VM supported configurations](https://docs.cloud.google.com/confidential-computing/confidential-vm/docs/supported-configurations)
- [Compute Engine PMU](https://docs.cloud.google.com/compute/docs/pmu-overview)
- [Instance create CLI](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create)

The initial allocation, image compatibility and cost ceiling are still undecided.
The script defaults to printing mutations; running it is not an authorization.
