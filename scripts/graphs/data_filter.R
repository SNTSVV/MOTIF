usage <- "
This script is for filtering out some experiment results of MOTIF
Usage:
    $ Rscript <script> <RESULT_FILE>
Example:
    $ Rscript <script> ./_ASN1_MASS/_exp0207/summary_10ks.csv
    This script will generate \"./_ASN1_MASS/_exp0207/summary_10ks_<filterred_rows>.csv\"
"
options(warn=-1)
#########################################################################################
# SET ENV
#########################################################################################
{
    absolute_path<-function(path, base=NULL){
        # if the path is not the absolute path (including home directory)
        if (!startsWith(path, "/") && !startsWith(path, "~")){
            if (is.null(base)) { base <- getwd() }
            return (file.path(base, path))
        }
        return (path)
    }
    getENV<-function(baseDir=NULL){
        env<-list()
        args <- commandArgs(trailingOnly = FALSE)
        env$COMMAND_DIR <- getwd()
        this_script <- args[startsWith(args,"--file=" )==TRUE]
        
        if (length(this_script)!=0){  # In case of executing this code from the command
            this_script <- substring(this_script, 8)   # remove prefix ("--file=")
            this_script <- absolute_path(this_script, base=env$COMMAND_DIR)
            env$THIS_SCRIPT <- basename(this_script)
            env$SCRIPT_DIR <- dirname(this_script)
            env$PARAMS <- commandArgs(trailingOnly = TRUE)
        }else{   # In case of executing this code from the IDE
            env$THIS_SCRIPT <- ""
            env$SCRIPT_DIR <- absolute_path(env$THIS_SCRIPT, base=absolute_path(baseDir))
            env$PARAMS <- c()
        }
        return (env)
    }
    help<-function(error_message=NULL){
        cat(str_replace_all(usage,"<script>", ENV$THIS_SCRIPT))
        if (!is.null(error_message)){
            msg <- sprintf("\nERROR:: %s\n",error_message)
            cat(msg)
        }
        sys.on.exit()
    }
    basename_without_ext<-function(filepath){
        return (sub('\\..*$', '', basename(filepath)))
    }
    
    
    ENV<-getENV(base='scripts/graphs')
    cat("========================================================================================\n")
    cat(sprintf("COMMAND_DIR : %s\n", ENV$COMMAND_DIR))
    cat(sprintf("SCRIPT_DIR  : %s\n", ENV$SCRIPT_DIR))
    cat(sprintf("THIS_SCRIPT : %s\n", ifelse(ENV$THIS_SCRIPT=="", "NONE", ENV$THIS_SCRIPT)))
    cat(sprintf("PARAMS      : %s\n", ifelse(length(ENV$PARAMS)==0, "NONE", paste(ENV$PARAMS, collapse=" "))))
    cat("----------------------------------------------------------------------------------------\n")
    
}


#########################################################################################
# Load packages and function definitions
#########################################################################################
suppressMessages(library(stringr))

#########################################################################################
# Processing command parameter
#########################################################################################
# ENV$PARAMS <- c("./_ASN1_MASS/_exp0207/summary_10ks.csv")
{
    if (length(ENV$PARAMS) < 1) { help("Not enough parameters") }
    
    RESULT_FILE  <- ENV$PARAMS[1]
    OUTPUT_FILE <- file.path(dirname(RESULT_FILE), paste(basename_without_ext(RESULT_FILE), "_%d.csv", sep=''))
    EXCEPTION_FILE <- file.path(dirname(RESULT_FILE), "exception")
}

#########################################################################################
# Work code
#########################################################################################
{
    # load data from summary.csv for each result folder
    data <- read.csv(RESULT_FILE, header=TRUE)
    head(data)
    colnames(data)
    
    # Filter out exception functions
    if (file.exists(EXCEPTION_FILE)) {
        # load exeception list
        exception <- read.csv(EXCEPTION_FILE,header=FALSE)
        exception <- str_trim(exception$V1)
        
        # set function names form  the data
        # data$Function <- strsplit(data$MutantName, split="\\.")[[1]][6]  # Not working, replaced to the below
        fnames<-c()
        for(mname in data$Filename){
            v<-str_trim(strsplit(mname, split="\\.")[[1]][6])
            fnames<-c(fnames, v)
        }
        data$Function <- fnames
        
        # remove exceptions from Functions
        for(functionname in exception){
            data <- data[data$Function != functionname,]
        }
        data <- subset(data, select = -c(Function))
        
        # remove exceptions from Mutants
        for(mname in exception){
            data <- data[data$Filename != mname,]
        }
        
        
        # Write table
        filename <- sprintf(OUTPUT_FILE, nrow(data[data$Run.ID==1,]))
        print(sprintf("Writing the filtered out data into %s", filename))
        write.csv(data, file=filename, quote=FALSE, append=FALSE, sep=",", row.names = FALSE, col.names = TRUE)
    }
}
