#!/bin/bash -l

################################################################
# SLURM parameters
################################################################
###### general options ##############################
#SBATCH -J PARALLEL
#SBATCH --time=2-00:00:00
#SBATCH --mail-type=all
#SBATCH --mail-user=jaekwon.lee@uni.lu

###### job options ##############################
#SBATCH -N 1                         # Stick to a single node (all executions will be located in a node)
#SBATCH -c 1                         # --cpus-per-task=<ncpus>, if your application is using multithreading, increase the number of cpus(cores), otherwise just use 1
#SBATCH --mem-per-cpu=1GB            # Stick to maximum size of memory
#SBATCH --ntasks-per-node=1          # it is recommended to be the same to the total number of tasks for one parallel job, otherwise many node resources will be waisted
                                     # (HPC manager wants to reduce the number of nodes for one job)
###SBATCH --ntasks-per-node=28

###### performance option ########################
#SBATCH --qos normal
#SBATCH --partition=batch
###SBATCH --partition=interactive

###### logging option ##############################
#SBATCH -o %j-%x.out          # Logfile: <jobid>-<jobname>.out
#SBATCH -e %j-%x.out          # Logfile: <jobid>-<jobname>.out
#

############################
# In the documentation, the following variables exist for each -o, -e parameters.
# But it actually does not have any value when the script is executing.
# So this script takes one parameter -l to save the execution logs of each instance inside of a directory
# echo SBATCH_OUTPUT=$SBATCH_OUTPUT
# echo SBATCH_ERROR=$SBATCH_ERROR
# See the document:
#     https://slurm.schedmd.com/sbatch.html


#############################################################################
# Slurm launcher for embarrassingly parallel problems combining srun and GNU
# parallel within a single node to runs multiple times the command ${TASK}
# within a 'tunnel' set to execute no more than ${SLURM_NTASKS} tasks in
# parallel.
#
# Resources:
# - https://www.marcc.jhu.edu/getting-started/additional-resources/distributing-tasks-with-slurm-and-gnu-parallel/
# - https://rcc.uchicago.edu/docs/tutorials/kicp-tutorials/running-jobs.html
# - https://curc.readthedocs.io/en/latest/software/GNUParallel.html
#############################################################################

###### For Debugging
echo "CMD:"
echo $(basename $0) $@
# echo "========================= PRINT SLURM PARAMETERS ========================="
#printenv | grep SLURM
#printenv | grep SBATCH
# echo "========================================================================="


################################################################
# Define functions
################################################################
read_line_from_file(){
  local input_file=$1
  local line_num=$2
  line_num=$(expr $line_num + 0)  # string to integer
  line=`sed -n "${line_num}p" ${input_file}`
  # trim white spaces
  echo ${line} | sed 's/ *$//g'
}

print_error_and_exit() {
  printf "\n *** ERROR *** \n$*\n\n"; exit 1;
}

