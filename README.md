# Getting started with MOTIF

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


## Working Environment
`MOTIF` is designed for working on Linux machines, especially for the Ubuntu 18.04 LTS.
It requires installing the following Linux and Python libraries.
```shell
sudo apt update -y
sudo apt install -y gcc g++ python python3 python3-pip   # Python 3.6.9

# python-pip upgrade
sudo pip3 install --upgrade pip

# install python dependencies
pip3 install Jinja2==3.0.3
pip3 install libclang==15.0.6.1
pip3 install psutil==5.9.2
pip3 install chardet==3.0.4
```
If you have an issue with installing the working environment,
please use the Singularity image that we provided
following [the section for Singualrity](#working-with-singularity)



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


## Preparing target subjects
We provide the subject data: ASN1 and MLFS, which are open-source. Each subject archive contains software under test, mutants generated by MASS, target live mutants, and a configuration file for MOTIF.
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
# ./run_list.py [-J <EXP_NAME>] [-timeout <INT>] <MUTANT_LIST> <PHASE>
# -J <EXP_NAME>:  name of experiment and also become the name of the output directory
# -timeout <INT>: maximum execution time of the fuzzer
# <MUTANT_LIST>:  a text list file of target mutants
# <PHASE>:        execution phase of MOTIF {'all', 'preprocess', 'build', 'run'}, 'all' contains all the following phases 
$ ./run_list.py -c case_studies/MLFS/config-mlfs.py -J _exp1 --timeout 600 case_studies/MLFS/live_mutants all
$ ./run_list.py -c case_studies/ASN1/config-asn1.py -J _exp1 --timeout 600 case_studies/ASN1/live_mutants all
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






---
---
# General guideline of MOTIF
We provide this guide for users who apply the MOTIF pipeline to a new subject.

## Preparing a target subject
1. Create a subject directory
   ```shell
   # You can make the directory anywhere, but we recommend you to locate it in this repository 
   # so that you can easily mount the directory to the virtual machines without additional settings. 
   $ mkdir -p case_studies/_SUBJECT
   ```

2. Copy source codes for the software under test (SUT) as a tar file.
    * MOTIF works with tar archive files for parallel work
   ```shell
   # Move to the directory of the SUT
   $ cd /path/from/SUT
   # Make an archive in the _SUBJECT directory from the current directory, including all hidden files
   #    Please make sure that all symbolic link files use relative paths and do not link outside of the SUT directory
   /path/from/SUT$ tar -cf /path/to/_SUBJECT/src.tar . 
    ```

3. Copy mutants files as a tar file
    * MOTIF works with tar archive files for parallel work
    * We assume that the mutants are generated by a mutation analysis tool (e.g., MASS)
      and the directory of the mutants has to have the same structure as the source code repository.
      See the example below:
      > /path/from/SUT (source code repository) <br>
      &nbsp; &nbsp; &nbsp; ./time.c <br>
      &nbsp; &nbsp; &nbsp; ./main.c <br>
      <br>
      /path/from/MUTANTS (mutants directory) <br>
      &nbsp; &nbsp; &nbsp; ./time/time.mut.12.1_1_1.ROR.system_time.c <br>
      &nbsp; &nbsp; &nbsp; ./time/time.mut.13.1_1_2.UOI.system_time.c <br>
      &nbsp; &nbsp; &nbsp; ./main/main.mut.14.1_1_3.SDL.main.c <br>
    * The name of the mutant file has the structure below:
      > <FILE_NAME>.mut.<LINE_NO>.<EXTEND_INFO>.<MUTATION_OPERATOR>.<FUNCTION_NAME>.c
      > * <FILE_NAME>: the mutated source code
      > * <LINE_NO>: the mutated line number in the file
      > * <EXTEND_INFO>: the extended information for the mutation (e.g., mutated column and order of the mutant))
      > * <MUTATION_OPERATOR>: type of mutation operator that is applied to this mutant
      > * <FUNCTION_NAME>: the name of the mutated function
    * You can copy them as an archive using the following commands:
       ```shell
       # Move to the directory of the mutants
       $ cd /path/from/MUTANTS
       # Make an archive in the _SUBJECT directory from the current directory
       /path/from/SUT$ tar -cf /path/to/_SUBJECT/mutants.tar .
       ```

4. Make a list of target mutants

   Among the mutants files that you copied from mutation analysis results, select and list mutants that you want to do mutation testing.
   Each item consists of a mutant name and a list of input filter.
   The mutant name can be specified with a relative path.
   The input filter is optional and can be specified multiple values with a delimiter ';', among {A: all, N: negative, Z: zero, P: positive}.
   > [relative/path/from/MUTANTS/]<mutant_name>[;input_filter]

   Actual list could be one of the examples below:
   ```
   # A simple list of mutant file name
   time.mut.87.3_2_1.ICR.time_to_timestamp.c
   time.mut.88.2_4_2.ROD.time_to_timestamp.c
   ...
   ```
   ```
   # A relative mutant file path from the '_SUBJECT/mutants' directory.
   ./time/time.mut.87.3_2_1.ICR.time_to_timestamp.c
   ./time/time.mut.88.2_4_2.ROD.time_to_timestamp.c
   ...
   ```
   ```
   # A mutant file name (also can contain relative path) and input filter.
   time.mut.87.3_2_1.ICR.time_to_timestamp.c;A
   time.mut.88.2_4_2.ROD.time_to_timestamp.c;Z;P
   time.mut.89.2_1_3.LCR.time_to_timestamp.c;N;Z;P
   ...
   ```

