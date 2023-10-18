
/**************************************************
* For keeping compatibility to the AFL test driver
***************************************************/
char TD_LOG_BUF[1024];   // Cannot use variable when we define an array in global

void logging(const char *msg){
    printf("%s", msg); fflush(stdout);
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
        if (x == TD_DATA_IDX) logging("*");
        sprintf(TD_LOG_BUF, "%02X,", (char)TD_DATA[x] & 0x000000FF);
        logging(TD_LOG_BUF);
    }
    if (TD_DATA_IDX == TD_DATA_SIZE) logging("*");
    logging("]\n");
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
* Compares the results of two functions that should give the same output
***************************************************/
int compare_value(const char* origin, const char* mut, const int size, const char* func_name) {
    int identical = 0;  // 0 - identical  1 - non-identical

    sprintf(TD_LOG_BUF, "Comparing variable %s ... ", func_name);
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


