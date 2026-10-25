#!/usr/bin/env bash
# Build the chr21 STAR index (flow test). Usage: genome_generate.sh STAR INPUTDIR OUTDIR THREADS
set -euo pipefail
STAR=${1:?star}; IN=${2:?inputs}; OUT=${3:?outdir}; T=${4:-4}
mkdir "$OUT"  # refuse an existing index directory
# genomeSAindexNbases = min(14, log2(46.7e6)/2 - 1) = 11 for chr21; sjdbOverhang = read length (63) - 1
/usr/bin/time -v -o "$OUT/time-v.txt" nice -n 10 "$STAR" --runMode genomeGenerate --runThreadN "$T" \
  --genomeDir "$OUT" --genomeFastaFiles "$IN/chr21.fa" --sjdbGTFfile "$IN/chr21.gtf" --sjdbOverhang 62 \
  --genomeSAindexNbases 11 --limitGenomeGenerateRAM 8000000000 --outFileNamePrefix "$OUT/" > "$OUT/stdout.txt" 2>&1
