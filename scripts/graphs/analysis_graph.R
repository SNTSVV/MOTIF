usage <- "
This script is for generating a graph and talbe for the number of killed mutants over time
Usage:
    $ Rscript <script> <GRANULARITY> <MAX_TIME> <INPUT_FILE>
Example:
    $ Rscript <script> 60 200 ./SEMUS/case_studies/ASN1/WORKSPACE/summary_merge_1347.csv
    $ Rscript <script> 60 200 ./case_studies/ASN1/_exp0407/summary_10ks_1347.csv
    $ Rscript <script> 60 200 ./case_studies/ASN1/_exp0407/summary_10ks_1347.csv Percent
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
# Load packages
#########################################################################################
{
suppressMessages(library(ggplot2))
suppressMessages(library(stringr))
suppressMessages(library(scales))
}

#########################################################################################
# Processing command parameter
#########################################################################################
# ENV$PARAMS <- c(60, 180, "./case_studies/ASN1/_exp0418/summary_10ks.csv", "percent")
{
    if (length(ENV$PARAMS) < 3) { help("Not enough parameters") }
    if (is.na(as.numeric(ENV$PARAMS[1]))) { help("Wrong input at the 1st parameter")  }
    if (is.na(as.numeric(ENV$PARAMS[2]))) { help("Wrong input at the 2nd parameter")  }
    
    GRANULARITY <- as.numeric(ENV$PARAMS[1]) # 60 seconds # graph x-axis time unit
    MAX_TIME <- as.numeric(ENV$PARAMS[2])    # AFL execution time in seconds
    INPUT_PATH <- ENV$PARAMS[3]              # summary file
    DRAW_PERCENTAGE <- FALSE
    if (length(ENV$PARAMS)>=4)
        DRAW_PERCENTAGE <- TRUE          # draw Percentage graph (currently don't care the characters)
    
    # additional variables
    OUTPUT_TABLE <- file.path(dirname(INPUT_PATH), sprintf("%s_timetable.csv", basename_without_ext(INPUT_PATH)))
    OUTPUT_GRAPH <- file.path(dirname(INPUT_PATH), sprintf("%s_timegraph.pdf", basename_without_ext(INPUT_PATH)))
    width <- 6                               # graph width in inch
    height <- 4                              # graph height in inch
}

