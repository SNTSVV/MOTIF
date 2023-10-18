/**************************************************
* print utilities
***************************************************/
void printf_hex(const char * prefix, const char * postfix, const char *var, size_t length){
    printf(prefix);
    printf("(hex, %ld bytes) ", length);
    for(size_t idx=0; idx<length; idx++) {
        if (idx != 0 && idx %4 == 0) printf(",");
        printf("%02X", (char) var[idx] & 0x000000FF);
    }
    printf(postfix);
}

