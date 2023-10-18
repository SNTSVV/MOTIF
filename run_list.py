#! /usr/bin/env python3
import os
import platform
if platform.python_version().startswith("3.") is False:
    raise Exception("Must be using Python 3")
import math
from pipeline import Config
from pipeline import utils
from pipeline import Mutant


###
# This class is a helper to execute multiple runs of fuzzing.
# Additionally, it supports various execution environment such as Singularity and HPC.
# - python3 run_list.py case_studies/ASN1/list/live_mutants all
# - python3 run_list.py --singularity case_studies/ASN1/list/live_mutants all
# - python3 run_list.py --hpc case_studies/ASN1/list/live_mutants all
# - python3 run_list.py --hpc --parallel case_studies/ASN1/list/live_mutants all
# - python3 run_list.py --hpc --parallel --runs 10 case_studies/ASN1/list/live_mutants all
# - run_list.pyt execute run.py with one target mutant
# - all parameters specified for run_list.py also pass to the run.py execution
###
class ListRunner(object):

    def __init__(self):
        # Load config file and set the values
        global confList
        params = Config.parse_arg(_multi=True)
        confList = Config.configure(params, _multi=True)
        confList.print_config(_multi=True)
        confList.verify_config(_multi=True)

        # load mutants
        mutants, input_filters = self.load_mutant_list(confList.MUTANT_LIST)
        mutant_objs = self.obtain_mutants_info(mutants)

        print('\nGenerating commands ...', end='')
        if confList.PHASE == "preprocess":
            mutants, input_filters = self.reduce_redundent_mutant(mutant_objs, mutants, input_filters)
            commands = self.generate_commands(mutants, input_filters, _sequential=not confList.HPC_PARALLEL)
            print('Done (%d commands)' % len(commands))
            if len(mutant_objs) != len(mutants):
                print("Preprocessing does not need to be done for all the mutants.")
                print("Reduced the number of mutants (%d -> %d) since they share the same source code." % (len(mutant_objs), len(mutants)))
        else:
            commands = self.generate_commands(mutants, input_filters)
            print('Done (%d commands)' % len(commands))

        print('\nExecuting commands ...', end='')
        self.run(commands)
        pass

    def run(self, _commands):
        command_file = self.store_commands(_commands)
        print("\nCommands are stored in %s"% command_file)

        if confList.HPC is False:
            # execute in local machine or HPC without sbatch
            self.local_sequential(_commands, _resume=confList.RESUME)
        else:
            print('\nCreating slurm job(s) ...')
            if confList.HPC_PARALLEL is False:
                log_file = self.get_logfile_path()
                self.sbatch_sequencial(command_file, log_file, _resume=confList.RESUME)
            else:
                log_file = self.get_logfile_path()
                self.sbatch_parallel(len(_commands), command_file, log_file, _resume=confList.RESUME)
        pass

    ##########################################
    # Execute runners as a single process
    ##########################################
    def generate_commands(self, _mutants, _input_filters, _sequential=False):
        cmds = []
        # Execute multiple runs
        if confList.RUNS is not None and confList.PHASE in ["fuzzing", "gen"]:
            # generate multiple runs of commands for all mutants
            for idx in range(0, len(_mutants)):
                for runID in range(1, confList.RUNS+1):
                    params = self.make_parameters(_mutants[idx], _input_filters[idx], runID, _sequential)
                    cmd = "%s %s" % (confList.PYTHON_CMD, ' '.join(params))
                    cmds.append(cmd)
        else:
            # generate single run of commands for all mutants
            for idx in range(0, len(_mutants)):
                params = self.make_parameters(_mutants[idx], _input_filters[idx], _sequential=_sequential)
                cmd = "%s %s" % (confList.PYTHON_CMD, ' '.join(params))
                cmds.append(cmd)
        return cmds

    def store_commands(self, _cmds):
        # store the commands in one file
        filename = "%s.cmd"%confList.JOB_NAME
        command_file = utils.makepath(confList.OUTPUT_PATH, filename)
        utils.prepare_directory(os.path.dirname(command_file))
        with open(command_file, "w") as f:
            for line in _cmds:
                f.write(line + '\n')
        return command_file

    ##########################################
    # Execute commands in local machine or in a singularity
    ##########################################
    def local_sequential(self, _cmds, _resume=1):
        start_idx = _resume-1    # python index starts from 0
        end_idx = len(_cmds)
        for idx in range(start_idx, end_idx):
            print("\n[cmd %d]: %s"%(idx+1, _cmds[idx]))
            if confList.SINGULARITY is False:
                self.execute_command(_cmds[idx])
            else:
                print("Connecting to Singularity ...")
                self.execute_command_in_singularity(_cmds[idx])
        return True

    def execute_command(self, _command):
        if confList.DRY_RUN is True:
            print('\n'+_command)
            return True
        utils.shell.execute_and_check(_command, 'retcode', 0, _verbose=True)
        return True

    def execute_command_in_singularity(self, _command):
        cmd = "singularity exec --bind ./:/expr -H /expr %s %s" % (confList.SINGULARITY_FILE, _command)
        if confList.DRY_RUN is True:
            print('\n'+cmd)
            return True
        utils.shell.execute_and_check(cmd, 'retcode', 0, _verbose=True)
        return True

    ##########################################
    # Submit a job(s) to SLURM on HPC
    ##########################################
    def sbatch_sequencial(self, _cmd_file, _log_file, _resume=1):
        # generate command for ./launcher.sh
        # sbatch -J <JOB_NAME> <SBATCH_PARAMETERS> -o <LOG_FILE> -e <LOG_FILE>
        #        ./launcher.sh <CMD_FILE> <SINGULARITY_FILE>
        cmd = "sbatch -J %s %s -o %s -e %s" % (
            confList.JOB_NAME,
            confList.SBATCH_PARAMETERS,
            _log_file, _log_file)
        if confList.REPORT_EMAIL is not None:
            cmd += " --mail-user %s" % confList.REPORT_EMAIL
        cmd += " %s %s %s" % (
            confList.SLURM_SINGLE_EXECUTOR,
            _cmd_file,
            confList.SINGULARITY_FILE)

        # execute command
        print("\n"+cmd)
        if confList.DRY_RUN is True:
            print("\n---This is a dry run, we do not submit a job(s) to SLURM---\n")
            return True

        retcode, lines = utils.shell.execute(cmd, _verbose=True)
        if retcode is None:
            utils.error_exit("Failed to create HPC job. Please check the command below: \n%s"%cmd)
        jobID = self.get_jobID(lines)
        if jobID is not None: self.store_jobIDs([jobID])
        return True

    def sbatch_parallel(self, _n_cmds, _cmd_file, _log_file, _resume=1):

        # set resume option
        first_cmd_id = _resume    # The file line starts from 1
        last_cmd_id = _n_cmds

        # execute parallel.sh
        cnt = 0
        jobIDs = []
        for cmd_id in range(first_cmd_id, last_cmd_id+1, confList.N_TASKS_PER_JOB):
            upper_bound_id = cmd_id + confList.N_TASKS_PER_JOB - 1
            upper_bound_id = min(upper_bound_id, last_cmd_id)
            tasks_per_node = min(confList.N_PARALLELS_PER_JOB, upper_bound_id - cmd_id + 1)

            # sbatch -J <JOB_NAME> <SBATCH_PARAMETERS> -o <LOG_FILE> -e <LOG_FILE>
            cmd = "sbatch -J %s %s --ntasks-per-node %d -o %s -e %s" % (
                    "%s.%02d" % (confList.JOB_NAME, cnt+1),
                    confList.SBATCH_PARAMETERS,
                    tasks_per_node,
                    _log_file, _log_file)
            dependency = self.get_dependency_string(confList.DEPENDENCY)
            if dependency is not None: cmd += " --dependency %s" % dependency
            if confList.REPORT_EMAIL is not None: cmd += " --mail-user %s" % confList.REPORT_EMAIL
            if confList.PHASE.lower() == "fuzzing":
                # calculate request time it should be less than 2 days (48 hours)
                multiply = math.ceil(confList.N_TASKS_PER_JOB / confList.N_PARALLELS_PER_JOB)
                additional = max(confList.FUZZING_TIMEOUT * 0.2, 1800)  # 20% additional time or 30 mins
                single_request_time = confList.FUZZING_TIMEOUT + additional
                cmd += " --time %s" % utils.convert_time_for_SLURM(single_request_time * multiply)

            # append parallel command
            #        ./parallel.sh [-l <LOG_FILE>] [--lines MIN:MAX] <CMD_FILE> <SINGULARITY_FILE>
            cmd += " %s -l %s --lines %d:%d %s %s" % (
                        confList.SLURM_PARALLEL_EXECUTOR,
                        _log_file,                 # log_file
                        cmd_id,                    # --min
                        upper_bound_id,            # --max
                        _cmd_file,
                        confList.SINGULARITY_FILE)
            print("\n"+cmd)

            # execute on HPC with parallel
            if confList.DRY_RUN is False:
                retcode, lines = utils.shell.execute(cmd, _verbose=True)
                if retcode is None:
                    utils.error_exit("Failed to create HPC job. Please check the command below: \n%s"%cmd)
                jobID = self.get_jobID(lines)
                if jobID is not None:
                    jobIDs.append(jobID)

            cnt += 1

        if cnt >= 50:
            msg  = "\nWe cannot order over 50 jobs at the same time."
            msg += "\nThe remaining jobs will be started the first 50 jobs are finished."
            # utils.error_exit(msg)

        if confList.DRY_RUN is True:
            print("\n---This is a dry run, we do not submit a job(s) to SLURM---\n")
        else:
            self.store_jobIDs(jobIDs)
        return True

    ##########################################
    # Work with HPC job dependency
    ##########################################
    def get_jobID(self, _lines):
        jobID = None
        for line in _lines:
            line = line.strip()
            if line == "": continue
            if line.startswith("Submitted batch job") is True:
                jobID = int(line[20:])
                break
        return jobID

    def get_jobs_path(self, _previous=False):
        os.makedirs(confList.LIST_JOBID_PATH, exist_ok=True)
        if _previous is True:   # get list of jobs for the previous step
            items = confList.JOB_NAME.split("-")
            # replace current phase to previous phase
            process_order = ["", "preprocess", "build", "fuzzing", "gen"]
            for idx in range(0, len(process_order)):
                if items[-1] != process_order[idx]: continue
                items[-1] = process_order[idx-1]
                break
            job_name = "-".join(items)
        else:
            job_name = confList.JOB_NAME

        if job_name == "": return None

        target_list = confList.MUTANT_LIST.replace("/", "_")
        target_list = target_list.replace(".", "")

        filepath = utils.makepath(confList.LIST_JOBID_PATH, target_list+ "-"+job_name+".list")
        return filepath

    def store_jobIDs(self, _jobIDs):
        filepath = self.get_jobs_path()
        f = open(filepath, "w")
        for jobID in _jobIDs:
            f.write("%d\n"%jobID)
        f.close()

    def load_jobIDs(self):
        filepath = self.get_jobs_path(_previous=True)
        if os.path.exists(filepath) is False: return []

        f = open(filepath, "r")
        lines = f.readlines()
        f.close()

        jobIDs = []
        for line in lines:
            if line.strip() == "": continue
            jobIDs.append(int(line.strip()))
        return jobIDs

    def get_dependency_string(self, _dependency):
        if _dependency is None: return None
        if _dependency != "auto": return _dependency

        jobIDs = self.load_jobIDs()
        IDstr = ':'.join([str(jobID) for jobID in jobIDs])
        if IDstr == "": return None
        return "afterok:%s"%IDstr

    ##########################################
    # utils
    ##########################################
    def get_logfile_path(self):
        # prepare log path for HPC parallel executions
        utils.prepare_directory(confList.HPC_LOG_PATH)
        return utils.makepath(confList.HPC_LOG_PATH, confList.LOG_FILE_NAME)

    def load_mutant_list(self, _filepath):
        '''
        load a list of mutants from the given file
        :param _filepath: file path that describes <mutant-filename>;[input-filters] in each line
            - <mutant-filename>: name of a mutant (recommend to include the directory path)
                                 In case of omitting directory path, the pipeline finds the path, if there is no duplicate name of mutants
            - <input-filters>  : list of input filters for a mutated function (N:negative, Z:zero, P:positive, A:all)
                                 e.g.: `N;Z`, `N;Z;P`, `A`
                                 if the input-filters are not provided, we assume that all type of inputs are considered for the mutant
        :return:
        '''
        with open(_filepath, 'r') as f:
            lines = f.readlines()

        # generate inputs
        mutants = []
        input_filters = []
        for line in lines:
            line = line.strip()
            if line == "": continue

            items = line.split(";")

            # get mutants path
            mutant = items[0]
            if os.path.dirname(mutant) != "":
                if mutant.startswith("../") is True: utils.error_exit("Not available mutant name: %s"% mutant)
                elif mutant.startswith("./") is False: mutant = "./" + mutant
                elif mutant.startswith("/") is True: mutant = "." + mutant
            mutants.append(mutant)

            if len(items)>1:
                input_filters.append(";".join(items[1:]))
            else:
                input_filters.append("A")

        return mutants, input_filters

    def make_parameters(self, _mutant, _input_filter, _runID=None, _sequential=False):
        # create parameters
        params = confList.get_single_run_arguments_template()
        if _runID is not None:
            params.insert(-3, "--runID")
            params.insert(-3, str(_runID))  # all parameters should be a string
        if _sequential is True:
            params.insert(-3, "--noconfview")
        params[-3] = _mutant
        params[-2] = _input_filter

        return params

    def obtain_mutants_info(self, _mutants):
        # load all mutants information
        print('Loading mutants list from MUTANTS_FILE %s ...'%confList.MUTANTS_FILE)
        match = '*.%s.*.c'%confList.MUTANT_FUNC_PREFIX
        all_mutants = utils.get_all_files_in_tar(confList.MUTANTS_FILE, _match=match)
        base_mutants = [ os.path.basename(path) for path in all_mutants]

        # check the listed mutants are in the all mutants
        print('Verifying mutants and get mutants info ...')
        mutant_objs = []
        for idx in range(0, len(_mutants)):
            mutant = _mutants[idx]
            print('[Verifying %d/%d] %s ... '% (idx+1, len(_mutants), mutant), end='')

            # verify the mutant exists in the tar file (to reduce the time, I didn't use the utils library)
            mutant_path = None
            if os.path.dirname(mutant) == "":
                for idx in range(0, len(base_mutants)):
                    if mutant != base_mutants[idx]: continue
                    mutant_path = all_mutants[idx]
                    break
            else:
                for item in all_mutants:
                    if mutant != item: continue
                    mutant_path = item
                    break
            if mutant_path is None:
                utils.error_exit("Cannot find the mutant in the MUTANTS_FILE: %s"% mutant)

            # generate mutant info
            mutant_info = Mutant.parse(mutant_path)
            print('OK')

            mutant_objs.append(mutant_info)

        return mutant_objs

    def reduce_redundent_mutant(self, _objs, _mutants, _input_filters):
        r_mutants = []
        r_filters = []

        selected = set()
        for idx in range(0, len(_objs)):
            key_name = _objs[idx].src_name + ":" + _objs[idx].func
            if key_name in selected: continue

            # add into the selected list
            selected.add(key_name)
            r_mutants.append(_mutants[idx])
            r_filters.append(_input_filters[idx])

        return r_mutants, r_filters


if __name__ == "__main__":
    obj = ListRunner()
    exit(0)