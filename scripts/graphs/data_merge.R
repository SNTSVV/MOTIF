usage <- "
This script is for merging experiment results of SEMUS
Usage:
    $ Rscript <script> <INPUT_PATH> <EXP_NAME>
Example:
    $ Rscript <script> ./SEMUS/case_studies/ASN/WORKSPACE EXP_2023_0317
    This script will generate \"summary_merge.csv\" and \"summary_merge_<filtered_rows>.csv\"
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
# ENV$PARAMS <- c("./SEMUS/case_studies/ASN1/WORKSPACE/_EXP_2023_0322", "EXP_2023_0322")
{
    if (length(ENV$PARAMS) < 2) { help("Not enough parameters") }
    
    INPUT_PATH  <- ENV$PARAMS[1]
    MATCH_NAME  <- ENV$PARAMS[2]
    OUTPUT_FILE <- file.path(INPUT_PATH, "summary_merge.csv")
    OUTPUT_SUBSET_FILE <- file.path(INPUT_PATH, "summary_merge_%d.csv")
}

#########################################################################################
# Work code
#########################################################################################
{
    # load data from summary.csv for each result folder
    data <- data.frame()
    dirnames <- list.dirs(INPUT_PATH)
    if (dirnames[1]==INPUT_PATH) dirnames <- dirnames[-1]
    for (dirname in dirnames){
        folder_name <- basename(dirname)
        if (! startsWith(folder_name, MATCH_NAME) ) next;
        subdata <- read.csv(file.path(dirname, "summary.csv"), header=TRUE)
        # data <- data.frame(MutantID=data$Mutant.ID, RunID=data$Run.ID,Result= data$Result, CrashedTime=data$Crashed.Time..s.)
        runID <- strtoi(substring(folder_name, nchar(MATCH_NAME)+2))
        subdata <- cbind(data.frame(RunID=runID), subdata)
        
        data <- rbind(data, subdata)
    }
    
    # backup data for the subset
    subdata <- data
    
    # save the merged data
    print(sprintf("Writing the merged data into %s", OUTPUT_FILE))
    colnames(data)<- c("Run ID", "Mutant ID", "Mutant Name", "Num Tests", "Crashed Time (s)", "Result")
    write.table(data, file=OUTPUT_FILE, quote=FALSE, append=FALSE, sep=",", row.names = FALSE, col.names = TRUE)
    
    # Filter out exception functions
    EXCEPTION_FILE <- file.path(INPUT_PATH, "exception")
    if (file.exists(EXCEPTION_FILE)) {
        # load exeception list
        exception <- read.csv(EXCEPTION_FILE,header=FALSE)
        exception <- str_trim(exception$V1)
        
        # set function names form  the data
        # data$Function <- strsplit(data$MutantName, split="\\.")[[1]][6]  # Not working, replaced to the below
        fnames<-c()
        for(mname in subdata$MutantName){
            v<-str_trim(strsplit(mname, split="\\.")[[1]][6])
            fnames<-c(fnames, v)
        }
        subdata$Function <- fnames
        
        # remove exceptions from Functions
        for(functionname in exception){
            subdata <- subdata[subdata$Function != functionname,]
        }
        subdata <- subset(subdata, select = -c(Function))
        
        # remove exceptions from Mutants
        for(mname in exception){
            mname <- basename(mname)
            subdata <- subdata[subdata$MutantName != mname,]
        }
        
        # Write table
        filename <- sprintf(OUTPUT_SUBSET_FILE, nrow(subdata[subdata$RunID==1,]))
        print(sprintf("Writing the filtered out data into %s", filename))
        colnames(subdata)<- c("Run ID", "Mutant ID", "Mutant Name", "Num Tests", "Crashed Time (s)", "Result")
        write.csv(subdata, file=filename, quote=FALSE, append=FALSE, sep=",", row.names = FALSE, col.names = TRUE)
    }
}
