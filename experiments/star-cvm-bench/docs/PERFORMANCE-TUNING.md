# STAR profiling and tuned-build protocol

The Drosophila 100k-pair workload exposed two independent optimization levers.
They are general STAR optimizations, not SEV-SNP-specific changes.

## Input chunk balance

STAR divides the first value of `--limitIObufferSize` among input mates. With
the 30,000,000-byte default and two 26,420,188-byte FASTQ files, this workload
forms only two chunks. A four-thread run therefore leaves two mapping threads
idle. The tested setting is:

```sh
--limitIObufferSize 4000000 50000000
```

It forms 13 chunks for this input and distributes reads across all four
threads. This value is workload-specific: sweep it again when read count,
compression, mate count or thread count changes. Preserve STAR's output buffer
value unless a separate experiment justifies changing it.

This tuning is not universally result-preserving. STAR's random multimapper
mode uses per-thread random state, so changing chunk assignment can change a
read's primary alignment. Keep `outMultimapperOrder=Old_2.4` for this validated
profile. Treat `Random`, transcriptome/BAM modes, and other untested output
modes as unsupported until they have their own differential tests.

## CPU-tuned build

`scripts/build_star_native_lto.sh` builds pinned STAR 2.7.11b with
`-march=native -flto`. The binary is intentionally host-specific. Record the
compiler, resolved native target, binary hash and complete flags, and use the
exact same binary in the ordinary and confidential guests.

This build is an experimental candidate, not a blanket equivalence claim.
Compiler and link-time optimization can change behavior in edge cases even
when a fixed corpus is unchanged. Do not promote it for functionality-critical
use until the declared workload and parameter domain pass raw-output
differential testing; keep the upstream binary available as the fallback.

## Validation

Run upstream and optimized batches separately with tracing disabled. Give the
optimized batch an honest label such as `znver5-lto-balanced-io` rather than
`upstream`. Compare VM/SNP batches with `compare_batches.py --variant LABEL`.
Compare builds within an environment with `compare_variants.py`, explicitly
allowing only the changed binary, build flags and STAR arguments. Both tools
recompute signatures from raw outputs.

For SAM, validation follows `outSAMorder`: `Paired` requires every QNAME to be
one contiguous group and each multimapping mate unit to remain adjacent with
complementary first/second flags and matching `HI`; `PairedKeepInputOrder` also
preserves QNAME-group and within-group order. `Standard` is compared as an
unordered record multiset. The checker still establishes equality only for the
outputs it understands; it is not a proof over every STAR mode or every input.

Report these separately:

1. absolute upstream and optimized times in each environment;
2. optimization benefit within VM and within SNP;
3. SNP-over-VM ratio before and after optimization.

Do not describe a general optimization as an SNP optimization. First-touch
memory acceptance and tmpfs checks are correlation controls; their preprocessing
cost belongs in end-to-end accounting, and neither alone identifies a cause.
