#!/usr/bin/env bash
# Build STAR 2.7.11b from source with upstream's default flags.
# Usage: build_star.sh WORKDIR [JOBS]   -> WORKDIR/STAR-2.7.11b/source/STAR
set -euo pipefail
W=${1:?workdir}; J=${2:-4}
TAG=2.7.11b; COMMIT=b1edc1208d91a53bf40ebae8669f71d50b994851
mkdir -p "$W"; cd "$W"
[ -d STAR-$TAG ] || git clone -q --depth 1 --branch "$TAG" https://github.com/alexdobin/STAR.git STAR-$TAG
test "$(git -C STAR-$TAG rev-parse HEAD)" = "$COMMIT"
# Reject local source edits; mixing them with a release identifier is misleading.
test -z "$(git -C STAR-$TAG status --porcelain --untracked-files=no)"
cd STAR-$TAG/source
# upstream Makefile defaults: -O3 -std=c++11 -fopenmp -mavx2 -pipe -Wall -Wextra, bundled htslib
make -j"$J" STAR
./STAR --version
sha256sum STAR
