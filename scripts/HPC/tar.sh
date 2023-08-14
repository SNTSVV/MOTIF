#!/bin/bash -l

################################################################
# SLURM parameters
################################################################
###### general options ##############################
#SBATCH -J TAR_SH
#SBATCH --time=10:00:00
#SBATCH --mail-type=all

###### job options ##############################
#SBATCH -N 1                         # Stick to a single node (all executions will be located in a node)
#SBATCH -c 1                         # --cpus-per-task=<ncpus>, if your application is using multithreading, increase the number of cpus(cores), otherwise just use 1
#SBATCH --mem-per-cpu=16GB           # Stick to maximum size of memory
#SBATCH --ntasks-per-node=1          # it is recommended to be the same to the total number of tasks for one parallel job, otherwise many node resources will be waisted
                                     # (HPC manager wants to reduce the number of nodes for one job)
###### performance option ########################
#SBATCH --qos normal
#SBATCH --partition=batch

###### logging option ##############################
#SBATCH -o %j-%x.out          # Logfile: <jobid>-<jobname>.out
#SBATCH -e %j-%x.out          # Logfile: <jobid>-<jobname>.out


CMD_PREFIX=
REMOVE=FALSE
ZIP=FALSE
EXTRACT_FILES=FALSE

usage(){
    echo ""
    echo "This script generates archive files for each sub-folder in the <target path>"
    echo "         OR extracts files from each archive file in the <target path>"
    echo "Files in the root of <target path> would not be affected by this command."
    echo "USAGES:"
    echo "   \$ $0 [-r] [-z] [-x] <target path>"
    echo "   e.g.)  \$ $0 ./expr/test"
    echo "          If the <target path> has two sub-folders, 'F1' and 'F2',"
    echo "          they are going to be archived into 'F1.tar' and 'F2.tar' in the './expr/test'."
    echo "OPTIONS:"
    echo "-r   remove sub-folders after making them archives, it doesn't work for the option '-x'"
    echo "-z   apply 'z' option to the 'tar' command; it makes '*.tar.gz' file by compressing files in a sub-folder"
    echo "-x   extract files that end with 'tar' or 'tar.gz' into each folder"
    echo "     e.g.)  \$ $0 -x ./expr/test"
    echo "            If the <target path> has two tar files, F1.tar and F2.tar,"
    echo "            they are going to be extracted into each sub-folder, F1 and F2 in the ./expr/test."
    echo "            Note that this command may not work correctly if the tar files made in a different way."
    echo ""
    exit 1
}
make_tar(){
    local target=$1
    local compress=$2

    if [[ "$#" == "3" ]]; then
      local working_dir=$3
      cd $working_dir
    fi

    if [[ "${compress}" == "TRUE" ]]; then
      # make "*.tar.gz" file
      echo "tar czf ${target}.tar.gz ${target} ..."
      ${CMD_PREFIX} tar czf ${target}.tar.gz ${target}
    else
      # make "*.tar" file
      echo "tar cf ${target}.tar ${target} ..."
      ${CMD_PREFIX} tar cf ${target}.tar ${target}
    fi

    if [[ "$#" == "3" ]]; then
        # return where we were (without echo, by "~")
        cd ~-
    fi
}
extract_tar(){
    local tarfile=$1
    local compress=$2

    if [[ "$#" == "3" ]]; then
      local working_dir=$3
      mkdir -p $working_dir
      cd $working_dir
    fi

    if [[ "${compress}" == "TRUE" ]]; then
      # extract files from "*.tar.gz"
      echo "tar xzf ${tarfile} ..."
      ${CMD_PREFIX} tar czf ${tarfile}
    else
      # extract files from "*.tar"
      echo "tar xf ${tarfile} ..."
      ${CMD_PREFIX} tar xf ${tarfile}
    fi

    if [[ "$#" == "3" ]]; then
        # return where we were (without echo, by "~")
        cd ~-
    fi
}
remove_original_data(){
    local target=$1
    echo "rm -rf ${target} ..."
    ${CMD_PREFIX} rm -rf ${target}
}


