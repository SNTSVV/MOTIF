usage <- "
This script is for comparing two results
Usage:
    $ Rscript <script> <GRANULARITY> <MAX_TIME> <INPUT_FILE1> <INPUT_FILE2>
Example:
    $ Rscript <script> 60 200 ./_ASN1_MASS/_exp0207/summary_10ks_1347.csv \
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
# ENV$PARAMS <- c(60, 200, "./case_studies/ASN1/_exp0207/summary_10ks.csv", "./SEMUS/case_studies/ASN1/WORKSPACE/EXP_2023_0324/summary_merge.csv")
{
    if (length(ENV$PARAMS) < 4) { help("Not enough parameters") }
    if (is.na(as.numeric(ENV$PARAMS[1]))) { help("Wrong input at the 1st parameter")  }
    if (is.na(as.numeric(ENV$PARAMS[2]))) { help("Wrong input at the 2nd parameter")  }
    
    GRANULARITY <- as.numeric(ENV$PARAMS[1]) # 60 seconds # graph x-axis time unit
    MAX_TIME <- as.numeric(ENV$PARAMS[2])    # AFL execution time in seconds
    INPUT_PATH1 <- ENV$PARAMS[3]              # summary file1
    INPUT_PATH2 <- ENV$PARAMS[4]              # summary file2
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
    return (list(run=runID,killed=killed, live=nrow(target)-killed))
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
    data_motif <- data.frame(mutID=data_motif$Mutant.ID, runID=data_motif$Run.ID, result=data_motif$Result, time=data_motif$Crashed.Time..s.)
    data_semus <- data.frame(mutID=data_semus$Mutant.ID, runID=data_semus$Run.ID, result=data_semus$Result, time=data_semus$Crashed.Time..s.)
    data_motif$result <- ifelse(data_motif$result=="KILLED", "KILLED", "LIVE")
    data_semus$result <- ifelse(data_semus$result=="KILLED", "KILLED", "LIVE")
    
    cat("\n compare by run (just match between the same runID)\n")
    cat("RunID, MOTIF,SEMUS, KILLED-KILLED,KILLED-LIVE,LIVE-KILLED,LIVE-LIVE, Chi-sq, Ficher-test\n")
    runs <- (unique(data_motif$runID))
    
    for (runID in runs){
        mstat <- get_stats(data_motif[data_motif$runID==runID,])
        sstat <- get_stats(data_semus[data_semus$runID==runID,])
        cont.table <- data.frame(MOTIF=c(mstat$killed, mstat$live), SEMuS=c(sstat$killed, sstat$live), row.names = c("KILLED", "LIVE"))
        
        # calculate statistical test
        chi <- chisq.test(cont.table)
        fi <- fisher.test(cont.table)
        comp.table <- get_complementaries(data_motif[data_motif$runID==runID,], data_semus[data_semus$runID==runID,])
        
        cat(sprintf("%d, %d,%d, %d,%d,%d,%d, %.4f,%.4f\n",
                    runID, mstat$killed, sstat$killed, comp.table[1,1], comp.table[1,2], comp.table[2,1], comp.table[2,2], chi$p.value, fi$p.value))
    }
    
    cat("\n compare by time\n")
    cat("      MOTIF vs SEMUS\n")
    cat("Time, MOTIF, SEMUS, KILLED-KILLED, KILLED-LIVE, LIVE-KILLED, LIVE-LIVE, Chi-sq, Ficher-test\n")
    for (timeID in c(1:MAX_TIME)){
        # make results within the time limits
        timelimit <- timeID * GRANULARITY
        motif <- get_data_by_timelimit(data_motif, timelimit)
        semus <- get_data_by_timelimit(data_semus, timelimit)
        
        mstat <- get_stats(motif)
        sstat <- get_stats(semus)
        cont.table <- data.frame(MOTIF=c(mstat$killed, mstat$live), SEMuS=c(sstat$killed, sstat$live), row.names = c("KILLED", "LIVE"))
        
        # calculate statistical test
        chi <- chisq.test(cont.table)
        fi <- fisher.test(cont.table)
        comp.table <- get_complementaries(motif, semus)
        
        cat(sprintf("%d, %d,%d, %d,%d,%d,%d, %.4f,%.4f\n",
                    timeID, mstat$killed, sstat$killed, comp.table[1,1], comp.table[1,2], comp.table[2,1], comp.table[2,2], chi$p.value, fi$p.value))
    }
    

    cat("\n compare by worst run and best run\n")
    IDset <- data.frame(WORST=c(get_min_runID(data_motif), get_min_runID(data_semus)),
                        BEST=c(get_max_runID(data_motif), get_max_runID(data_semus)))
    for (col in c(1:ncol(IDset))){
        mstat <- get_stats(data_motif[data_motif$runID==IDset[1, col],])
        sstat <- get_stats(data_semus[data_semus$runID==IDset[2, col],])
        cont.table <- data.frame(MOTIF=c(mstat$killed, mstat$live), SEMuS=c(sstat$killed, sstat$live), row.names = c("KILLED", "LIVE"))
        
        # calculate statistical test
        chi <- chisq.test(cont.table)
        fi <- fisher.test(cont.table)
        comp.table <- get_complementaries(data_motif[data_motif$runID==IDset[1, col],],
                                          data_semus[data_semus$runID==IDset[2, col],])
        
        cat(sprintf("%s -- runID=(MOTIF: %d, SEMuS: %d), killed=(MOTIF: %d, SEMuS: %d)\n",
                    colnames(IDset)[col], IDset[1, col], IDset[2, col], mstat$killed, sstat$killed))
        cat(sprintf("   -- complementaries: KILLED-KILLED, KILLED-LIVE, LIVE-KILLED, LIVE-LIVE\n"))
        cat(sprintf("                       %13d, %11d, %11d, %9d\n",
                    comp.table[1,1], comp.table[1,2], comp.table[2,1], comp.table[2,2]))
        cat(sprintf("\t -- chi-sq: %.4f\n", chi$p.value))
        cat(sprintf("\t -- fisher: %.4f\n\n", fi$p.value))
    }
    
}

