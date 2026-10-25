# STAR baseline: inputs and build: pinned versions and inputs

Flow-test only. chr21 + whole-transcriptome reads leaves ~95% of reads unmapped, so the
alignment-phase profile is NOT representative of a full-genome run.

## STAR
- Upstream: https://github.com/alexdobin/STAR, release tag `2.7.11b`, commit `b1edc1208d91a53bf40ebae8669f71d50b994851` (2024-01-25).
- Build: `../scripts/build_star.sh WORKDIR` (upstream Makefile defaults: `-O3 -std=c++11 -fopenmp -mavx2`, bundled htslib).
- Reference build (this host): g++ 15.2.0 (Ubuntu 15.2.0-4ubuntu4), kernel 6.17; binary sha256
  `33ed677c8571676db92d8e51bc29a1bfa630148a387491a690062c61e8143b14`. The binary embeds the build
  time and path, so a rebuild elsewhere has a different hash; record each build hash. For VM/CVM timing, copy the same binary to both guests;
  version and output checks alone do not establish identical machine code.

## Reference (Ensembl release 116, GRCh38)
| File | Source | sha256 |
|---|---|---|
| `chr21.fa.gz` | https://ftp.ensembl.org/pub/release-116/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.chromosome.21.fa.gz | `550576cebf1e7b5c01b74e3b28469faa4f2b9067ff9fd07bed9df1c51abb51a6` (Ensembl CHECKSUMS `sum`: `54500 11512`, matches) |
| `chr21.fa` | `gzip -dc chr21.fa.gz` | `2064bcc6b46ff2d1e0369b6aa2dea105611b5cbc3284492d58dc1cc3fe1e6968` |
| `full.chr.gtf.gz` | https://ftp.ensembl.org/pub/release-116/gtf/homo_sapiens/Homo_sapiens.GRCh38.116.chr.gtf.gz | `f101fe4b1a350deaf26ab04bb565ba3e638e467fdc14c5c20b989b03edc87e05` |
| `chr21.gtf` | header lines + rows with seqname `21` | `d00c24af0dc46084d304119ac1d6cd3bc9afe586ba2414dd398a25240e12c9d8` |

## Reads (ENA SRR1039508, "airway", Illumina HiSeq 2000, paired-end, 63 bp; full run 22.9 M reads, ~2.5 GB gz)
First N records of each mate, streamed from `https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR103/008/SRR1039508/SRR1039508_{1,2}.fastq.gz`
(ENA md5 of the full files: `d57df747bc142e9850074d512ab9d6db`, `3331c6a9e0183ff9d398a3292dd45f66`).
| Set | Files | sha256 |
|---|---|---|
| 1M pairs | `SRR1039508_1000000_1.fastq` | `2d4297dca68e1f502a378e97d826c5a254eadd50a0a0fbc81970abd97a769be4` |
| | `SRR1039508_1000000_2.fastq` | `dfca37157d8bee859de6173182017cef4e4c40c19b3b388a46447ffec22415eb` |
| 10k pairs (smoke; first 40,000 lines of the 1M files) | `SRR1039508_10000_1.fastq` | `11a003a1d847cdf156e4bd2000034b55a32562f7c88d6d7e23eb7152fdea51c1` |
| | `SRR1039508_10000_2.fastq` | `96d99d1c4584eadd009cfebd303b3e41091a2b5584310a879c4e9b45581dc006` |

Fetch: `../scripts/fetch_inputs.sh OUTDIR [NPAIRS]`.

## Index and alignment
- Index: `../scripts/genome_generate.sh STAR INPUTDIR OUTDIR 4` (`--genomeSAindexNbases 11`, `--sjdbOverhang 62`, `--limitGenomeGenerateRAM 8e9`).
- Alignment and correctness: use `tools/star_bench.py` from the experiment root.
  It includes unmapped records and checks headers, alignment tags and summary counts.

The full-file ENA MD5 entries are provider metadata; they were not checked on the
streamed prefix. The SHA-256 values above identify the actual downloaded subsets.
The build and data were prepared by a separate worker; the integration smoke
report records which binary and read hashes were independently checked.
