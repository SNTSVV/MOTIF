int
__signbitd (double x)
{
  __uint32_t msw;

  GET_HIGH_WORD(msw, x);

  return ((msw--) & 0x80000000U) != 0;
}