usage() {
    cat <<EOF

USAGE:
    $(basename $0) [--log LOG_PATH] [--lines MIN:MAX] <INPUT_FILE> [SINGULARITY_IMAGE]
    This command is used for the sbatch command to execute multiple commands from <INPUT_FILE> in parallel.
    Each command will be executed in the [SINGULARITY_IMAGE] environment if it is provided.

OPTIONS:
  -d --dry :   dry run mode
  -l --log :   (optional) log path for the parallel executions, if not specified, we use a default value defined above
  --lines  :   the minimum and maximum line numbers with a delimiter ":", Available formats: "1", "1:10", ":10", "20:"

COMMAND EXAMPLES:
    $(basename $0) --lines 1:10 ./preprocess.cmd
          The lines from 1 to 10 in preprocess.cmd will be executed in parallel.
    $(basename $0) --lines 1:10 ./preprocess.cmd containers/ubuntu.sif
          The lines from 1 to 10 in preprocess.cmd will be executed in parallel on the containers/ubuntu.sif container.
    sbatch -o userlogs/%j-%x.out -e userlogs/%j-%x.out $(basename $0) -l userlogs/%j-%x.out --lines 1:10 ./preprocess.cmd
        If you want to store logs to user-defined folder, the -l option should be set like the same log with sbatch

SBATCH EXAMPLES:
  Within a passive job
      (access)$> sbatch --ntasks-per-node 4 $0
  Within a passive job, using several cores (6) per tasks
      (access)$> sbatch --ntasks-per-socket 2 --ntasks-per-node 4 -c 6 $0
  Within a passive job, using large memory per tasks (we have 10 tasks)
      sbatch --time 2-00:00:00 --ntasks-per-node 10 --mem-per-cpu=16G $0

  Get the most interesting usage statistics of your jobs <JOBID> (in particular
  for each job step) with:
     ssacct -j <JOBID> --format User,JobID,Jobname,partition,state,time,elapsed,MaxRss,MaxVMSize,nnodes,ncpus,nodelist,ConsumedEnergyRaw
  Get the interactive mode shell for the running job:
     sjoin -j <JOBID>

EOF
}

start(){
  start=$(date +%s)
  cat <<EOF
################################################
### Task command   : ${TASK_CMD}
### SRUN option    : ${SRUN_CMD}
### Parallel option: ${PARALLEL_CMD}
### Range          : [${MIN}, ${MAX}]
### Starting timestamp (s): ${start}
################### START ######################

EOF
}

finish() {
  end=$(date +%s)
  cat <<EOF

#################### END #######################
### Ending timestamp (s): ${end}
### Elapsed time     (s): $(($end-$start))
################################################
##############################################################################
Beware that the GNU parallel option --resume makes it read the log file set by
--joblog (i.e. logs/state*.log) to figure out the last unfinished task (due to the
fact that the slurm job has been stopped due to failure or by hitting a walltime
limit) and continue from there.
In particular, if you need to rerun this GNU Parallel job, be sure to delete the
logfile logs/state*.parallel.log or it will think it has already finished!
##############################################################################

EOF
}


##############################################################################
##############################################################################
##############################################################################
# Use the UL HPC modules
if [ -f  /etc/profile ]; then
    .  /etc/profile
fi

##############################################################################
# Dependency check
##############################################################################
# Default setting
LAUNCHER_PATH="./launcher.sh"

# Set the correct path of Launcher
# - the Get parallel.sh path from the current working directory and set the path to the launcher path
if [ -n $SLURM_JOB_ID ] ; then
    ORIGIN_PATH="$(scontrol show job $SLURM_JOB_ID | awk -F= '/Command=/{print $2}')"
    ORIGIN_PATH="$(echo $ORIGIN_PATH | awk -F' ' '{print $1}')"
else
    ORIGIN_PATH=$(realpath $0)
fi
LAUNCHER_PATH="`(dirname ${ORIGIN_PATH})`/${LAUNCHER_PATH}"


################################################################
# Parse the command-line argument
################################################################
{
CMD_PREFIX=
LOG_PATH=%j-%x.log
LINES=
MIN=1
MAX=
INPUT_FILE=
SINGULARITY_IMAGE=
LOAD_SINGULARITY=FALSE

# remaining parameters
PARAMETERS=

# Parse the command-line argument
while [ $# -ge 1 ]; do
    case $1 in
        -h | --help) usage; exit 0;;
        -d | --dry) CMD_PREFIX=echo;;
        -l | --log) LOG_PATH=$2; shift;;
        --lines) LINES=$2; shift;;
        --min) MIN=$2; shift;;
        --max) MAX=$2; shift;;
        --load) LOAD_SINGULARITY=TRUE;;
        *) PARAMETERS="$*"; break; ;;
    esac
    shift;
done


# split remaining parameters and into each corresponding parameter
PARAMETERS=`echo ${PARAMETERS} | sed 's/ *$//g'`   # trim parameters
IFS=' '                                            # Set a space as delimiter
read -a PARAMS <<< "${PARAMETERS}"              # Read the split words into an array based on comma delimiter

