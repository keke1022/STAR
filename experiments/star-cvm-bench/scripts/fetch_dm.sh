#!/usr/bin/env bash
# Fetch the Drosophila pilot inputs.
# Reference: Ensembl release 116, D. melanogaster BDGP6.54 toplevel + matching GTF (genome-build BDGP6.54).
# Reads: ENA DRR129224 (polyA RNA-seq, Illumina HiSeq 4000, paired-end 2x101, 28.0M pairs);
# only the first N pairs are streamed (full run ~2.3 GB gz is not downloaded).
# Usage: fetch_dm.sh OUTDIR [NPAIRS]   (default 100000)
set -euo pipefail
VALIDATOR=$(cd "$(dirname "$0")/../tools" && pwd)/validate_fastq.py
OUT=${1:?outdir}; N=${2:-100000}
[[ "$N" =~ ^[1-9][0-9]*$ ]] || { echo "NPAIRS must be a positive integer" >&2; exit 2; }
mkdir "$OUT"
cd "$OUT"
B=https://ftp.ensembl.org/pub/release-116
curl -sSfL -o dm.fa.gz "$B/fasta/drosophila_melanogaster/dna/Drosophila_melanogaster.BDGP6.54.dna.toplevel.fa.gz"
curl -sSfL -o dm.gtf.gz "$B/gtf/drosophila_melanogaster/Drosophila_melanogaster.BDGP6.54.63.gtf.gz"
curl -sSfL -o fasta.CHECKSUMS "$B/fasta/drosophila_melanogaster/dna/CHECKSUMS"
curl -sSfL -o gtf.CHECKSUMS "$B/gtf/drosophila_melanogaster/CHECKSUMS"
gzip -dc dm.fa.gz > dm.fa
gzip -dc dm.gtf.gz > dm.gtf
ENA=https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR129/DRR129224
L=$((N*4))
for m in 1 2; do
  set +o pipefail
  curl -sSfL "$ENA/DRR129224_$m.fastq.gz" | gzip -dc | head -n "$L" > "DRR129224_${N}_$m.fastq"
  set -o pipefail
  test "$(wc -l < DRR129224_${N}_$m.fastq)" -eq "$L"
done
python3 "$VALIDATOR" "DRR129224_${N}_1.fastq" "DRR129224_${N}_2.fastq" --pairs "$N" > pairing.json
sha256sum dm.fa.gz dm.fa dm.gtf.gz dm.gtf DRR129224_${N}_1.fastq DRR129224_${N}_2.fastq > SHA256SUMS
grep 'toplevel\.fa\.gz' fasta.CHECKSUMS | grep -v -E '_rm|_sm' > ensembl.fa.sum; sum dm.fa.gz > local.fa.sum
grep 'BDGP6\.54\.63\.gtf\.gz' gtf.CHECKSUMS > ensembl.gtf.sum; sum dm.gtf.gz > local.gtf.sum

for key in fa gtf; do
  read -r a b _ < "ensembl.$key.sum"
  read -r c d _ < "local.$key.sum"
  test "$a $b" = "$c $d" || { echo "Ensembl $key checksum mismatch" >&2; exit 1; }
done
