#define uint unsigned long long
#define medianUint2 medianUint2_candidate
#include "../../../../source/medianUint2.h"
#undef medianUint2

extern unsigned long long nondet_ulong_long();

static uint medianUint2_reference(uint a, uint b) {
    return a/2 + b/2 + (a%2 + b%2)/2;
}

int main() {
    uint a=nondet_ulong_long();
    uint b=nondet_ulong_long();
    uint expected=medianUint2_reference(a,b);
    uint actual=medianUint2_candidate(a,b);
#ifdef MEDIAN_UINT2_MUTANT
    // Deliberately wrong for inputs with two odd low bits.
    actual=(a & b) + ((a ^ b) >> 1) - ((a & b) & 1);
#endif
    __CPROVER_assert(actual==expected,
                     "candidate preserves medianUint2 for all uint values");
    return 0;
}

#undef uint
