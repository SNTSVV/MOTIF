usage <- "
This script is for generating a graph and talbe for the number of killed mutants over time
Usage:
    $ Rscript <script> <GRANULARITY> <MAX_TIME> <INPUT_FILE1> <INPUT_FILE2>
Example:
    Rscript analysis_graph_RQ2.R 60 180 ./case_studies/LIBU/_exp0418/summary_10ks.csv ./case_studies/MLFS/_exp0413/summary_10ks.csv
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
{
    if (length(ENV$PARAMS) < 4) { help("Not enough parameters") }
    if (is.na(as.numeric(ENV$PARAMS[1]))) { help("Wrong input at the 1st parameter")  }
    if (is.na(as.numeric(ENV$PARAMS[2]))) { help("Wrong input at the 2nd parameter")  }
    
    GRANULARITY <- as.numeric(ENV$PARAMS[1]) # 60 seconds # graph x-axis time unit
    MAX_TIME <- as.numeric(ENV$PARAMS[2])    # AFL execution time in seconds
    INPUT_PATH1 <- ENV$PARAMS[3]              # summary file
    INPUT_PATH2 <- ENV$PARAMS[4]              # summary file
    
    # additional variables
    OUTPUT_GRAPH <- file.path(dirname(INPUT_PATH1), sprintf("%s_merge_timegraph.pdf", basename_without_ext(INPUT_PATH1)))
    width <- 6                               # graph width in inch
    height <- 3                              # graph height in inch
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
    # load file for LIBU
    data <- read.csv(INPUT_PATH1, header=TRUE)
    data <- data.frame(MutantID=data$Mutant.ID, RunID=data$Run.ID,Result= data$Result, CrashedTime=data$Crashed.Time..s.)
    max_mutants <- nrow(data[data$RunID==1,])
    
    summary_libu <- make_timetable(data, GRANULARITY, MAX_TIME, direction="vertical")
    summary_libu <- cbind(approach="LIBU", summary_libu, killed.percent= summary_libu$killed / max_mutants)
    
    # load file for MLFS
    data <- read.csv(INPUT_PATH2, header=TRUE)
    data <- data.frame(MutantID=data$Mutant.ID, RunID=data$Run.ID,Result= data$Result, CrashedTime=data$Crashed.Time..s.)
    max_mutants <- nrow(data[data$RunID==1,])
    
    summary_mlfs <- make_timetable(data, GRANULARITY, MAX_TIME, direction="vertical")
    summary_mlfs <- cbind(approach="MLFS", summary_mlfs, killed.percent= summary_mlfs$killed / max_mutants)
    summary_mlfs$runID <- summary_mlfs$runID + 100
    
    summary <- rbind(summary_mlfs, summary_libu)
    summary$approach <- factor(summary$approach, levels=c("MLFS", "LIBU"))
    summary$runID <- as.integer(summary$runID)
    # head(summary)
    # summary$approach

    # Draw graph ========================================
    cat(sprintf("Drawing time graph to %s\n", OUTPUT_GRAPH))
    colorPalette <- c("#D55E00", "#000000", "#D55E00", "#CC79A7")
    fontsize<-18
    draw_fontsize <- 6
    bar_width <- 4
    vline_time <- 10000 / GRANULARITY
    if (GRANULARITY==60){
        time_unit <- "minutes"
        time_breaks <- c(0, 50,100,150)
    }else{
        time_unit <- "seconds"
        time_breaks <- c(0, 2000,4000,6000,8000,10000)
        summary <- summary[(summary$time%%100)==0,]
    }
    summary <- summary[summary$time <= 10000 , ]
    
    g <- ggplot()+
        geom_vline(xintercept = vline_time, linetype="dashed", color = "red", size=0.5, alpha=0.5) +
        geom_line(summary, mapping=aes(x=time, y=killed.percent, linetype=approach, group=runID)) +
        # geom_bar(avgsKilled, mapping=aes(x=time, y= killed,  fill=approach), alpha=0.5,
        #          stat='identity', width = bar_width, position=position_dodge(width = bar_width), hjust=-bar_width) +
        xlab(sprintf("Execution time (%s)", time_unit))+
        scale_x_continuous(limits = c(0,MAX_TIME), labels = scales::comma_format(), breaks=time_breaks) +
        ylab("Killed mutants")+
        scale_y_continuous(limits = c(0, 1.0), labels=scales::percent)+
        # scale_color_manual(values=colorPalette, guide = guide_legend(nrow = 1))+
        scale_linetype_manual(values=c("solid", "dashed"), guide = guide_legend(nrow = 1))+
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
    
    # print(g)
    
    #
    # g <- ggplot()+
    #     geom_vline(xintercept = 166.7, linetype="dashed", color = "red", size=0.5, alpha=0.5) +
    #     geom_line(summary, mapping=aes(x=time, y=killed.percent, color=approach, group=runID)) +
    #     xlab("Execution time (minutes)")+
    #     scale_x_continuous(limits = c(0,max_time), labels = scales::comma_format()) +
    #     # ylab("Number of killed mutants")+
    #     # scale_y_continuous(limits = c(0,max_mutants), labels=scales::comma_format())+
    #     ylab("Killed mutants")+
    #     scale_y_continuous(limits = c(0, 1.0), labels=scales::percent)+
    #     scale_color_manual(values=colorPalette)+
    #     theme_bw()+
    #     theme(title=element_text(size=fontsize))+
    #     theme(axis.text=element_text(size=fontsize, color="black"),
    #           axis.title.y=element_text(size=fontsize, color="black"),
    #           axis.title.x=element_text(size=fontsize, color="black"),
    #           axis.line=element_line(colour = "black", size = 0.2, linetype = "solid"))+
    #     theme(axis.line.y.right = element_line(color = "red",  size = 0.2, linetype = "solid"),
    #           axis.ticks.y.right = element_line(color = "red"),
    #           axis.text.y.right = element_text(color = "red"),
    #           axis.title.y.right = element_text(color = "red")) +
    #     theme(legend.title=element_blank(), legend.text = element_text(size=fontsize), legend.position="none")
    print(g)
    #
    # Save to file
    ggsave(OUTPUT_GRAPH, width=width, height=height)
    print("Finished")
}
