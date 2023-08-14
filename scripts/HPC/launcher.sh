#!/bin/bash -l

################################################################
# SLURM parameters
################################################################
###### general options ##############################
#SBATCH -J LAUNCHER
#SBATCH --time=2-00:00:00
#SBATCH --mail-type=all
#SBATCH --mail-user=jaekwon.lee@uni.lu

###### job options ##############################
#SBATCH -N 1                         # Stick to a single node (all executions will be located in a node)
#SBATCH -c 1                         # --cpus-per-task=<ncpus>, if your application is using multithreading, increase the number of cpus(cores), otherwise just use 1
#SBATCH --mem-per-cpu=1GB            # Stick to maximum size of memory
#SBATCH --ntasks-per-node 1          # it is recommended to be the same to the total number of tasks for one parallel job, otherwise many node resources will be waisted
                                     # (HPC manager wants to reduce the number of nodes for one job)
###SBATCH --ntasks-per-node=28

###### performance option ########################
#SBATCH --qos normal
#SBATCH --partition=batch

###### logging option ##############################
#SBATCH -o %j-%x.out          # Logfile: <jobid>-<jobname>.out
#SBATCH -e %j-%x.out          # Logfile: <jobid>-<jobname>.out
#

###### For Debugging
echo "====== ENV VARIABLES ========================="
echo  "SLURM_CLUSTER_NAME = ${SLURM_CLUSTER_NAME}"
echo "SLURM_NODE_ALIASES = ${SLURM_NODE_ALIASES}"
echo "SLURM_NODEID       = ${SLURM_NODEID}"
echo "SLURM_NODELIST     = ${SLURM_NODELIST}"
echo "SLURM_JOBID        = ${SLURM_JOBID}"
echo "SLURM_JOB_NAME     = ${SLURM_JOB_NAME}"
echo "SLURM_MEM_PER_CPU  = ${SLURM_MEM_PER_CPU}"
echo "SLURM_MEM_PER_NODE = ${SLURM_MEM_PER_NODE}"

echo "============================================="
echo "CMD:"
echo $(basename $0) $@
#echo "========================= PRINT SLURM PARAMETERS ========================="
#printenv | grep SLURM
#echo "========================================================================="


################################################################
# Define functions
################################################################
# print the usage of this script
usage() {
    cat <<EOF

USAGE:
  $(basename $0) [-d] [-h] [--lines MIN:MAX] <INPUT_FILE> [SINGULARITY_IMAGE]
  This script executes commands sequentially that are at the lines [MIN, MAX] in the <INPUT_FILE>.
  If the [SINGULARITY_IMAGE] is provided, the commands are executed in the singularity container.
  The default singularity options are the following:
      ${SINGULARITY_PARAMS}
  If you want to change the options, please fix this scripts.

OPTIONS
  -h --help:  show usage of this script
  -d --dry :  dry run mode
  --lines  :  the minimum and maximum line numbers with a delimiter ":", Available formats: "1", "1:10", ":10", "20:"

EXAMPLES
  \$ $(basename $0) --lines 10 preprocess.cmd
      The line 10 in the preprocess.cmd will be executed.

  \$ $(basename $0) --lines 10 preprocess.cmd containers/ubuntu.sif
      Assuming the command at the line 10 in the preprocess.cmd is "python hello_world.py",
      the above example is the same to executing the following command:
      "singularity exec ${SINGULARITY_PARAMS} containers/ubuntu.sif python hello_world.py"
EOF
}

# read a line from a specified file
read_line_from_file(){
  local input_file=$1
  local line_num=$2
  line_num=$(expr $line_num + 0)  # string to integer
  line=`sed -n "${line_num}p" ${input_file}`
  # trim white spaces
  echo ${line} | sed 's/ *$//g'
}

# read a command
start(){
  start=$(date +%s.%N)
  echo ""
  echo "################################################"
  if [[ "${SINGULARITY_IMAGE}" != "" ]]; then
      echo "### Singulairty    : singularity exec ${SINGULARITY_PARAMS} ${SINGULARITY_IMAGE}"
  fi
  echo "### Starting timestamp (s): ${start}"
  echo "################### START ######################"
  echo ""
}

# read a command
finish() {
  end=$(date +%s.%N)
  runtime=$(echo $end $start | awk '{printf "%.3f",$1 - $2}') # calculated elapsed time

  cat <<EOF

#################### END #######################
### Ending timestamp (s): ${end}
### Elapsed time     (s): ${runtime}
################################################


EOF
}

################################################################
# Parse the command-line argument
################################################################
{
CMD_PREFIX=
MIN=1
MAX=
INPUT_FILE=
SINGULARITY_IMAGE=
SINGULARITY_PARAMS="--bind ./:/expr -H /expr"
LOAD_SINGULARITY=FALSE

# remaining parameters
PARAMETERS=
while [ $# -ge 1 ]; do
    case $1 in
        -h | --help) usage; exit 0;;
        -d | --dry) CMD_PREFIX=echo;;
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
read -a PARAMS <<< "${PARAMETERS}"                 # Read the split words into an array based on comma delimiter

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


################################################################
# Define modules that requires to execute an experiment
################################################################
{
if [[ "${SINGULARITY_IMAGE}" != "" || "${LOAD_SINGULARITY}" == "TRUE" ]]; then
    # load the module when this script is executed in a HPC computing node
    if [[ "$ULHPC_CLUSTER" != "" ]]; then
        module purge || print_error_and_exit "Unable to find the module command - you're NOT on a computing node"
        module load tools/Singularity/3.8.1
        echo "Loaded singularity module"
    fi

    # Error check of the input file
    check=`command -v singularity`    # get the location of the command
    if [[ "${check}" == "" ]]; then
        echo "Cannot find singularity command. Please install singularity application."
        exit 1
    fi
fi
}



################################################################
# Commands script
################################################################
# set MAX variable if it is not specified
if [ "${MAX}" == "" ]; then
    # count the number of lines in the input file
    MAX=`grep -c ^ ${INPUT_FILE}`

    # check the last line is just a blank line (if then, reduce one line)
    LAST_CMD=`read_line_from_file ${INPUT_FILE} ${MAX}`
    if [[ "${LAST_CMD}" == "" ]]; then
        MAX=$(($MAX - 1))
    fi
fi



# execute command
start;
for ((LINE_NO=${MIN}; LINE_NO<=${MAX}; LINE_NO++)); do {

    # get command from the input file
    CMD=`read_line_from_file ${INPUT_FILE} ${LINE_NO}`

    # Error check of the line number
    if [ "${CMD}" == "" ]; then
      echo "There is no command. Please check the line \`${LINE_NO}\` in the input file \`${INPUT_FILE}\` "
      exit 1
    fi

    echo ""
    echo "### Task command   : ${CMD}"
    echo ""
    if [[ "${SINGULARITY_IMAGE}" != "" ]]; then
      ${CMD_PREFIX} singularity exec ${SINGULARITY_PARAMS} ${SINGULARITY_IMAGE} ${CMD}
    else
      ${CMD_PREFIX} ${CMD}
    fi
    RETURN_CODE=$?
    if [[ "${RETURN_CODE}" != "0" ]]; then break; fi

} done
finish;
echo "Done (return code: ${RETURN_CODE})"

