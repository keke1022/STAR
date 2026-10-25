#!/usr/bin/env bash
# Fetch the small flow-test inputs for the STAR baseline.
# Reference: Ensembl release 116, GRCh38, chromosome 21 only.
# Reads: ENA SRR1039508 (airway, Illumina HiSeq 2000, paired-end); only the first N pairs,
# streamed (the full run is ~2.5 GB compressed and is not downloaded).
# Usage: fetch_inputs.sh OUTDIR [NPAIRS]   (default NPAIRS=1000000)
set -euo pipefail
OUT=${1:?outdir}; N=${2:-1000000}
[[ "$N" =~ ^[1-9][0-9]*$ ]] || { echo "NPAIRS must be a positive integer" >&2; exit 2; }
mkdir "$OUT"  # refuse to overwrite previous inputs
cd "$OUT"
REL=116
BASE=https://ftp.ensembl.org/pub/release-$REL
curl -sSfL -o chr21.fa.gz "$BASE/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.chromosome.21.fa.gz"
curl -sSfL -o ensembl.CHECKSUMS "$BASE/fasta/homo_sapiens/dna/CHECKSUMS"
curl -sSfL -o full.chr.gtf.gz "$BASE/gtf/homo_sapiens/Homo_sapiens.GRCh38.$REL.chr.gtf.gz"
gzip -dc chr21.fa.gz > chr21.fa
# chromosome 21 rows only (Ensembl names it "21"), header lines kept
gzip -dc full.chr.gtf.gz | awk -F'\t' '/^#/ || $1=="21"' > chr21.gtf
ENA=https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR103/008/SRR1039508
L=$((N*4))
for m in 1 2; do
  # stream, keep the first N records; set +o pipefail because head closes the pipe early
  set +o pipefail
  curl -sSfL "$ENA/SRR1039508_$m.fastq.gz" | gzip -dc | head -n "$L" > "SRR1039508_${N}_$m.fastq"
  set -o pipefail
  test "$(wc -l < SRR1039508_${N}_$m.fastq)" -eq "$L"
done
sha256sum chr21.fa.gz chr21.fa full.chr.gtf.gz chr21.gtf SRR1039508_${N}_1.fastq SRR1039508_${N}_2.fastq > SHA256SUMS
# Ensembl's own BSD-style checksum for the FASTA, to compare with `sum`
grep 'chromosome\.21\.fa\.gz' ensembl.CHECKSUMS > ensembl.chr21.sum
sum chr21.fa.gz > local.chr21.sum

python3 - <<'CHECK_FASTQ'
from pathlib import Path
files = sorted(Path('.').glob('SRR1039508_*_?.fastq'))
if len(files) != 2:
    raise SystemExit('Expected exactly two FASTQ mates')
with files[0].open() as a, files[1].open() as b:
    while True:
        ra, rb = [a.readline() for _ in range(4)], [b.readline() for _ in range(4)]
        if not ra[0] and not rb[0]:
            break
        for record in (ra, rb):
            if not record[0].startswith('@') or not record[2].startswith('+') or len(record[1].strip()) != len(record[3].strip()):
                raise SystemExit('Malformed FASTQ record')
        # ENA mate suffixes may be /1 and /2; names before them must agree.
        names = [r[0].split()[0].removesuffix('/1').removesuffix('/2') for r in (ra, rb)]
        if names[0] != names[1]:
            raise SystemExit('Paired FASTQ names differ')
CHECK_FASTQ
read -r a b _ < ensembl.chr21.sum
read -r c d _ < local.chr21.sum
test "$a $b" = "$c $d" || { echo "Ensembl FASTA checksum mismatch" >&2; exit 1; }
