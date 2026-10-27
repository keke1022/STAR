#ifndef PROOF_MAX_N
#define PROOF_MAX_N 8
#endif

// Include the production implementation itself, not a hand-written model.  The
// include guard suppresses STAR's large common header so CBMC only has to parse
// this isolated function.
#define HDEF_binarySearch2
#define uint unsigned long long
#define binarySearch2 binarySearch2_candidate
#include "../../../../source/binarySearch2.cpp"
#undef binarySearch2

// Include the byte-for-byte fb477c5 source snapshot as the reference.
#define binarySearch2 binarySearch2_reference
#include "reference.cpp"
#undef binarySearch2

extern unsigned long long nondet_ulong_long();
extern int nondet_int();

int main() {
    uint X[PROOF_MAX_N];
    uint Y[PROOF_MAX_N];
    uint X_before[PROOF_MAX_N];
    uint Y_before[PROOF_MAX_N];

    int N=nondet_int();
    __CPROVER_assume(N>=0 && N<=PROOF_MAX_N);

    for (int i=0;i<PROOF_MAX_N;i++) {
        X[i]=nondet_ulong_long();
        Y[i]=nondet_ulong_long();
        X_before[i]=X[i];
        Y_before[i]=Y[i];
    }

    // STAR's junction producers sort by X then Y and collapse duplicate pairs.
    // This strict lexicographic order is the compositional precondition.
    for (int i=1;i<N;i++) {
        __CPROVER_assume(X[i-1]<X[i] ||
                         (X[i-1]==X[i] && Y[i-1]<Y[i]));
    }

    uint x=nondet_ulong_long();
    uint y=nondet_ulong_long();
    int expected=binarySearch2_reference(x,y,X,Y,N);
    int actual=binarySearch2_candidate(x,y,X,Y,N);

#ifdef BINARY_SEARCH2_MUTANT
    // Deliberately wrong: erase the old API's -2 distinction.  The proof script
    // requires CBMC to find a counterexample for this build.
    if (actual==-2) actual=-1;
#endif

    __CPROVER_assert(actual==expected,
                     "candidate preserves binarySearch2 return value");
    for (int i=0;i<PROOF_MAX_N;i++) {
        __CPROVER_assert(X[i]==X_before[i] && Y[i]==Y_before[i],
                         "binarySearch2 does not mutate its input arrays");
    }
    return 0;
}

#undef uint