## Changing the configuration for a subject
The `config.py` is the default configuration file for the pipeline.
If you want to use the other file, you can create and provide it to the pipeline (i.e., `run.py` and `run_list.py`) using "-c" parameter.
Please take a look at the `config.py` file and change it according to your need.
At least you need to provide the following information correctly:
* `EXP_BASE`: path of the `_SUBJECT` directory (relative path from the root directory of MOTIF or the absolute path)
* `TEMPLATE_CONFIG`: template configuration for the test drivers
* compile configurations: `INCLUDES`,  `COMPILE_SUT_CMDS`, and etc.



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

Each phase will do as below:
* `preprocess`: generate test drivers for each function that are related to the <MUTANTS_LIST_FILE>
    * If there is multiple mutants for a function, then it generates one set of test drivers (fuzzing drivers)
* `build`: generate inputs and executable SUT for all mutants listed in the <MUTANTS_LIST_FILE>
* `run`: execute fuzzing for all mutants listed in the <MUTANTS_LIST_FILE>
* `verify`: showing execution results of fuzzing drivers with inputs killing a mutant
* `all`: execute fuzzing all the phases at once

You can execute the pipeline as follows:
```shell
$ ./run_list.py case_studies/_SUBJECT/live_mutants preprocess
$ ./run_list.py case_studies/_SUBJECT/live_mutants build
$ ./run_list.py --timeout 600 case_studies/_SUBJECT/live_mutants run
or 
$ ./run_list.py --timeout 600 case_studies/_SUBJECT/live_mutants all

# If users want to conduct multiple experiments for the same mutant, users can use --runs option as below:
$ ./run_list.py --timeout 600 --runs 10 case_studies/_SUBJECT/live_mutants all
```


## Single Mutation Testing
Internally, the `run_list.py` calls `run.py` for each experiment with a mutant.
Usually, you will work with a list of mutants, but you may need to use `run.py` sometimes for debugging or other purposes.
In this case, you can use the below commands.
The parameters of the `run.py` is similar to `run_list.py` as they share almost the same parameters.
The parameter `--runID` is used for indicating an experiment among the multiple runs of the experiment for a mutant.
This parameter is used when the `run_list.py` uses `--runs` parameter.
```shell
# ./run.py [--runID <int>] [--timeout <int>] <mutant_name> <input_filter> <phase>
$ ./run.py time.mut.89.2_1_3.LCR.time_to_timestamp.c A preprocess
$ ./run.py --timeout 600 time.mut.89.2_1_3.LCR.time_to_timestamp.c A preprocess
$ ./run.py --runID 1 --timeout 600 time.mut.89.2_1_3.LCR.time_to_timestamp.c A preprocess
```


---
---