# Assign each parameters to each variable
INPUT_FILE=${PARAMS[0]}
SINGULARITY_IMAGE=${PARAMS[1]}
}

################################################################################
# Error check
################################################################################
{
if [[ "${INPUT_FILE}" == "" ]]; then
    echo "ERROR: NOT provided the input file parameter; INPUT_FILE is necessary"
    exit 1
fi

# Error check of the input file
if [[ ! -f "${INPUT_FILE}" ]]; then
  echo "Cannot find the input file \`${INPUT_FILE}\`. Please check the variable."
  exit 1
fi

if [[ "${SINGULARITY_IMAGE}" == "" ]]; then
    echo "WARNING: This command will be executed on the host OS"
fi
# Error check of the SINGULARITY IMAGE file
if [[ "${SINGULARITY_IMAGE}" != "" && ! -f "${SINGULARITY_IMAGE}" ]]; then
  echo "Cannot find the singularity image file \`${SINGULARITY_IMAGE}\`. Please check the variable."
  exit 1
fi
}

# setting MIN and MAX
# split $LINES into two part with delimiter ":"
if [[ "$LINES" != "" ]]; then {
    ARR=(`echo ${LINES} | sed -e 's/:/ /g'`)
    minV=${ARR[0]}
    maxV=${ARR[1]}

    is_positive_int(){ [ "$1" -gt 0 ] 2>/dev/null && echo 1 || echo 0; }

    ###
    if [[ "${LINES}" == *: ]]; then
        if [[ $(is_positive_int ${minV}) -eq 0 ]] ; then
            echo "'${LINES}' is not a valid value, it should be a positive integer or positive integers with : delimiter."
            exit 1
        fi
        maxV=""
    elif [[ "${LINES}" == :* ]]; then
        minV=1
        maxV=${ARR[0]}
        if [[ $(is_positive_int ${maxV}) -eq 0 ]] ; then
            echo "'${LINES}' is not a valid value, it should be a positive integer or positive integers with : delimiter."
            exit 1
        fi
    else
        if [[ "${maxV}" == "" ]]; then maxV=${minV}; fi

        if [[ $(is_positive_int ${minV}) -eq 0 || $(is_positive_int ${maxV}) -eq 0 ]] ; then
            echo "'${LINES}' is not a valid value, it should be a positive integer or positive integers with : delimiter."
            exit 1
        fi

        if [ ${minV} -gt ${maxV} ]; then
            echo "MIN=${minV} should be less than or equal to MAX=${maxV}"
            exit 1
        fi
    fi

    MIN=$((${minV} + 0))
    MAX=$((${maxV} + 0))
    echo "MIN_LINE_NO=${MIN}"
    echo "MAX_LINE_NO=${MAX}"
} fi

