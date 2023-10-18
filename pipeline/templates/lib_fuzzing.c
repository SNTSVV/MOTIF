

/**************************************************
* Global variables
***************************************************/
char LOG_DIR_NAME[5] = "logs";
char INPUT_DIR_NAME[7] = "inputs";
char SINGLE_LOG_NAME[10] = "total.log";
char SEQUENCE_NAME[8] = "__num__";
char * TD_WORKING_DIR = NULL;      // keeping working directory

/**************************************************
* Manage execution ID
***************************************************/
unsigned long long TD_SEQ_ID = 0;  // sequence_id
unsigned long long TD_TIME_ID = 0;
unsigned long long DIST_BASE_NUM = 5000; // (maximum file nums in a folder)
const int TD_PATH_BUF_SIZE = 5000;

static void _mkdir(const char *dir) {
    char tmp[TD_PATH_BUF_SIZE];
    char *p = NULL;
    size_t len;

    snprintf(tmp, sizeof(tmp),"%s",dir);
    len = strlen(tmp);
    if(tmp[len - 1] == '/')
        tmp[len - 1] = 0;
    for(p = tmp + 1; *p; p++)
        if(*p == '/') {
            *p = 0;
            mkdir(tmp, S_IRWXU);
            *p = '/';
        }
    mkdir(tmp, S_IRWXU);
}

void prepare_dist_dir(const char * dirpath, char *dist_dir){
    unsigned long long dist_num = (TD_SEQ_ID/DIST_BASE_NUM)*DIST_BASE_NUM;
    sprintf(dist_dir, "%s/%010llu", dirpath, dist_num);
    _mkdir(dist_dir);
}

// Get the sequence id of this execution
unsigned long long set_seq_id(){
    char filepath[TD_PATH_BUF_SIZE];

    // if workdir does not exist, set SEQ_ID = 0
    if (TD_WORKING_DIR == NULL) return 0;
    _mkdir(TD_WORKING_DIR);

    // create filename
    sprintf(filepath, "%s/%s", TD_WORKING_DIR, SEQUENCE_NAME);


    // This try is not perfect, if you have better idea, please update it.
    if (access(filepath, F_OK) != 0) {
        FILE *fd = fopen(filepath, "w");
        fprintf(fd, "0");
        fclose(fd);
    }

    // open a file with lock
    int fileNo = open(filepath, O_RDWR);
    flock(fileNo, LOCK_EX);  // LOCK_EX: Exclusive lock

    // read a value
    char buf[100];
    long size = read(fileNo, buf, 100);
    if (size==-1) perror("read");
    buf[size] = 0;  // set NULL at the end of the read text

    // increase the ID
    char *endptr;    // this variable is just for the out parameter value of the strtoull function
    TD_SEQ_ID = strtoull(buf, &endptr, 10) + 1;  // get a number based on 10

    // write the changed value
    sprintf(buf, "%llu", TD_SEQ_ID);
    size = strlen(buf);
    lseek(fileNo, 0, SEEK_SET);
    write(fileNo, buf, size);

    // unlock
    flock(fileNo, LOCK_UN);  // LOCK_UN: Unlock
    close(fileNo);
    return 0;
}

// get a time value in microseconds
unsigned long long get_micro_time(){
    // time.h required
    struct timespec value;
    if (clock_gettime( CLOCK_REALTIME, &value)==-1){
        perror( "clock gettime" );
        return 0;
    }
    // microsecond level
    return (unsigned long long)value.tv_sec * 1000000 + (value.tv_nsec/1000);
}


void set_time_id(){
    TD_TIME_ID = get_micro_time();
}

/**************************************************
* Logging functions
***************************************************/
FILE* TD_LOG_FP=NULL;
char TD_LOG_BUF[1024];   // Cannot use variable when we define an array in global

void log_open(){
    // set log path
    char path[TD_PATH_BUF_SIZE];
    char dist_dir[TD_PATH_BUF_SIZE];
    sprintf(path, "%s/%s", TD_WORKING_DIR, LOG_DIR_NAME);   // create a directory for logs
    prepare_dist_dir(path, dist_dir);    // create a sub directory for logs
    sprintf(path, "%s/%010llu.log", dist_dir, TD_SEQ_ID);
    TD_LOG_FP = fopen(path, "w");
}

void log_close() {
    if (TD_LOG_FP != NULL){
        fclose(TD_LOG_FP);
        TD_LOG_FP = NULL;
    }
}

void logging(const char *msg){
    if (TD_LOG_FP != NULL) { fprintf(TD_LOG_FP, "%s", msg); fflush(TD_LOG_FP); }
    else                   { printf("%s", msg); fflush(stdout); }
    TD_LOG_BUF[0] = NULL;
}

/**************************************************
* Simple logging functions
***************************************************/
FILE* TD_SN_LOG_FP=NULL;

