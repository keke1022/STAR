#!/usr/bin/env bash
# Build a STAR index. Usage: genome_generate.sh STAR FASTA GTF OUTDIR THREADS SAINDEXNBASES SJDBOVERHANG [RAMBYTES]
#   SAINDEXNBASES = min(14, log2(genome length)/2 - 1); SJDBOVERHANG = read length - 1
# chr21 flow test: 11 and 62 (63 bp reads). Drosophila BDGP6.54: 12 and 100 (101 bp reads).
set -euo pipefail
STAR=${1:?star}; FA=${2:?fasta}; GTF=${3:?gtf}; OUT=${4:?outdir}; T=${5:?threads}; SA=${6:?saindex}; OH=${7:?overhang}; RAM=${8:-8000000000}
mkdir "$OUT"  # refuse an existing index
/usr/bin/time -v -o "$OUT/time-v.txt" nice -n 10 "$STAR" --runMode genomeGenerate --runThreadN "$T" \
  --genomeDir "$OUT" --genomeFastaFiles "$FA" --sjdbGTFfile "$GTF" --sjdbOverhang "$OH" \
  --genomeSAindexNbases "$SA" --limitGenomeGenerateRAM "$RAM" --outFileNamePrefix "$OUT/" > "$OUT/stdout.txt" 2>&1
