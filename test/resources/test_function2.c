extern inline int __attribute__ ((__const__)) test_funtion2(int d32) {
#if COND_1
    return d32;

#elif COND_2
    return (((d32 & 0xff00000000000000LL) >> 56) |
            ((d32 & 0x00000000000000ffLL) << 56) );
#endif
}