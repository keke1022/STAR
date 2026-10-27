#include <cassert>
#include <chrono>
#include <cstdint>
#include <iostream>
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

template <typename Search>
static double measure(Search search, std::vector<uint> &X, std::vector<uint> &Y,
                      const std::vector<std::pair<uint,uint>> &queries,
                      std::uint64_t &checksum) {
    auto start=std::chrono::steady_clock::now();
    for (const auto &query: queries) {
        checksum+=static_cast<std::uint64_t>(search(query.first,query.second,
                    X.data(),Y.data(),static_cast<int>(X.size()))+2);
    }
    auto stop=std::chrono::steady_clock::now();
    return std::chrono::duration<double,std::milli>(stop-start).count();
}

int main(int argc, char **argv) {
    int groups=argc>1 ? std::stoi(argv[1]) : 4096;
    int per_group=argc>2 ? std::stoi(argv[2]) : 64;
    int query_count=argc>3 ? std::stoi(argv[3]) : 2000000;
    assert(groups>0 && per_group>0 && query_count>0);

    std::vector<uint> X, Y;
    X.reserve(groups*per_group);
    Y.reserve(groups*per_group);
    for (int x=0;x<groups;x++) {
        for (int y=0;y<per_group;y++) {
            X.push_back(static_cast<uint>(x));
            Y.push_back(static_cast<uint>(y*2));
        }
    }

    std::mt19937_64 rng(0x53544152ULL);
    std::vector<std::pair<uint,uint>> queries;
    queries.reserve(query_count);
    for (int i=0;i<query_count;i++) {
        queries.emplace_back(rng()%groups,rng()%(per_group*2));
    }

    std::uint64_t old_checksum=0, new_checksum=0;
    double old_ms=measure(binarySearch2_reference,X,Y,queries,old_checksum);
    double new_ms=measure(binarySearch2_candidate,X,Y,queries,new_checksum);
    assert(old_checksum==new_checksum);
    std::cout << "entries=" << X.size() << " queries=" << queries.size()
              << " same_X_group=" << per_group << '\n'
              << "reference_ms=" << old_ms << " candidate_ms=" << new_ms
              << " speedup=" << old_ms/new_ms << " checksum=" << new_checksum << '\n';
    return 0;
}

#undef uint