################################################################################
# Prepare log path
################################################################################
{
# create log path for parallel executions
# we create a folder with the log path without extension
LOG_PATH=${LOG_PATH//%j/${SLURM_JOB_ID}}
LOG_PATH=${LOG_PATH//%x/${SLURM_JOB_NAME}}
DIR_PATH=$(dirname ${LOG_PATH})                # get dir path
FILENAME=$(basename ${LOG_PATH})               # get only filename
FILENAME="${FILENAME%.*}"                   # remove ext from the filename
LOG_PATH="${DIR_PATH}/${FILENAME}"

echo "Generate log path: ${LOG_PATH}"
mkdir -p ${LOG_PATH}
}

################################################################
# Node execution settings
################################################################
{
# the --exclusive to srun makes srun use distinct CPUs for each job step
# -N1 -n1 allocates a single core to each task - Adapt accordingly
# -N : minimum of nodes, should be in parallel
# -n : number of tasks, should be in parallel
SRUN="srun --exclusive -N 1 -n 1 --cpus-per-task=${SLURM_CPUS_PER_TASK:=1} --mem-per-cpu=${SLURM_MEM_PER_CPU} --cpu-bind=cores"

}

################################################################
# Parallel settings
################################################################
{
### GNU Parallel options
# --delay .2 prevents overloading the controlling node
# -j is the number of tasks parallel runs so we set it to $SLURM_NTASKS
# --joblog makes parallel create a log of tasks that it has already run
# --resume makes parallel use the joblog to resume from where it has left off
#   the combination of --joblog and --resume allow jobs to be resubmitted if
#   necessary and continue from where they left off
PARALLEL="parallel --delay .2 -j ${SLURM_NTASKS} --joblog ${LOG_PATH}/parallel.log" # --resume"

# Set parallel option for linking parallel parameters
#    parallel echo {1} {2} ::: 1 2 3 ::: a b c
#    parallel --link echo {1} {2} ::: 1 2 3 ::: a b c
# if you use "--link" total number of parallel tasks will be 3.
# if you do not use it, total number of parallel tasks will be 9 (= 3 * 3).
# parallel version is less than 20190000: the parameter name is --xapply
version=`parallel --version | grep "^GNU" | grep "[0-9]" | awk '{print $3}'`
if (( ${version} > 20190000 )); then
	PARAMETER_LINK_OPTION="--link"
else
	PARAMETER_LINK_OPTION="--xapply"
fi

# this runs the parallel command you want, i.e. running the
# script ${TASK} within a 'tunnel' set to run no more than ${SLURM_NTASKS} tasks
# in parallel
# See 'man parallel'
# - Reader's guide: https://www.gnu.org/software/parallel/parallel_tutorial.html
# - Numerous (easier) tutorials are available online. Ex:
#   http://www.shakthimaan.com/posts/2014/11/27/gnu-parallel/news.html
#
}

##################################################################
# working process
##################################################################
# set MAX variable if it is not specified
if [ "${MAX}" == "" ]; then
  # count the number of lines in the input file
  MAX=`grep -c ^ ${INPUT_FILE}`
  LAST_CMD=`read_line_from_file ${INPUT_FILE} ${MAX}`
  if [[ "${LAST_CMD}" == "" ]]; then
    MAX=$(($MAX - 1))
  fi
fi


# make arguments for parallel
# prepare 5 digits number padding 0
LINE_STR_PARAMS=
LINE_NUM_PARAMS=
for ((cnt=${MIN}; cnt<=${MAX}; cnt++)); do
  NAME=$(printf '%05d' "${cnt}")
	LINE_STR_PARAMS="${LINE_STR_PARAMS} ${NAME}"
	LINE_NUM_PARAMS="${LINE_NUM_PARAMS} ${cnt}"
done

# Showing the number of tasks
NUM_TASKS=$((${MAX}-${MIN}+1))
echo "Work ${NUM_TASKS} tasks on the HPC nodes!!"


# Assemble commands
PARALLEL_CMD="${PARALLEL} ${PARAMETER_LINK_OPTION}" # --colsep ' '"
SRUN_CMD="${SRUN} -e ${LOG_PATH}/{1}.out -o ${LOG_PATH}/{1}.out"
if [[ "${SINGULARITY_IMAGE}" != "" ]]; then
    TASK_CMD="${LAUNCHER_PATH} --lines {2} ${INPUT_FILE} ${SINGULARITY_IMAGE}"
else
    if [[ "${LOAD_SINGULARITY}" == "TRUE" ]]; then
        TASK_CMD="${LAUNCHER_PATH} --load --lines {2} ${INPUT_FILE}"
    else
        TASK_CMD="${LAUNCHER_PATH} --lines {2} ${INPUT_FILE}"
    fi
fi

# Execute parallel works!
start;
${CMD_PREFIX} ${PARALLEL_CMD} ${SRUN_CMD} ${TASK_CMD} ::: ${LINE_STR_PARAMS} ::: ${LINE_NUM_PARAMS}
finish;
