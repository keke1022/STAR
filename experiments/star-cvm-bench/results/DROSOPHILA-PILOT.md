# Complete-reference Drosophila pilot, 2026-10-25

The unified runner independently completed four native STAR alignments against
the complete BDGP6.54 reference: 1 and 4 threads, two runs per setting, 100,000
paired records from DRR129224. Canonical SAM contents, retained headers, STAR
non-timing statistics and SJ output agreed across all four runs. Reference and
annotation hashes, their build header, binary/read hashes and all paired FASTQ
names and lengths were checked. This reuses the preparation worker's index;
index generation was not independently rerun.

| Setting | Elapsed seconds, both samples | Peak RSS range (KiB) |
|---|---|---|
| 1 thread | 13.407, 13.708 | 2,122,844–2,122,896 |
| 4 threads | 9.543, 9.192 | 2,434,200–2,436,240 |

For this particular sample, unique mapping was 91.70%, multimapping 2.95%, and
unmapped-too-short 4.66%. The runner writes unmapped reads inside SAM, producing
220,318 records. The preparation worker used STAR's default unmapped-output
setting and observed 209,618 records; those different configurations are not
compared as equivalent-output timing samples. STAR's total splice count is
26,246; SJ.out.tab has 10,290 rows. These are distinct quantities.

The preparation worker's index-generation log records 101.18 seconds with four
threads and 5,536,540 KiB peak RSS (about 5.28 GiB). This exceeds the initial
2–4 GiB estimate. That log was inspected, not independently reproduced.

This is a workflow and output-consistency pilot on a shared native host. Runs
were sequential; cache state was uncontrolled after hashing, with no warm-up
and only two samples per setting. It does not establish thread scaling,
biological accuracy, a bottleneck, VM/CVM overhead or an optimization benefit.
Formal timing experiments still require the matched guest pair, representative
input sizes, controlled conditions and at least five timed repetitions.

[Curated samples, fingerprints and signatures](drosophila-pilot-20261025.json)
contain no raw data or machine filesystem paths. The input scripts now validate
paired FASTQ structure/count and fail on provider-reference checksum mismatches.
Fourteen Python tests and shell syntax checks passed. Acquisition/build scripts
were prepared and run by the data worker; the integrated versions were reviewed
and syntax-checked, not used for a fresh full download/build.
