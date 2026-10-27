#include <algorithm>
#include <cassert>
#include <cstdint>
#include <random>
#include <vector>

#define HDEF_binarySearch2
#define uint unsigned long long
#define binarySearch2 binarySearch2_candidate
#include "../../../../source/binarySearch2.cpp"
#undef binarySearch2

static int binarySearch2_reference(uint x, uint y, uint *X, uint *Y, int N) {
    if (N==0 || x>X[N-1] || x<X[0]) return -1;
    int i1=0, i2=N-1, i3=N/2;
    while (i2>i1+1) {
        i3=(i1+i2)/2;
        if (X[i3]>x) i2=i3; else i1=i3;
    }
    if (x==X[i1]) i3=i1;
    else if (x==X[i2]) i3=i2;
    else return -1;
    for (int jj=i3;jj>=0;jj--) {
        if (x!=X[jj]) break;
        if (y==Y[jj]) return jj;
    }
    for (int jj=i3;jj<N;jj++) {
        if (x!=X[jj]) return -1;
        if (y==Y[jj]) return jj;
    }
    return -2;
}

int main() {
    std::mt19937_64 rng(0x53544152ULL);
    for (int trial=0;trial<20000;trial++) {
        int n=static_cast<int>(rng()%257);
        std::vector<std::pair<uint,uint>> pairs;
        pairs.reserve(n);
        while (static_cast<int>(pairs.size())<n) {
            pairs.emplace_back(rng()%64, rng()%512);
            std::sort(pairs.begin(), pairs.end());
            pairs.erase(std::unique(pairs.begin(), pairs.end()), pairs.end());
        }
        std::vector<uint> x_values(n), y_values(n);
        for (int i=0;i<n;i++) {
            x_values[i]=pairs[i].first;
            y_values[i]=pairs[i].second;
        }
        for (int query=0;query<100;query++) {
            uint x=rng()%70;
            uint y=rng()%520;
            int expected=binarySearch2_reference(x,y,x_values.data(),y_values.data(),n);
            int actual=binarySearch2_candidate(x,y,x_values.data(),y_values.data(),n);
            assert(actual==expected);
        }
    }
    return 0;
}

#undef uint
