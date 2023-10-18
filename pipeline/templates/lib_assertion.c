{# This code has a dependency to 'lib_utils.c' #}
/**************************************************
* ASSERT utilities
***************************************************/
// return 0 if two values are the same
int compare(const char * target, const char * expected, size_t length){
    int ret = 0;
    for(size_t idx=0; idx<length; idx++) {
        ret = target[idx] - expected[idx];
        if ( ret != 0 ) break;
    }
    if (ret != 0){
        printf_hex("Expected value: ", "\n", expected, length);
    }
    return ret;
}