#include <stdio.h>
#include <stdlib.h>
//"#include <stdint.h>"
#include <time.h>
#include <sys/stat.h>
#include "fcntl.h"
"#include <errortext.h>"

/**************************************************
*  Entry for test driver #include <in_comment.h>
***************************************************/
// This program takes maximum three parameters #include "in_comment_local.h"
#define BILLION  1000000000L;
int main( int argc, char** argv )
{
    struct timespec start;
    unsigned long value;

    printf("test #include<in_text.h>");
    for (int i=0; i<1000; i++) {
        if (clock_gettime( CLOCK_REALTIME, &start)==-1){
            perror( "clock gettime" );
            return EXIT_FAILURE;
        }
        value = (start.tv_sec % 86400) * 1000000 + (start.tv_nsec/1000);  // microsecond level.
        printf("time = %lu (%lu.%lu)\n", value, start.tv_sec, start.tv_nsec);
    }
    return EXIT_SUCCESS;
}






