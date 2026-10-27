#ifndef HDEF_binarySearch2
#define HDEF_binarySearch2

#include "IncludeDefine.h"

// Preconditions: N>=0; X/Y address at least N elements; the (X[i],Y[i])
// pairs are strictly increasing in lexicographic order (duplicates collapsed).
int binarySearch2(uint x, uint y, uint *X, uint *Y, int N);

#endif