void log_open_check(){
    // set log path
    char logpath[TD_PATH_BUF_SIZE];
    sprintf(logpath, "%s/%s", TD_WORKING_DIR, SINGLE_LOG_NAME);
    TD_SN_LOG_FP = fopen(logpath, "a");
    if (TD_SEQ_ID==1){
        fprintf(TD_SN_LOG_FP,"SeqID,TimeID,Initial,Origin,Mutant,Comp");
    }
}

void log_close_check() {
    if (TD_SN_LOG_FP != NULL){
        fclose(TD_SN_LOG_FP);
        TD_SN_LOG_FP = NULL;
    }
}

unsigned long TD_SN_LOG_CNT=0;
void logging_check_point(const int i){
    char log_buf[100];

    if (TD_SN_LOG_CNT == 0){
        sprintf(log_buf, "\n%llu,%llu,1", TD_SEQ_ID,TD_TIME_ID);
    }
    else{
        sprintf(log_buf, ",%d", i);
    }
    TD_SN_LOG_CNT++;

    if (TD_SN_LOG_FP != NULL) {
        fprintf(TD_SN_LOG_FP, "%s", log_buf);
        fflush(TD_SN_LOG_FP);
    }else{
        printf("%s", log_buf);
        fflush(stdout);
    }
}


/**************************************************
* Input file read and convert it into a variable
***************************************************/
char* TD_DATA = NULL;
unsigned int TD_DATA_SIZE = 0;
unsigned int TD_DATA_IDX = 0;

void load_file(const char* filename){
    logging("Read the file data into buffer\n");

    FILE *fp = fopen(filename, "rb");
    if (fp == NULL) {
        logging("[-] Failed to open the input file\n");
        exit(-1);
    }

    // calculate data size
    fseek(fp, 0L, SEEK_END);
    TD_DATA_SIZE = ftell(fp);
    rewind(fp);

    // load all data from file
    TD_DATA = (char *) malloc(TD_DATA_SIZE);
    size_t rdsize = fread(TD_DATA, 1, TD_DATA_SIZE, fp);
    sprintf(TD_LOG_BUF, "File read %ld bytes\n", rdsize);
    logging(TD_LOG_BUF);

    fclose(fp);

    // initialize
    TD_DATA_IDX = 0;
}

void seek_data_index(const int v){ TD_DATA_IDX = v;}

void print_data(){
    sprintf(TD_LOG_BUF, "Data read (%3d/%3d): 0x[", TD_DATA_IDX, TD_DATA_SIZE);
    logging(TD_LOG_BUF);
    for(unsigned int x=0; x<TD_DATA_SIZE; x++){
        if (x==TD_DATA_IDX) logging("*");
        sprintf(TD_LOG_BUF, "%02X,", (char)TD_DATA[x] & 0x000000FF);
        logging(TD_LOG_BUF);
    }
    if (TD_DATA_IDX == TD_DATA_SIZE) logging("*");
    logging("]\n");
}

unsigned int extend_data(const unsigned int _size_to_extend){
    int prev_size = TD_DATA_SIZE;

    // realloc
    int new_size = TD_DATA_SIZE + _size_to_extend;
    TD_DATA = (char *) realloc(TD_DATA, new_size);

    // assign random seed with nanoseconds
    unsigned long long time = get_micro_time();
    srand((unsigned int)time); // &t1

    for (unsigned int x=0; x<_size_to_extend; x++){
        TD_DATA[prev_size+x] = ((int)rand()) & 0x000000FF;  // select 8 bit random value
    }

    TD_DATA_SIZE = new_size;
    return prev_size;   // return old size
}

void get_value(char * var, const int size, const int is_string){
    memcpy(var, TD_DATA+TD_DATA_IDX, size);
    TD_DATA_IDX += size;

    if (is_string != 0) var[size-1] = 0;
}

void clean(){
    if (TD_DATA != NULL){
        free(TD_DATA);
        TD_DATA = NULL;
    }
}


/**************************************************
* Make a copy of the given input
***************************************************/
#define TD_INPUT_NO -1         //  -1 - not storing
#define TD_INPUT_ALL 0         //   0 - storing all inputs,
#define TD_INPUT_ONLY_CRASH 1  //   1 - storing only crashed inputs
int TD_INPUT_STORE_OPTION = TD_INPUT_NO; // NO is the default

void store_data(const char * output_filename, char* buf, unsigned int buf_size){
    if (buf == NULL) return;

    // open output file
    FILE* fout = fopen(output_filename, "wb");
    fwrite(buf, 1, buf_size, fout);
    fclose(fout);
}


int INPUT_FILE_REVISION_ID=0; // revision number for the input file

