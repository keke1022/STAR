# Prior work and what this experiment must add

STAR already implements parallel alignment and supports compilation and index
tradeoffs. Starting from an old repository is not sufficient motivation for an
optimization. Pin the actual upstream release and show a measured bottleneck.
[STAR source](https://github.com/alexdobin/STAR/tree/2.7.11b)

- [Optimizing STAR Aligner for High Throughput Computing in the Cloud (2024)](https://arxiv.org/abs/2409.05886)
  directly studies STAR cloud throughput and resource selection. Its use of early
  stopping needs separate treatment: reducing the amount of processed data is not
  an equivalent-output acceleration of a fixed alignment job.
- [Evaluating Trusted Execution Environment Performance for Genome Sequence Alignment:
  An AMD SEV Case Study (SC25 workshop)](https://sc25.conference-program.com/presentation/?id=ws_shpc104&sess=sess230)
  studies BWA-MEM2 with AMD memory-encryption configurations. It is relevant to
  experiment design but does not establish STAR performance on SEV-SNP.
- [A comprehensive performance evaluation of TEEs for confidential DNA alignment](https://www.sciencedirect.com/science/article/pii/S0167739X25003267)
  evaluates confidential DNA alignment across SGX, TDX and SNP. Only the abstract
  has been inspected for this initial survey; specific workload coverage and
  detailed methods need checking before making a novelty claim.

A useful result here would quantify an attributable STAR overhead, explain it
with available measurements and controlled interventions, then preserve results
while reducing execution cost. Merely running a bioinformatics aligner in a CVM
is already represented in prior work. RNA-seq splice-aware mapping also differs
from DNA alignment, so costs cannot be transferred without measurement.
