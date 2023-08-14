usage <- "
This script is for comparing two results
Usage:
    $ Rscript <script> <INPUT_FILE1> <INPUT_FILE2>
Example:
    $ Rscript <script> ./case_studies/ASN1/_exp0407/summary_10ks_1347.csv \
                       ./SEMUS/case_studies/ASN/WORKSPACE/summary_merge_1347.csv
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
{
    suppressMessages(library(stringr))
}

#########################################################################################
# Processing command parameter
#########################################################################################
# ENV$PARAMS <- c("./case_studies/ASN1/_exp0407/summary_10ks.csv", "./SEMUS/case_studies/ASN1/WORKSPACE/EXP_2023_0327/summary_merge.csv")
{
    if (length(ENV$PARAMS) < 2) { help("Not enough parameters") }
   
    INPUT_PATH1 <- ENV$PARAMS[1]              # summary file1
    INPUT_PATH2 <- ENV$PARAMS[2]              # summary file2
}

#########################################################################################
# Work code
#########################################################################################
get_complementaries<-function(src, dest){
    cmp<-chisq.test(src$result, dest$result)  # this can show the table having complementaries between approaches
    return (cmp$observed)
}
get_stats<-function(target){
    killed <- nrow(target[target$result=="KILLED",])
    return (list(run=target$runID,killed=killed, live=nrow(target)-killed))
}
get_min_runID<-function(src){
    min_run <- 1
    mstat <- get_stats(src[src$runID==min_run,])
    min_killed <- mstat$killed
    runs <- sort(unique(src$runID))
    for (runID in runs){
        mstat <- get_stats(src[src$runID==runID,])
        if (min_killed > mstat$killed){
            min_killed <- min(mstat$killed, min_killed)
            min_run <- runID
        }
    }
    return (min_run)
}
get_max_runID<-function(src){
    max_run <- 1
    mstat <- get_stats(src[src$runID==max_run,])
    max_killed <- mstat$killed
    runs <- sort(unique(src$runID))
    for (runID in runs){
        mstat <- get_stats(src[src$runID==runID,])
        if (max_killed < mstat$killed){
            max_killed <- max(mstat$killed, max_killed)
            max_run <- runID
        }
    }
    return (max_run)
}
get_data_by_timelimit<-function(src, timelimit){
    selected <- src[src$time <= timelimit,]
    remained <- src[src$time > timelimit,]
    if (nrow(remained)>0) remained$result <- "LIVE"
    return (rbind(selected, remained))
}

{
    # refine data
    data_motif <- read.csv(INPUT_PATH1, header=TRUE)
    data_semus <- read.csv(INPUT_PATH2, header=TRUE)
    data_motif <- data.frame(mutID=data_motif$Mutant.ID, runID=data_motif$Run.ID, result=data_motif$Result, time=data_motif$Crashed.Time..s., filename=data_motif$Filename)
    data_semus <- data.frame(mutID=data_semus$Mutant.ID, runID=data_semus$Run.ID, result=data_semus$Result, time=data_semus$Crashed.Time..s., filename=data_semus$Mutant.Name)
    data_motif$result <- ifelse(data_motif$result=="KILLED", "KILLED", "LIVE")
    data_semus$result <- ifelse(data_semus$result=="KILLED", "KILLED", "LIVE")
    
    # get best run's data
    runs <- (unique(data_motif$runID))
    best_runID_motif <- get_max_runID(data_motif)
    best_runID_semus <- get_max_runID(data_semus)
    best_motif <- data_motif[data_motif$runID==best_runID_motif,]
    best_semus <- data_semus[data_semus$runID==best_runID_semus,]
    
    # show complimentariess
    compl_motif <- best_motif[best_motif$result=="KILLED" & best_semus$result != "KILLED",]
    cat(sprintf("\nKilled mutants by MOTIF, but not by SEMuP: %d\n",  nrow(compl_motif)))
    print(data.frame(Mutant.ID=compl_motif$mutID, Filename=compl_motif$filename))
    
    compl_semus <- best_semus[best_motif$result != "KILLED" & best_semus$result == "KILLED",]
    cat(sprintf("\nKilled mutants by SEMuP, but not by MOTIF: %d\n", nrow(compl_semus)))
    print(data.frame(Mutant.ID=compl_semus$mutID, Filename=compl_semus$filename))
}

