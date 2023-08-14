# Getting started of MOTIF

## Download Git repository
```shell
# Download this pipeline repository into `MOTIF` directory.
# We assume the directory `MOTIF` is the base directory when the command starts with $ from now.
$ git clone https://github.com/SNTSVV/MOTIF.git MOTIF  
```

## Repository description
* `case_studies`: directory expected to contain case study data
* `containers`: directory containing virtual machine images and its environment setting
* `pipeline`: directory containing main source codes for the MOTIF pipeline
* `scripts`: directory containing scripts for supporting experiments
* `test`: directory containing test cases of MOTIF
* `tools`: directory containing scripts for supporting experiments (managing result files)
* `config.py`: default configuration file
* `run.py`: main entry point for a mutant
* `run_list.py`: main entry point for a list of mutants
* `Vagrantfile`: configuration file for the vagrant box (for Windows and Mac OS users)


## Pre-requisition
We use Singularity to provide the same environment for all the users.
Users who work on Linux operating systems can install Singularity directly on their machines.
But Windows and Mac OS users need to rely on a Linux virtual machine since Singularity only supports Linux.
SyLabs, which has developed Singularity, provides Vagrant boxes with Singularity pre-installed on Linux.
We recommend you install Vagrant.
For the installation, please follow the guidelines from [the official website](https://docs.sylabs.io/guides/3.8/admin-guide/installation.html).

Note that we used Singularity 3.8 CE version since HPC uses this version.


## Connecting to vagrant box (for Windows or Mac OS users)
* We provide all the configuration to set up the vagrant instance for Singularity in `Vagrantfile`
* Please use the commands below in the root repository of MOTIF
```shell
# The command below creates a virtual machine instance according to the Vagrantfile based on the root repository.
# This will bind automatically the root repository to the directory /vagrant inside of the container
$ vagrant up 
# Connect into the the vagrant box instance
$ vagrant ssh
# Move to the bound directory, which is sharing between vagrant container and the host OS
[vagrant]$ cd /vagrant 
```
> Now, we assume that you are in the directory /vagrant in the vagrant instance, which is the same as the root repository of the MOTIF.


## Preparing AFL++
* The commands below will generate necessary binary files for MOTIF, `afl-gcc` and `afl-fuzz`.
```shell
# install AFL++
$ git clone https://github.com/AFLplusplus/AFLplusplus AFL++
$ cd AFL++
AFL++$ make clean
AFL++$ make
```
* We provide AFL++ that we used for our experiments.
```shell
# You can find the archive file at the following URL: https://figshare.com/articles/conference_contribution/Fuzzing_for_CPS_Mutation_Testing/22693525
# Please use the following commands to download and extract:
$ wget -O AFL++-4.05a.tar https://figshare.com/ndownloader/files/40299817
$ tar xf AFL++-4.05a.tar
```


## Preparing singularity container
* We provide the definition file `./containers/singularity_motif.def` containing commands to install all the dependencies and environment
```shell
# Create a singularity container
$ sudo singularity build ./containers/motif_default.sif ./containers/singularity_motif.def

# You can test the singularity image with the following commands:
# Please note that we are binding the root repository in the directory `/expr` in the container.  
# Connect a shell in the singularity container
$ singularity shell --bind /vagrant:/expr -H /expr ./containers/motif_default.sif  
# Execute a command in the singularity container
$ singularity exec --bind /vagrant:/expr -H /expr ./containers/motif_default.sif pwd
```
* We also provide pre-built singularity image in a [Figshare page](https://figshare.com/articles/conference_contribution/Fuzzing_for_CPS_Mutation_Testing/22693525).
```shell
# You can just download the singularity image into `containers` directory using the following command: 
$ wget -O containers/motif_default.sif https://figshare.com/ndownloader/files/41974680 
```


## Preparing target subjects
We provide the subject data: ASN1 and MLFS, which are open-source. Each subject archive contains software under test, mutants generated by MASS, target live mutants, and configuration file for MOTIF.
The commands below will download the data and extract them into the `case_studies` directory.
```shell
# for MLFS
$ wget -O case_studies/MLFS.tar https://figshare.com/ndownloader/files/41974686
$ tar -xf case_studies/MLFS.tar -C case_studies/
# for ASN1
$ wget -O case_studies/ASN1.tar https://figshare.com/ndownloader/files/41974683
$ tar -xf case_studies/ASN1.tar -C case_studies/
```

## Executing MOTIF with each subject
By executing `run_list.py`, you can do mutation testing for all the mutants that are listed a file.
The following is the example usage and example command for the target subjects.
```shell
# ./run_list.py [--singularity] [-J <EXP_NAME>] [-timeout <INT>] <MUTANT_LIST> <PHASE>
# --singularity:  making the command to be executed in the singularity image specified in the config file
# -J <EXP_NAME>:  name of experiment and also become the name of the output directory
# -timeout <INT>: maximum execution time of the fuzzer
# <MUTANT_LIST>:  a text list file of target mutants
# <PHASE>:        execution phase of MOTIF {'all', 'preprocess', 'build', 'run'}, 'all' contains all the following phases 
$ ./run_list.py -c case_studies/MLFS/config-mlfs.py --singularity -J _exp1 --timeout 600 case_studies/MLFS/live_mutants all
$ ./run_list.py -c case_studies/ASN1/config-asn1.py --singularity -J _exp1 --timeout 600 case_studies/ASN1/live_mutants all
```

## Finding the experiment results
```shell
$ ls -al case_studies/MLFS/_exp1
# The following directories will be appeared 
#   1-func-drivers:  test drivers for each target function
#   2-func-inputs:   seed inputs for each target function
#   3-mutant-funcs:  functions that are extracted from the mutants (only mutated functions)
#   4-mutant-bins:   compiled results for each mutant
#   5-fuzzing:       stored results of fuzzing for each mutant
#   logs:            stored log files (not be shown in local execution)
#   _exp1-all.cmd:   listed all the commands that are executed by the run_list.py
```

## Making summary of the results 
```shell
# Generate the summary of the results (will be stored <OUTPUT>/summary.csv if the output path is not given)
$ ./tools/RunCollector.py -b case_studies/MLFS -J _exp1 -m live_mutants --time 600 --plus

# show the output directory
$ ls -al case_studies/MLFS/_exp1

# show results
$ cat case_studies/MLFS/_exp1/summary.csv
```







# General guideline of MOTIF
We provide this guide for users who apply MOTIF pipeline to a new subject.

## Preparing a target subject
1. Create a subject directory
   ```shell
   # You can make the directory anywhere, but we recommend you to locate it in this repository 
   # so that you can easily mount the directory to the singularity container without additional settings. 
   $ mkdir -p case_studies/_SUBJECT
   ```

2. Copy source codes for the software under test (SUT) as a tar file.
   * MOTIF works with tar archive file for parallel work
   ```shell
   # Move to the directory of the SUT
   $ cd /path/from/SUT
   # Make an archive in the _SUBJECT directory from the current directory, including all hidden files
   #    Please make sure that all symbolic link files use relative paths and do not link outside of the SUT directory
   /path/from/SUT$ tar -cf /path/to/_SUBJECT/src.tar ./. 
    ```

3. Copy mutants files as a tar file
   * MOTIF works with tar archive file for parallel work
   * We assume that the mutants are generated by a mutation analysis tool (e.g., MASS)
     and the directory of the mutants has to have the same structure as the source code repository.
     See the example below:
     > /path/from/SUT (source code repository) <br>
     &nbsp; &nbsp; &nbsp; ./time.c <br>
     &nbsp; &nbsp; &nbsp; ./main.c <br>
     <br>
     /path/from/MUTANTS (mutants directory) <br>
     &nbsp; &nbsp; &nbsp; ./time/time.mut.12.1_1_1.system_time.c <br>
     &nbsp; &nbsp; &nbsp; ./time/time.mut.12.1_1_1.system_time.c <br>
     &nbsp; &nbsp; &nbsp; ./main/main.mut.12.1_1_1.main.c <br>

   * You can copy them as an archive using the following commands:
      ```shell
      # Move to the directory of the mutants
      $ cd /path/from/MUTANTS
      # Make an archive in the _SUBJECT directory from the current directory
      /path/from/SUT$ tar -cf /path/to/_SUBJECT/mutants.tar ./.
      ```

4. Make a list of target mutants

   Among the mutants files that you copied from mutation analysis results, select and list mutants that you want to do mutation testing.
   Each item consist of mutant name or mutant path and a list of input filter:
   > [relative/path/from/MUTANTS/]<mutant_name>[;input_filter]

   The input filter is a list of options, which are {A: all, N: negative, Z: zero, P: positive}. You can specify them with delimiter ';'
   Actual list could be one of the examples below:
   ```
   # A simple list of mutant file name
   clock.mut.87.3_2.ICR.gs_clock.c
   clock.mut.88.2_4.ROD.gs_clock.c
   ...
   ```
   ```
   # A relative mutant file path from the '_SUBJECT/mutants' directory.
   src/clock/clock.mut.87.3_2.ICR.gs_clock.c
   src/clock/clock.mut.88.2_4.ROD.gs_clock.c
   ...
   ```
   ```
   # A mutant file name (also can contain relative path) and input filter.
   clock.mut.87.3_2.ICR.gs_clock.c;A
   clock.mut.88.2_4.ROD.gs_clock.c;Z;P
   clock.mut.89.2_1.LCR.gs_clock.c;N;Z;P
   ...
   ```


## Changing the configuration for a subject
The `config.py` is the default configuration file for the pipeline.
If you want to use the other file, you can create and provide it to the pipeline (i.e., `run.py` and `run_list.py`) using "-c" parameter.
Please take a look at the `config.py` file and change according to your necessary. 
At least you need to provide the following information correctly:
* `EXP_BASE`: path of the SUBJECT directory
* `TEMPLATE_CONFIG`: template configuration for the test drivers
* compile configurations: `INCLUDES`,  `COMPILE_SUT_CMDS`, and etc.
* `SINGULARITY_FILE`: singularity file that will be used for the pipeline 



## Mutation Testing (Multiple mutants in sequential)
The `run_list.py` is the main entry point of the pipeline for mutation testing.
The following is the simple usage of the command. This command will run fuzzing for all the mutants in the specified mutants list sequentially
> run_list.py [-c <CONFIG_FILE>] [-J <EXP_NAME>] [-t <EXP_TAG>] [--runs <RUNS>] [--timeout <TIMEOUT>] <MUTANTS_LIST_FILE> <PHASE_NAME>
> - MUTANTS_LIST_FILE: a file containing the list of target mutants. (e.g., `live_mutants`)
> - PHASE_NAME: one of the following phases {'preprocess', 'build', 'run', 'all'}
> - CONFIG_FILE: the path of the configuration file. Default file is `./config.py`
> - EXP_NAME: Name of the experiment
> - EXP_TAG: Sub name of the experiment, need to specify if you want to multiple runs with the same test drivers
> - RUNS: Number of runs to be executed for each mutant
> - TIMEOUT: Maximum time limit to do fuzzing

Each phases will do as below:
* `preprocess`: generate test drivers for each function that are related to the <mutants_list_file>
    * If there is multiple mutants for a function, then it generates one test driver
* `build`: generate inputs and executable SUT for all mutants listed in the <mutants_list_file>
* `run`: execute fuzzing for all mutants listed in the <mutants_list_file>
* `all`: execute fuzzing all the phase at once

You can execute the pipeline in the singularity container after connecting to the container.
```shell
$ singularity shell --bind ./:/expr -H /expr ./containers/motif_default.sif
[singularity]~/$ cd /expr
[singularity]/expr$ python3 run_list.py live_mutants preprocess
[singularity]/expr$ python3 run_list.py live_mutants build
[singularity]/expr$ python3 run_list.py --timeout 600 live_mutants run
or 
[singularity]/expr$ python3 run_list.py --timeout 600 live_mutants all
```

MOTIF also supports the pipeline execution connecting to the singularity container indirect way with a flag `--singularity`. 
The following command will connect to the singularity written in `SINGULARITY_IMAGE` in `config.py`, 
then execute the `preprocess`, `build`, and `run` phases.
```shell
$ python3 run_list.py --singularity --timeout 600 live_mutants all
```


## Mutation Testing on HPC (Sequential)
For the execution of the pipeline, you need to upload all the input files and pipeline files into the HPC.
We assume that `~/<workpath>` directory is the working directory for this mutation testing.
On the HPC, you need to specify `--hpc` flag instead of `--singularity` flag.
With `--hpc` flag, the pipeline will generate a list of commands in a <command_file> for the fuzzing and
request a job to the SLURM job scheduler by providing `launcher.sh` (located in the directory `./scripts/HPC/`),
which contains all the necessary pieces of stuff to execute the commands from the <command_file>.
The commands listed in the file will be executed sequentially.
```shell
# run_list.py [--runs <int>] [--timeout <int>] [--hpc] <mutants_list_file> <phase>
[HPC]~/<workpath>$ python3 run_list.py --hpc live_mutant_list preprocess
[HPC]~/<workpath>$ python3 run_list.py --hpc live_mutant_list build
[HPC]~/<workpath>$ python3 run_list.py --hpc --timeout 600 live_mutant_list run
```


## Mutation Testing on HPC (Parallel)
This pipeline supports multiple executions of fuzzing on HPC.
To do this, you need to provide `--parallel` flag.
(When the `--parallel` is on, `--hpc` is also on automatically, you do not need to provide `--hpc` parameter together)
With `--parallel` flag, the pipeline will generate a list of commands in a <command_file> for the fuzzing and
request multiple jobs to slurm job scheduler using `parallel.sh`(located in the directory `./scripts/HPC/`),
by providing the <command_file> and line numbers that indicate the `parallel.sh` need to process commands.
The `parallel.sh` will call `launcher.sh` with the line number of <command_file>.
The parameter [--runs <int>] executes <int> times of fuzzing for each mutant.
If we have 5 target mutants and runs 10 times, the total number of the experiment will be 50 = 10  * 5.
```shell
# run_list.py [--runs <int>] [--timeout <int>] [--hpc] [--parallel] <mutants_list_file> <phase>
# You also can do preprocess with '--parallel' parameter.
#    But you may not need to use --parallel for the preprocess phase as the phase will be taken a short time.  
[HPC]~/<workpath>$  python3 run_list.py --hpc --parallel live_mutant_list preprocess
[HPC]~/<workpath>$  python3 run_list.py --hpc --parallel live_mutant_list build
[HPC]~/<workpath>$  python3 run_list.py --hpc --parallel --timeout 600 --runs 10 live_mutant_list run
```


## Single Mutation Testing
Internally, the `run_list.py` calls `run.py` for each experiment with a mutant.
Usually, you will work with a list of mutants, but you may need to use `run.py` sometimes for debugging or other purposes.
In this case, you can use the below commands.
The parameters of the `run.py` is similar to `run_list.py` as they share almost the same parameters.
The parameter `--runID` is used for indicating an experiment among the multiple runs of the experiment for a mutant.
This parameter is used when the `run_list.py` uses `--runs` parameter.
Note that you need to execute `run.py` in the singularity shell, because of the experiment environment.
```shell
$ singularity shell --bind ./:/expr -H /expr ./containers/motif_default.sif
[singularity]~/$ cd /expr
# python3 run.py [--runID <int>] [--timeout <int>] <mutant_name> <input_filter> <phase>
[singularity]/expr$ python3 run.py mutant_file_name A preprocess
[singularity]/expr$ python3 run.py --timeout 600 mutant_file_name A preprocess
[singularity]/expr$ python3 run.py --runID 1 --timeout 600 mutant_file_name A preprocess
```