# Working with Singularity
We provide the singularity image that we used for our experiments.
To use the singularity image, users need to install the software Singularity.
For the installation, please follow the guidelines from [the official website](https://docs.sylabs.io/guides/3.8/admin-guide/installation.html).
Note that we used Singularity 3.8 CE version since HPC in the University of Luxembourg uses this version.


## Connecting to vagrant box (for Windows or Mac OS users)
* We provide all the configuration to set up the vagrant instance for Singularity in `Vagrantfile`
* Please use the commands below in the root repository of MOTIF
```shell
# The command below creates a virtual machine instance according to the Vagrantfile based on the root repository.
# This will bind automatically the root repository to the directory /vagrant inside of the container
$ vagrant up 
# Connect into the vagrant box instance
$ vagrant ssh
# Move to the bound directory, which is sharing between the vagrant container and the host OS
[vagrant]$ cd /vagrant 
```
> Now, we assume that you are in the directory /vagrant in the vagrant instance, which is the same as the root repository of the MOTIF.


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

## Configuration of the Singularity
In the `config.py`, you need to specify the path of the singularity image for the parameter `SINGULARITY_IMAGE` in `config.py`.
For example, for the `motif_default.sif`, you can set as follows:
```shell
SINGULARITY_IMAGE = "containers/motif_default.sif"
```

## Installing requirements (minimum requirements to execute `./run_list.py`)
These requirements would have been satisfied if you installed the MOTIF requirements.
Only users who did not do this before, execute the below:
```shell
sudo apt update -y
sudo apt install -y gcc g++ python python3 python3-pip    # Python 3.6.9

# python-pip upgrade
sudo pip3 install --upgrade pip

# install python dependencies
pip3 install psutil
```



## Executing MOTIF
To make MOTIF work in the specified singularity image, you need to use `--singularity` flag for 
`run_list.py`. The script will then execute its work by calling `run.py` inside of the singularity image. 
See the following examples:
```shell
$ ./run_list.py --singularity --timeout 600 case_studies/_SUBJECT/live_mutants all

# The above command will call `run.py` for each mutant in the `live_mutants` in the singularity image as below:
# ./run.py --timeout 600 <mutant_1> all
# ./run.py --timeout 600 <mutant_2> all
# ./run.py --timeout 600 <mutant_3> all
# ...
```

`run.py` does not subject to the flag `--singularity`. 
Therefore, if you want to execute `run.py` in the singularity image, you need to connect to the singularity image first.
See the following examples:
```shell
$ singularity shell --bind ./:/expr -H /expr ./containers/motif_default.sif
[singularity]~/$ cd /expr
[singularity]/expr$ ./run.py time.mut.89.2_1_3.LCR.time_to_timestamp.c A preprocess
[singularity]/expr$ ./run.py time.mut.89.2_1_3.LCR.time_to_timestamp.c A build
[singularity]/expr$ ./run.py --timeout 600 time.mut.89.2_1_3.LCR.time_to_timestamp.c A run
or 
[singularity]/expr$ ./run.py --timeout 600 time.mut.89.2_1_3.LCR.time_to_timestamp.c A all
```


---
---
# Working with HPC (High Performance Computing)
Users who are available to use HPC can apply the following flags: `--hpc` and `--parallel`.
Only `run_list.py` is subject to these parameters.
To execute the commands, please consider that you have the correct working environments in HPC.

For the execution of the pipeline, you need to upload all the input files and pipeline files into the HPC.
We assume that `~/<workpath>` directory is the working directory for this mutation testing
and has the same files and structure as the local machine above.

## Mutation Testing on HPC (Sequential)
The flag `--hpc` is for the MOTIF pipeline to work with a job scheduler on HPC (SLURM).
With the flag, the pipeline will generate a list of commands (i.e. list of `run.py` commands) in a <command_file>
and request a job to the SLURM by providing `launcher.sh` (located in the directory `./scripts/HPC/`)
, which is a script dedicated for SLURM job scheduler to execute sequentially each line of <command_file>.
See the example below:
```shell
# run_list.py [--hpc] [--timeout <int>] <mutants_list_file> <phase>
[HPC]~/<workpath>$ ./run_list.py --hpc --runs 2 --timeout 100 case_studies/_SUBJECT/live_mutants all

#### <command_file>
#./run.py --runID 1 --timeout 100 time.mut.87.3_2_1.ICR.time.c A all
#./run.py --runID 2 --timeout 100 time.mut.87.3_2_1.ICR.time.c A all
#./run.py --runID 1 --timeout 100 time.mut.88.2_4_2.ROD.time.c A all
#./run.py --runID 2 --timeout 100 time.mut.88.2_4_2.ROD.time.c A all
#./run.py --runID 1 --timeout 100 time.mut.89.2_1_3.LCR.time.c A all
#./run.py --runID 2 --timeout 100 time.mut.89.2_1_3.LCR.time.c A all
# launcher.sh will execute them sequentially
```


## Mutation Testing on HPC (Parallel)
The flag `--parallel` will allow you to execute your commands in multiple nodes in HPC.
Since `--hpc` parameter is automatically on with the parameter `--parallel`, you do not need to provide `--hpc` parameter together.
With `--parallel` flag, the pipeline will generate a list of commands (i.e. list of `run.py` commands)  in a <command_file>
and request multiple jobs to SLURM job scheduler using `parallel.sh` (located in the directory `./scripts/HPC/`),
by providing the <command_file> and line numbers that indicate the `parallel.sh` need to process commands.
As like `launcher.sh`,  `parallel.sh` is also a script dedicated for SLURM job scheduler to execute in parallel each line of <command_file>.
The `parallel.sh` will call `launcher.sh`  with the line number of <command_file>.
See the following examples:
```shell
# run_list.py [--parallel] [--runs <int>] [--timeout <int>] <mutants_list_file> <phase>
[HPC]~/<workpath>$ ./run_list.py --parallel --runs 10 --timeout 10000 case_studies/_SUBJECT/live_mutants preprocess
[HPC]~/<workpath>$ ./run_list.py --parallel --runs 10 --timeout 10000 case_studies/_SUBJECT/live_mutants build
[HPC]~/<workpath>$ ./run_list.py --parallel --runs 10 --timeout 10000 case_studies/_SUBJECT/live_mutants run
```
> We recommend you execute each phase separately with `--parallel` flag, because it may cause a collision issue.
> For example, assume that you have 10 mutants for a function under test.
> Since we assume that mutants do not mutate the function prototype, we developed MOTIF to share the same fuzzing drivers for those mutants.
> Therefore, MOTIF will generate one set of fuzzing drivers for the 10 mutants.
> However, with `all` phase flag, MOTIF will generate a set of fuzzing drivers for each mutant regardless the mutated function
> and share the same location to store them.
> This may lead to a collision in that when a node builds executable fuzzing drivers, the other node overwrites the fuzzing driver in the middle.
> To prevent this issue, please do not use `all` phase flag. 