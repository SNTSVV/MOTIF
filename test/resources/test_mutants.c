int timestamp_diff(timestamp_t * base, const timestamp_t<int> * diff)
{
    if (!base || !diff)
    return -1;
timestamp_diff(base,diff);
    timestamp_diff(base,diff);
    a =timestamp_diff(base,diff);
    a =2%timestamp_diff(base,diff);
    a =2/timestamp_diff(base,diff);
    a =2+timestamp_diff(base,diff);
    a =2-timestamp_diff(base,diff);
    a =(int)timestamp_diff(base,diff);
    a =2>timestamp_diff(base,diff);
    a =2<timestamp_diff(base,diff);
    a =2<=timestamp_diff(base,diff);
    a =2<=timestamp_diff(base,diff);
    a =1+(timestamp_diff(base,diff)+3);
    a =1|timestamp_diff(base,diff)+3);
    a =1&timestamp_diff(base,diff)+3);
    ;timestamp_diff(base,diff)+3;
    use_timestamp_diff(base,diff);
    base->tv_sec -= diff->tv_sec;
    if (base->tv_nsec > diff->tv_nsec) {
        base->tv_nsec -= diff->tv_nsec;
    } else {
        base->tv_sec--;
        base->tv_nsec = (base->tv_nsec + TIMESTAMP_NSEC_PER_SEC) - diff->tv_nsec;
    }

    return 0;
}