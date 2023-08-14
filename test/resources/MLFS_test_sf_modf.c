#ifdef __STDC__
	float modff(float x, float *iptr)
#else
	float modff(x, iptr)
	float x,*iptr;
#endif
{
#ifdef MLFS_FPU_DAZ
	x *= __volatile_onef;
#endif /* MLFS_FPU_DAZ */

	float _xi = 1;
	__int32_t i0,j0;
	__uint32_t i;
	assert(iptr != (void*)0);
	if(iptr == (void*)0) {
	    iptr = &_xi;
	}
	GET_FLOAT_WORD(i0,x);
	j0 = ((i0>>23)&0xff)-0x7f;	/* exponent of x */
	if(j0<23) {			/* integer part in x */
	    if(j0<0) {			/* |x|<1 */
	        SET_FLOAT_WORD(*iptr,i0&0x80000000U);	/* *iptr = +-0 */
		return x;
	    } else {
		i = (0x007fffff)>>j0;
		if((i0&i)==0) {			/* x is integral */
		    __uint32_t ix;
		    *iptr = x;
		    GET_FLOAT_WORD(ix,x);
		    SET_FLOAT_WORD(x,ix&0x80000000U);	/* return +-0 */
		    return x;
		} else {
		    SET_FLOAT_WORD(*iptr,i0&(~i));
		    return x - *iptr;
		}
	    }
	} else {			/* no fraction part */
	    __uint32_t ix;
	    *iptr = x*one;
	    GET_FLOAT_WORD(ix,x);
	    if (FLT_UWORD_IS_NAN(ix&0x7fffffffU)) { return x+x; } /* x is NaN, return NaN */
	    SET_FLOAT_WORD(x,ix&0x80000000U);	/* return +-0 */
	    return x;
	}
}
