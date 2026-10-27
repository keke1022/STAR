#ifndef HDEF_medianUint2
#define HDEF_medianUint2

inline uint medianUint2(uint a, uint b)
{
    // Overflow-safe floor((a+b)/2).  Shared bits contribute directly; differing
    // bits can be halved without a carry between the two terms.
    return (a & b) + ((a ^ b) >> 1);
};

#endif
