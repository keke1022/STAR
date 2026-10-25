# Workload progression

The checked chr21/10k-pair smoke input is documented in INPUTS.md. Larger chr21
runs are not needed for representative performance conclusions. An interrupted
1M-pair local attempt and overlapping runs were excluded, not treated as data.

Next local pilot: a complete Drosophila melanogaster BDGP6.54 reference with its
matching annotation, and the first 100,000 paired records from ENA DRR129224.
Preparation is in progress. Reference/annotation release consistency, exact
source URLs and hashes, paired names, read lengths and mapping rates must be
checked before measurement. Estimated index RAM is 2–4 GiB and disk 1–2 GiB;
these are planning estimates, not measured bounds. A complete small genome is
more suitable for iteration than human transcriptome reads against chr21, but
cannot stand in for human workloads.

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