#########################################################################################
# Work code
#########################################################################################
make_timetable<-function(src, granularity, max_time, direction="horizental"){
    # initialize return data
    summary <- data.frame()
    if (direction=="horizental") summary <- data.frame(time=c(1:max_time))
    
    # generate data for csv
    runs <- sort(unique(src$RunID))
    for (runID in runs){
        rundata <- src[src$RunID==runID,]
        killed_array <- c()
        for (time in c(1:max_time)){
            nKilled<-nrow(rundata[rundata$CrashedTime<=time*granularity & rundata$Result=="KILLED",])
            killed_array <- c(killed_array, nKilled)
        }

        if (direction=="horizental"){
            summary <- cbind(summary, killed_array)
        }
        else{
            summary_item<-data.frame(runID=runID, time=c(1:max_time), killed=killed_array)
            summary <- rbind(summary, summary_item)
        }
    }
    
    # finalize return data
    if (direction=="horizental"){
        runs<- sort(unique(src$RunID))
        colnames(summary)<- c("Time", sprintf("Run%d", runs))
    }
    
    return (summary)
}
{
    # load file  (extract a necessary columns)
    data <- read.csv(INPUT_PATH, header=TRUE)
    if (is.null(data$Initial.Result) == FALSE){
        data$CRASHED <- ifelse(data$Initial.Result=="CRASHED", TRUE, FALSE)
    }else{
        data$CRASHED <- FALSE
    }
    data <- data.frame(MutantID=data$Mutant.ID, RunID=data$Run.ID, CRASHED=data$CRASHED, Result= data$Result, CrashedTime=data$Crashed.Time..s.)
    data$CrashedTime <- as.integer(data$CrashedTime)
    
    
    # calculated the number of mutants killed by seed inputs at time 0
    Crashed <- c(0)
    runs <- sort(unique(data$RunID))
    for ( runID in runs ){
        nCrashed <- nrow(data[data$CRASHED==TRUE & data$Result=="KILLED" & data$RunID==runID,])
        Crashed <- c(Crashed, nCrashed)
    }
    
    # generate data for csv
    summary <- make_timetable(data, GRANULARITY, MAX_TIME, direction="horizental")
    summary <- rbind(Crashed, summary)
    
    # make simple statistics
    mins <- c()
    maxs <- c()
    avgs <- c()
    nmutants <- nrow(data[data$RunID==1,])
    for( time in summary$Time){
        item <- as.integer(summary[summary$Time==time, c(runs+1)])
        mins <- c(mins, min(item))
        maxs <- c(maxs, max(item))
        avgs <- c(avgs, mean(item))
    }
    summary$MIN <- mins
    summary$MAX <- maxs
    summary$AVG <- sprintf("%.1f", avgs)
    summary$MIN.P <- sprintf("%.02f%%", mins / nmutants*100)
    summary$MAX.P <- sprintf("%.02f%%", maxs / nmutants*100)
    summary$AVG.P <- sprintf("%.02f%%",  avgs / nmutants*100)
    
    # Save the data
    cat(sprintf("Output time table to %s\n", OUTPUT_TABLE))
    write.table(summary, file=OUTPUT_TABLE, quote=FALSE,  append=FALSE, sep=",", row.names = FALSE, col.names = TRUE)

    # generate data for graph
    summary <- make_timetable(data, GRANULARITY, MAX_TIME, direction="vertical")
    summary <- cbind(approach="one", summary)  # add for changing the color of the line
    

    # Draw graph ========================================
    cat(sprintf("Drawing time graph to %s\n", OUTPUT_GRAPH))
    max_time <- ceiling(max(summary$time))
    max_mutants <- nrow(data[data$RunID==1,])
    if (DRAW_PERCENTAGE==TRUE){
        summary$killed <- summary$killed / max_mutants
    }
    colorPalette <- c("#D55E00", "#000000", "#D55E00", "#CC79A7")
    fontsize<-18
    draw_fontsize <- 6
    g <- ggplot()+
        geom_vline(xintercept = 166.7, linetype="dashed", color = "red", size=0.5, alpha=0.5) +
        geom_line(summary, mapping=aes(x=time, y=killed, color=approach, group=runID)) +
        xlab("Execution time (minutes)")+
        scale_x_continuous(limits = c(0,max_time), labels = scales::comma_format()) +
        scale_color_manual(values=colorPalette)+
        theme_bw()+
        theme(title=element_text(size=fontsize))+
        theme(axis.text=element_text(size=fontsize, color="black"),
              axis.title.y=element_text(size=fontsize, color="black"),
              axis.title.x=element_text(size=fontsize, color="black"),
              axis.line=element_line(colour = "black", size = 0.2, linetype = "solid"))+
        theme(axis.line.y.right = element_line(color = "red",  size = 0.2, linetype = "solid"),
              axis.ticks.y.right = element_line(color = "red"),
              axis.text.y.right = element_text(color = "red"),
              axis.title.y.right = element_text(color = "red")) +
        theme(legend.title=element_blank(), legend.text = element_text(size=fontsize), legend.position="none")
    
    if (DRAW_PERCENTAGE == FALSE){
        g<- g +
            ylab("Number of killed mutants") +
            scale_y_continuous(limits = c(0,max_mutants), labels=scales::comma_format())
    }
    else{
        g<- g +
            ylab("Killed mutants") +
            scale_y_continuous(limits = c(0, 1.0), labels=scales::percent)
    }
    # print(g)
    
    # Save to file
    ggsave(OUTPUT_GRAPH, width=width, height=height)
    print("Finished")
}
