usage <- "
This script is for generating a graph and talbe for the number of killed mutants over time
Usage:
    $ Rscript <script> <GRANULARITY> <MAX_TIME> <INPUT_FILE1> <INPUT_FILE2>
Example:
    $ Rscript <script> 60 200 ./case_studies/ASN1/_exp0407/summary_10ks.csv ./SEMUS/case_studies/ASN1/WORKSPACE/EXP_2023_0324/summary_merge.csv
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
# ENV$PARAMS <- c(1, 10800, "./case_studies/ASN1/_exp0407/summary_10ks_1347.csv", "./SEMUS/case_studies/ASN/WORKSPACE/EXP_2023_0421/summary_merge_1347.csv", "percent")
{
    if (length(ENV$PARAMS) < 4) { help("Not enough parameters") }
    if (is.na(as.numeric(ENV$PARAMS[1]))) { help("Wrong input at the 1st parameter")  }
    if (is.na(as.numeric(ENV$PARAMS[2]))) { help("Wrong input at the 2nd parameter")  }
    
    GRANULARITY <- as.numeric(ENV$PARAMS[1]) # in seconds
    MAX_TIME <- as.numeric(ENV$PARAMS[2])    # total execution time in <GRANULARITY>
    INPUT_PATH1 <- ENV$PARAMS[3]              # summary file
    INPUT_PATH2 <- ENV$PARAMS[4]              # summary file
    DRAW_PERCENTAGE <- FALSE
    if (length(ENV$PARAMS)>=5)
        DRAW_PERCENTAGE <- TRUE          # draw Percentage graph (currently don't care the characters)
    
    # additional variables
    OUTPUT_GRAPH <- file.path(dirname(INPUT_PATH1), sprintf("%s_together.pdf", basename_without_ext(INPUT_PATH1)))
    width <- 6                               # graph width in inch
    height <- 3                              # graph height in inch
}

#########################################################################################
# Work code
#########################################################################################
make_timetable<-function(data, granularity, max_time, direction="horizental"){
    # initialize return data
    summary <- data.frame()
    if (direction=="horizental") summary <- data.frame(time=c(1:max_time))
    
    # generate data for csv
    runs <- sort(unique(data$runID))
    for (runID in runs){
        rundata <- data[data$runID==runID,]
        killed_array <- c()
        for (time in c(1:max_time)){
            nKilled<-nrow(rundata[rundata$crashedTime<=time*granularity & rundata$result=="KILLED",])
            killed_array <- c(killed_array, nKilled)
        }
        if (direction=="horizental"){
            summary <- cbind(summary, killed_array)
        }
        else{
            summary_item<-data.frame(runID=as.integer(runID), time=c(1:max_time), killed=killed_array)
            summary <- rbind(summary, summary_item)
        }
    }
    
    # finalize return data
    if (direction=="horizental"){
        runs<- sort(unique(data$runID))
        colnames(summary)<- c("Time", sprintf("Run%d", runs))
    }
    
    return (summary)
}

