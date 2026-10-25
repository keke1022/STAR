# STAR on ordinary and confidential VMs

This experiment measures STAR on matched ordinary and confidential VMs, then
tests optimizations without changing alignment results. This directory is an
experiment harness, not a modified STAR aligner. No VM/CVM speedup is established yet.

The first VM/CVM experiment now uses a **local sequential VM/SNP pair** with the
prepared Drosophila input. See [the local runbook](docs/LOCAL-PAIR.md) for guest
evidence, host observations, exact run commands and batch comparison. Cloud
configuration below remains an optional later plan.

## Run a local alignment smoke test

Requires Linux, Python 3, GNU `time`, `sort`, and an independently built STAR binary
with its matching index. Gzip input additionally requires `zcat`.

1. Copy `examples/workload.json` to an untracked `local.workload.json` and fill in
   the binary, index, reads, upstream revision, compiler flags, and input provenance.
2. Run:

```sh
python3 tools/star_bench.py run --config local.workload.json \
  --environment native-smoke --threads 1 --warmups 1 --repetitions 5 \
  --out runs/smoke-1t
python3 -m unittest discover -s tests -v
```

The runner records binary/index/read hashes, complete arguments, process wall
time, GNU time resource metrics, STAR logs, and alignment signatures. It rejects
failed processes, missing results, and divergent repeated outputs. Each output
directory must be new. Environment names are **declared labels, not attestation**.

Input hashing and correctness checking are outside the timed region but affect
filesystem caches. These runs have uncontrolled cache state after fingerprinting;
they are **not cold-cache experiments**. Each timed alignment is a new process
with a private index copy; a warm filesystem cache is not an in-process warm index.
This initial runner measures alignment plus index loading and SAM output. It does
not measure index generation or sorted BAM production; those are separate workloads.

To compare outputs across builds/environments (the final numbered directory is
printed in `runs.json`):

```sh
python3 tools/star_bench.py compare runs/vm/run/001 runs/snp/run/001
```

Comparison preserves all alignment columns, optional tags, and record
multiplicity while ignoring row/tag order, `@PG` and STAR's `@CO` command metadata. It also
compares other SAM headers (ignoring declared sort order), STAR non-timing summary
fields, splice-junction records, and gene-count output when present. It exits 1 on
differences or malformed/missing output. Equality is a strong regression check,
not a formal equivalence proof or a biological accuracy assessment. BAM/CRAM,
STARsolo matrices and chimeric outputs need additional validation before use.

Raw runs contain local filesystem paths. Do not commit runs, downloaded data,
machine inventories, credentials, or agent transcripts. Commit curated result
summaries and reproducible acquisition/build scripts instead.

See [the experiment protocol](docs/PROTOCOL.md) for fairness and interpretation.

## Build and obtain the flow-test data

The checked smoke input is Ensembl GRCh38 chromosome 21 with the first 10,000
paired records from ENA SRR1039508. Most reads cannot map to this partial reference;
this validates the workflow only. Run from this directory, creating fresh output
directories (parent directories must exist):

```sh
mkdir -p vendor inputs runs
scripts/build_star.sh vendor 4
scripts/fetch_inputs.sh inputs/chr21-10k 10000
scripts/genome_generate.sh vendor/STAR-2.7.11b/source/STAR \
  inputs/chr21-10k/chr21.fa inputs/chr21-10k/chr21.gtf runs/genome-chr21 4 11 62
```

Fill `local.workload.json` with these paths and use the runner above. Reference
acquisition downloads the full Ensembl chromosome GTF archive before extracting
chr21. See [input identities](docs/INPUTS.md), [prior work](docs/RELATED-WORK.md),
[dataset progression](docs/DATASET-PLAN.md), [environment plan](docs/ENVIRONMENT.md),
and [cost proposal](docs/COSTS.md). Read the RAM/storage requirements
before using larger inputs.

## Environment and cloud plan

`tools/collect-env.sh env-local` probes software sampling and hardware counters
separately, writes local reports, and changes no system settings. Raw reports can
contain machine metadata; do not commit them. Successful detection is not remote
attestation. Both ordinary and confidential guests require actual checks.

The GCP script is a resource draft. It has **not** been run against live cloud
resources. Obtain a working login and agree the project and budget before
execution. Without `--execute`, create/cleanup print commands only:

```sh
PROJECT=YOUR_PROJECT tools/gcp-plan-a.sh preflight
PROJECT=YOUR_PROJECT RUN_ID=YOUR_RUN IMAGE=EXACT_IMAGE tools/gcp-plan-a.sh create
PROJECT=YOUR_PROJECT RUN_ID=YOUR_RUN tools/gcp-plan-a.sh cleanup
PROJECT=YOUR_PROJECT RUN_ID=YOUR_RUN tools/gcp-plan-a.sh verify-clean
```

`preflight` reads image and machine metadata. `verify-clean` reads the exact pair's
instance and disk names and fails if any remain. Reuse the same project, zone and
run ID for cleanup. Creation rejects collisions; deletion checks both instance
labels first and never deletes detached disks automatically. If creation partly
fails, inspect and clean the partial pair. NVMe support on the ordinary guest and
lifetime deletion compatibility still need provider validation. A successful
preflight alone does not establish a deployable or matched pair.

The first real-input integration result is in [the native smoke report](results/NATIVE-SMOKE.md).

## Complete-reference Drosophila pilot

```sh
scripts/fetch_dm.sh inputs/dm-100k 100000
scripts/genome_generate.sh vendor/STAR-2.7.11b/source/STAR \
  inputs/dm-100k/dm.fa inputs/dm-100k/dm.gtf runs/genome-dm 4 12 100
```

Use the generated index and `DRR129224_100000_{1,2}.fastq` in a separate local
runner configuration. The fixed sample's high mapping fraction is useful for
validation but is not a statement about other samples or human workloads.

[Complete-reference pilot results](results/DROSOPHILA-PILOT.md) include independent output checks.
