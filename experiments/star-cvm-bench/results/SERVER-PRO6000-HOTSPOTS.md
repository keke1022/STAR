# server-pro6000 STAR hotspot and optimization result

Status: fixed-workload result complete; larger-corpus functionality validation
in progress. The CPU-tuned build remains an experimental candidate.

## What was slow

Source phase timing and `perf` sampling agree that the alignment loop dominates.
The largest sampled symbols were `stitchWindowAligns` (about 35–42%),
`stitchAlignToTranscript` (15–16%), `compareSeqToGenome` (about 13%) and
`extendAlign` (7–8%). Index loading was about 0.6 seconds after the first run.
The timed `ostream::write` calls for SAM data were only milliseconds; this is
not a persistence/fsync measurement and does not include all formatting work.

The 100,000-pair input also exposed a workload-size-specific parallelism issue.
With the default 30,000,000-byte input buffer, the two 26,420,188-byte FASTQ
files formed two chunks: 64,039 and 35,961 read pairs. A four-thread run thus
left two mapping threads idle. `--limitIObufferSize 4000000 50000000` formed 13
chunks and distributed about 24.4k, 24.5k, 24.4k and 26.6k pairs across the four
threads. It also reduced aggregate four-thread input-buffer initialization from
120 MB to 16 MB. Both effects contribute to the observed result.

## Formal comparison

The run order was VM1 → SNP1 → SNP2 → VM2. The first two windows used forward
variant/thread order and the last two reversed it. Every batch used one warm-up
and five timed repetitions with tracing disabled. Totals are 24 batches, 144
STAR executions, 120 timed samples and 24 warm-ups.

Pooled medians across the two windows for each environment:

| Environment | Variant | 1 thread | 4 threads |
|---|---|---:|---:|
| VM | upstream | 11.032 s | 7.276 s |
| VM | balanced input | 10.957 s | 3.521 s |
| VM | znver5/LTO + balanced input | 8.878 s | 2.970 s |
| SNP | upstream | 11.489 s | 7.530 s |
| SNP | balanced input | 11.489 s | 3.621 s |
| SNP | znver5/LTO + balanced input | 9.410 s | 3.071 s |

The balanced-input change was neutral at one thread (-0.7% VM, 0.0% SNP) and
reduced four-thread time by 51.6% in VM and 51.9% in SNP. The CPU-tuned build
then reduced time relative to balanced input by 19.0%/15.7% in VM (1t/4t) and
18.1%/15.2% in SNP. Combined four-thread reduction was 59.2% in both.

These are general STAR improvements. They did not remove the confidential-VM
difference: SNP over VM was +4.1%/+3.5% upstream, +4.9%/+2.8% with balanced
input, and +6.0%/+3.4% with both changes (1t/4t). The changes in these ratios do
not by themselves identify an SNP-specific mechanism.

## Functionality gate

All 144 raw SAM outputs were re-read after the formal run. For the recorded
default `outSAMorder=Paired`, the strict checker verifies all alignment fields,
optional tags and multiplicity; nonvolatile SAM headers; STAR non-timing
statistics; splice-junction output; contiguous QNAME groups; and adjacent mate
units with complementary first/second flags and matching `HI` tags. All outputs
matched. The checker also rejects injected split-QNAME, interleaved-multimapper,
changed-FLAG and `PairedKeepInputOrder` ordering negatives. Twenty-eight unit
tests pass.

This is not a universal equivalence proof. An independent counterexample showed
that `outMultimapperOrder=Random` can change primary alignments when chunk/thread
assignment changes; that mode is excluded. Other output modes remain unvalidated.
The `znver5`/LTO binary is therefore an experimental candidate until the full
DRR129224 corpus and the declared parameter domain pass the same raw-output
differential gate. The upstream binary remains the fallback.

## Reproducibility and environment

- Upstream binary SHA-256: `61227ee7797cdcbf52afc6856d17b5659173ef5ba66687f7b4f0a014db7bb1ff`.
- CPU-tuned binary SHA-256: `c24f8afc5ee6f629e3424237078f8fa248b01a7c20c189228befd59175a3f97c`.
- Source: STAR 2.7.11b commit `b1edc1208d91a53bf40ebae8669f71d50b994851`.
- Tuned build: GCC 15.2.0, resolved native target `znver5`,
  `CXXFLAGSextra=-march=native -flto`, `LDFLAGSextra=-flto`.
- Both SNP boots used distinct nonces. Their version-5, policy `0x30000` reports
  passed the AMD Turin ARK → ASK → VCEK → report chain, nonce matching and the
  expected measurement check.
- All guests were run serially with the same 8-vCPU/10-GiB pinning. All are shut
  off after the experiment. No timed sample swapped; VM2's first upstream 1t
  sample observed two guest major faults, which did not determine the median.
- SNP `Unaccepted` memory fell from 3.65 GiB to 0.59 GiB in SNP1 and from
  3.90 GiB to 0.88 GiB in SNP2. The result is therefore not a pure
  already-accepted-memory steady state.

See `docs/PERFORMANCE-TUNING.md` for the exact optimization and validation
contract. Large raw outputs and machine inventories are intentionally not
committed.
