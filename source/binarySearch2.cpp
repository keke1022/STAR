#include "binarySearch2.h"

int binarySearch2(uint x, uint y, uint *X, uint *Y, int N) {
    // Binary search in the lexicographically sorted (X,Y) junction list.
    // The producers of these arrays sort by X and then Y and collapse duplicate
    // pairs.  Searching the pair directly avoids a linear scan over all entries
    // that share X.
    if (N==0 || x>X[N-1] || x<X[0]) return -1;

    int i1=0, i2=N;
    while (i1<i2) {
        int i3=i1+(i2-i1)/2;
        if (X[i3]<x || (X[i3]==x && Y[i3]<y)) {
            i1=i3+1;
        } else {
            i2=i3;
        };
    };

    if (i1<N && X[i1]==x && Y[i1]==y) return i1;

    // Preserve the original implementation's observable sentinel behavior: a
    // missing Y returns -2 only when the matching X run reaches the end of the
    // array; otherwise the forward scan encounters the next X and returns -1.
    return x==X[N-1] ? -2 : -1;
};