{
    # load file 1 (extract a necessary columns)
    motif <- read.csv(INPUT_PATH1, header=TRUE)
    motif <- data.frame(mutantID=motif$Mutant.ID, runID=motif$Run.ID,result= motif$Result, crashedTime=motif$Crashed.Time..s.)
    
    # load file 2 (extract a necessary columns)
    semus <- read.csv(INPUT_PATH2, header=TRUE)
    semus <- data.frame(mutantID=semus$Mutant.ID, runID=semus$Run.ID,result= semus$Result, crashedTime=semus$Crashed.Time..s.)
    
    # generate data for graph
    summary_motif <- make_timetable(motif, GRANULARITY, MAX_TIME, direction="vertical")
    summary_motif <- summary_motif[summary_motif$time <= 10000 , ]
    summary_semus <- make_timetable(semus, GRANULARITY, MAX_TIME, direction="vertical")
    summary_semus$runID <- summary_semus$runID + 100
    summary <- data.frame(approach="MOTIF", summary_motif)
    summary <- rbind(summary, data.frame(approach="SEMuP", summary_semus))
    summary$approach <- as.factor(summary$approach)
    summary$runID <- as.integer(summary$runID)
    
    # # make data for
    # timeout_data <- summary[summary$time==167,]
    # avgsKilled <- aggregate(list(killed=timeout_data$killed),
    #                         by=list(approach=timeout_data$approach, time=timeout_data$time),
    #                         mean)
    
    # Draw graph ========================================
    cat(sprintf("Drawing time graph to %s\n", OUTPUT_GRAPH))
    max_mutants <- nrow(motif[motif$runID==1,])
    if (DRAW_PERCENTAGE==TRUE){
        summary$killed <- summary$killed / max_mutants
    }
    colorPalette <- c("#D55E00", "#000000", "#D55E00", "#CC79A7")
    fontsize<-18
    # time_unit <- ifelse(GRANULARITY==60, "minutes", "seconds")
    # vline_time <- 10000 / GRANULARITY
    # time_breaks <- c(0, 2000,4000,6000,8000,10000)
    vline_time <- 10000 / GRANULARITY
    if (GRANULARITY==60){
        time_unit <- "minutes"
        
        time_breaks <- c(0, 50,100,150)
    }else{
        time_unit <- "seconds"
        time_breaks <- c(0, 2000,4000,6000,8000,10000)
    }
    
    draw_fontsize <- 6
    g <- ggplot()+
        geom_vline(xintercept = vline_time, linetype="dashed", color = "red", size=0.5, alpha=0.5) +
        geom_line(summary, mapping=aes(x=time, y=killed, color=approach, group=runID)) +
        xlab(sprintf("Execution time (%s)",time_unit))+
        scale_x_continuous(limits = c(0,MAX_TIME), labels=scales::comma_format(), breaks=time_breaks)+
        ylab("Killed mutants")+
        scale_color_manual(values=colorPalette, guide = guide_legend(nrow = 1))+
        # scale_fill_manual(values=colorPalette, guide = "none")+
        theme_bw()+
        theme(title=element_text(size=fontsize))+
        theme(axis.text=element_text(size=fontsize, color="black"),
              axis.title.y=element_text(size=fontsize, color="black"),
              axis.title.x=element_text(size=fontsize, color="black"),
              axis.line=element_line(colour = "black", size = 0.2, linetype = "solid"))+
        theme(axis.line.y.right = element_line(color = "red",  size = 0.2, linetype = "solid"),
              axis.ticks.y.right = element_line(color = "red"),
              axis.text.y.right = element_text(color = "red"),
              axis.title.y.right = element_text(color = "red"))+
        theme(legend.title=element_blank(), legend.text = element_text(size=fontsize),
              legend.box.background = element_rect(colour = "black"))
    # legend left-top
    # g <- g + theme(legend.justification=c(0,1), legend.position=c(0.01, 0.99))
    # legend right-top
    # g <- g + theme(legend.justification=c(1,1), legend.position=c(0.99, 0.99))
    # right-bottom
    # g <- g + theme(legend.justification=c(1,0), legend.position=c(0.99, 0.01))
    # left-bottom
    # g <- g + theme(legend.justification=c(0,0), legend.position=c(0.01, 0.01))
    g <- g + theme(legend.justification=c(0.5,0), legend.position=c(0.5, 0.02))
    if (DRAW_PERCENTAGE == FALSE){
        g<- g + scale_y_continuous(limits = c(0,max_mutants), labels=scales::comma_format())
    }
    else{
        g<- g + scale_y_continuous(limits = c(0, 1.0), labels=scales::percent)
    }
    
    print(g)
    
    # Save to file
    ggsave(OUTPUT_GRAPH, width=width, height=height)
    print("Finished")
}