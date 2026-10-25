# Workload progression

The checked chr21/10k-pair smoke input is documented in INPUTS.md. Larger chr21
runs are not needed for representative performance conclusions. An interrupted
1M-pair local attempt and overlapping runs were excluded, not treated as data.

The complete-reference local pilot is now prepared and independently rerun:
Drosophila melanogaster BDGP6.54 toplevel plus matching annotation, with the first
100,000 paired records from ENA DRR129224. Exact sources and hashes are in INPUTS.md.
Paired FASTQ validation and four reference/annotation hashes were independently
checked. Index construction used about 5.28 GiB peak RSS in the preparation worker's
run (not independently rebuilt); the earlier 2–4 GiB planning estimate was low.
Index disk usage was reported as about 1.9 GiB. Read the actual run and available
memory before sizing guests. See results/DROSOPHILA-PILOT.md for scope and results.

A complete small genome is useful for iteration, but this tiny prefix of one RNA-seq
sample does not establish human workload or scaling performance.

The proposed larger workload is Ensembl 116 GRCh38 primary assembly with its
matching GTF, then either SRR1039508 (paired 63 bp, continuity with the smoke
sample) or DRR231146 (paired 150 bp). Full input acquisition and index building
have not been performed. Plan around a roughly 30 GiB human index and substantial
extra RAM/output space; the proposed 64 GiB guests and 300 GiB disks leave room
for this to be checked. Store one canonical binary and alignment index on both
machines; measure index generation separately if comparing that phase.

Primary read metadata: [DRR129224](https://www.ebi.ac.uk/ena/browser/view/DRR129224),
[SRR1039508](https://www.ebi.ac.uk/ena/browser/view/SRR1039508),
[DRR231146](https://www.ebi.ac.uk/ena/browser/view/DRR231146).
These are candidate datasets, not claims of benchmark representativeness.
