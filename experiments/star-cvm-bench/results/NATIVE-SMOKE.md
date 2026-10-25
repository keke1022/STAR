# Native workflow smoke, 2026-10-25

The integrated runner completed four actual STAR alignments: 1 and 4 threads,
two repetitions per setting, no warm-up. Each processed the first 10,000 paired
records of ENA SRR1039508 against the Ensembl 116 GRCh38 chr21 index. All four
outputs had identical canonical SAM contents (20,478 records including unmapped
mates), retained headers, non-timing statistics, and splice-junction output.
The binary and both input-read SHA-256 values matched the supplied manifest.

This is **not a VM/CVM experiment or a scaling result**. The shared native host
had another alignment in progress. Cache state was uncontrolled after input
fingerprinting; the reference covers only one chromosome. STAR classified
95.34% of the pairs as unmapped because the matched portion was too short.
The two elapsed-time samples were 31.868/31.816 seconds at 1 thread and
32.520/32.416 seconds at 4 threads. These validate collection only, and must not
be used to infer thread efficiency or confidential-computing overhead.

See [machine-readable results](native-smoke-20261025.json) for fingerprints,
resource totals, samples and comparison signatures. No raw machine inventory,
filesystem paths, reads, alignments or agent transcripts are committed.

The integration corrected two comparison details found by inspecting STAR's
actual output code: `@CO` command-line metadata changes with output paths, and
`Started job on`, `Started mapping on`, `Finished on` are timestamps despite
not containing the word "time". Regression tests vary these fields independently
while retaining alignment and biological summary comparisons.

Validation: 12 Python tests passed, covering timing/result failures, altered
alignments and labels/leftovers in the cloud-plan helper; shell syntax checks
passed. The build/data preparation worker ran the original acquisition and
build scripts. This integration reused that binary/index/input; it did not
repeat the full download or build, or test real cloud creation/deletion.