void store_input_data() {
    if (TD_WORKING_DIR == NULL) return;

    // make output filename
    char output_path[TD_PATH_BUF_SIZE];
    char dist_dir[TD_PATH_BUF_SIZE];
    sprintf(output_path, "%s/%s", TD_WORKING_DIR, INPUT_DIR_NAME);   // create a directory for logs
    prepare_dist_dir(output_path, dist_dir);    // create a sub directory for logs

    if (INPUT_FILE_REVISION_ID == 0) {
        sprintf(output_path, "%s/%010llu.inb", dist_dir, TD_SEQ_ID);
    } else {
        sprintf(output_path, "%s/%010llu_revised%d.inb", dist_dir, TD_SEQ_ID, INPUT_FILE_REVISION_ID);
    }

    // store data
    store_data(output_path, TD_DATA, TD_DATA_SIZE);
}


/**************************************************
* Compares the results of two functions that should give the same output
***************************************************/
int compare_value(const char* origin, const char* mut, const int size, const char* var_name) {
    int identical = 0;  // 0 - identical  1 - non-identical

    sprintf(TD_LOG_BUF, "Comparing variable %s ... ", var_name);
    logging(TD_LOG_BUF);

    int idx = 0;
    for (; idx < size; ++idx){
        if ((char)(origin[idx]) != (char)(mut[idx])){
            identical = 1;   // not identical
            break;
        }
    }

    if (identical == 0){
        logging("Identical.\n");
    }else{

        sprintf(TD_LOG_BUF, "Different at %dth byte!\n", idx);
        logging(TD_LOG_BUF);

        // output origin value
        logging("  -  origin: 0x[");
        for (int i=0; i<size; i++){
            sprintf(TD_LOG_BUF, "%02X, ", (char)origin[i] & 0x000000FF);
            logging(TD_LOG_BUF);
        }
        logging("]\n");

        // output mut value
        logging("  - mutated: 0x[");
        for (int i=0; i<size; i++){
            sprintf(TD_LOG_BUF, "%02X, ", (char)mut[i] & 0x000000FF);
            logging(TD_LOG_BUF);
        }
        logging("]\n");
    }

    return identical;
}


// compare without size
int compare_string(const char* origin, const char* mut, const char* var_name) {
    int identical = 0;  // 0 - identical  1 - non-identical

    sprintf(TD_LOG_BUF, "Comparing variable %s ... ", var_name);
    logging(TD_LOG_BUF);

    identical = strcmp(origin, mut) == 0 ? 0 : 1;

    if (identical == 0){
        logging("Identical.\n");
    }else{
        logging("Different!!\n");
        sprintf(TD_LOG_BUF, "  -  origin: %s\n", origin);
        logging(TD_LOG_BUF);
        sprintf(TD_LOG_BUF, "  -  mut: %s\n", mut);
        logging(TD_LOG_BUF);
    }

    return identical;
}


/**************************************************
* abort function that closes file first
***************************************************/
void safe_abort(){
    // clean data
    clean();

    //close files that is currently open
    log_close_check();
    log_close();

    // abort
    abort();
}

/**************************************************
* for the signal setup
***************************************************/
// func_handler should follow the following prototype (second one preferred)
//  - void sig_error_handler(int signo)
//  - void sig_error_handler(int signo, siginfo_t *info, void *other)
{#
char SIGNALS_STR[32][10] = {
    "SIGHUP",   //  1 -
    "SIGINT",   //  2 -
    "SIGQUIT",  //  3 - Quit from keyboard (Core Dump)
    "SIGILL",   //  4 - Illegal instruction  (Core Dump)
    "SIGTRAP",  //  5 - Breakpoint for debugging  (Core Dump)
    "SIGABRT",  //  6 - Abnormal termination  (Core Dump)
    "SIGBUS",   //  7 - Bus error (Core Dump)
    "SIGFPE",   //  8 - Floating-point exception (Core Dump)
    "SIGKILL",  //  9 - Forced process termination
    "SIGUSR1",  // 10 -
    "SIGSEGV",  // 11 - Segmentation Fault  (Core Dump) - Invalid memory reference
    "SIGUSR2",  // 12 -
    "SIGPIPE",  // 13 - Broken pipe (Termination)
    "SIGALRM", "SIGTERM", "SIGSTKFLT", "SIGCHLD","SIGCONT",
    "SIGSTOP","SIGTSTP","SIGTTIN", "SIGTTOU","SIGURG",
    "SIGXCPU","SIGXFSZ","SIGVTALRM", "SIGPROF","SIGWINCH",
    "SIGPOLL",
    "SIGPWR",   // 30 -
    "SIGSYS",    // 31 - Bad system CALL (Dump)
    ""
};

int setup_signal(void* func_handler){
    int sigtypes[] = {SIGILL, SIGBUS, SIGFPE, SIGSEGV, SIGPIPE, SIGSYS};
    int n_types = 6;

    struct sigaction sa;
    memset (&sa, 0, sizeof(sa));
    sa.sa_sigaction = func_handler;
    sa.sa_flags = SA_SIGINFO;

    int ret = 0;
    for (int i=0; i<n_types; i++){
        ret |= sigaction(sigtypes[i], &sa, NULL); // register handler for signals
    }
    return ret;
}

int release_signal(){
    return setup_signal(SIG_DFL);
}
#}