get_extract_dir_name(){
  # return empty string if the tar file contains only the folder that is the same name to the tar file
  # otherwise it returns the name of the tar file
  # param $1: tarfile_name
echo "$1" | awk '
    function only_filename(file) {
       n = split(file, a, "/");
       n = split(a[n], b, ".");
       name="";
       for (i=1; i<n; i++){
           name = name b[i];
       }
       return name;
   }
   {
    # level_idx=$2
    cmd = "tar -tf" $1
    result_array = ""

    ###### Execute $cmd and process each result line
    while (cmd | getline line) {
        #
        n=split(line,paths,"/");   # split $line and into an array paths
        if (paths[1] == ".") target=paths[2];
        else target=paths[1];

        ##### compare the selected directory is in the result_array
        nDirs = split(result_array, dirs, "|") # split result_array and into an array dirs
        flag="FALSE";
        for(i=1; i<=nDirs; i++){ if (target==dirs[i]) { flag="TRUE"; break; } }

        ##### add target in the result_array
        if (flag=="FALSE"){
            if (result_array=="") { result_array = target}
            else{ result_array = result_array "|" target }
        }
    }
    close(cmd);

    ##### check whether this file need to create the folder or not
    fname = only_filename($1)
    nDirs = split(result_array, dirs, "|") # split result_array and into an array dirs
    if ( nDirs == 1 && fname == dirs[1]){
            print "";  # do not need directory
    }
    else{
        print fname;
    }

}'
}





############################################################
# Dealing with arguments
############################################################
{
# Check the number of arguments
if [[ "$#" == "0" ]]; then
  usage
fi

# Parsing the command-line arguments
while [ $# -ge 1 ]; do
    case $1 in
        -h | --help) echo "input parameter error"; exit 0;;
        -d | --noop | --dry-run) CMD_PREFIX=echo;;
		-r | --remove) REMOVE=TRUE;;
		-z | --zip) ZIP=TRUE;;
    -x | --extract) EXTRACT_FILES=TRUE;;
        *) TARGET_FOLDER="$*"; break; ;;
    esac
    shift;
done

# check the necessary arguments
if [[ "${TARGET_FOLDER}" == "" ]]; then
	usage
fi

# check the number of TARGET_FOLDER list (it should be 1)
#IFS=' ' eval 'testvalue=(${TARGET_FOLDER})'
TEST_VALUE=$(echo ${TARGET_FOLDER} | sed 's/ *$//g') # trim parameters
IFS=' '                                              # Set a space as delimiter
read -a SPLITS <<< "${TEST_VALUE}"                   # Read the split words into an array based on comma delimiter
if [[ "${#SPLITS[@]}" != "1" ]]; then
    echo "ERROR: $0 takes only one target folder"
    echo ""
    usage
fi
}




############################################################
# main code
############################################################
echo "Working dir: $TARGET_FOLDER"
echo ""

if [[ "${EXTRACT_FILES}" == "TRUE" ]]; then
    # extract tar file
    for item_path in ${TARGET_FOLDER}/*; do
        # PASS if the "base" is not a file
        if [ ! -f "${item_path}" ] ; then continue; fi

        # get basename of the item path
        base=`(basename ${item_path})`
        extension="${base##*.}"
        if [[ "${extension}" != "tar" && "${extension}" != "gz" ]]; then continue; fi

        # set directory name
        dirname=`get_extract_dir_name $item_path`
        targetfile=`realpath $item_path`
        # extract the "$base" tar file into the target directory (if the tarfile requires to create sub-folder, it makes)
        if [[ "$dirname" == "" ]]; then
            extract_tar $targetfile ${ZIP} ${TARGET_FOLDER}
        else
            extract_tar $targetfile ${ZIP} ${TARGET_FOLDER}/${dirname}
        fi

        # remove if the option is active
        if [[ "${REMOVE}" == "TRUE" ]]; then
            remove_original_data ${item_path}
        fi
    done
else
    # make tar file
    for item_path in ${TARGET_FOLDER}/*; do
        # PASS if the "base" is a file
        if [ -f "${item_path}" ] ; then continue; fi


        base=`(basename ${item_path})`    # get basename of the item path

        # compress the "$base" directory into "$base".tar or "$base".tar.gz
        make_tar $base ${ZIP} ${TARGET_FOLDER}

        # remove if the option is active
        if [[ "${REMOVE}" == "TRUE" ]]; then
            remove_original_data ${item_path}
        fi
    done

    # show the archiving results
    nFiles=`(find ${TARGET_FOLDER} -type f | wc -l)`
    echo ""
    echo "The folder $TARGET_FOLDER has $nFiles files."
    echo "Done."
fi


