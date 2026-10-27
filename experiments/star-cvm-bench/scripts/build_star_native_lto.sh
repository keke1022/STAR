#!/usr/bin/env bash
# Build the pinned STAR release for the current CPU with link-time optimization.
# Usage: build_star_native_lto.sh WORKDIR [JOBS]
# Output: WORKDIR/STAR-2.7.11b-native-lto/source/STAR plus build-evidence.txt
set -euo pipefail

W=${1:?workdir}
J=${2:-4}
TAG=2.7.11b
COMMIT=b1edc1208d91a53bf40ebae8669f71d50b994851
TREE="$W/STAR-$TAG-native-lto"

mkdir -p "$W"
if [ ! -d "$TREE" ]; then
    git clone -q --depth 1 --branch "$TAG" https://github.com/alexdobin/STAR.git "$TREE"
fi
test "$(git -C "$TREE" rev-parse HEAD)" = "$COMMIT"
test -z "$(git -C "$TREE" status --porcelain --untracked-files=no)"

cd "$TREE/source"
make -j"$J" STAR CXXFLAGSextra="-march=native -flto" LDFLAGSextra="-flto"
{
    printf 'source_commit=%s\n' "$COMMIT"
    printf 'make_CXXFLAGSextra=%s\n' '-march=native -flto'
    printf 'make_LDFLAGSextra=%s\n' '-flto'
    g++ --version | sed -n '1p'
    printf 'compiler_native_target='; g++ -march=native -Q --help=target -c -x c++ /dev/null 2>/dev/null \
        | awk '$1 == "-march=" && !seen {print $2; seen=1}'
    ./STAR --version
    sha256sum STAR
} | tee "$W/build-evidence.txt"
