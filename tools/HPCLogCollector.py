#!/usr/bin/env python3
################################################################
# SLURM parameters
################################################################
###### general options ##############################
#SBATCH -J COLLECTOR
#SBATCH --time=5:00:00
#SBATCH --mail-type=all
##SBATCH --mail-user=jaekwon.lee@uni.lu

###### job options ##############################
#SBATCH -N 1                         # Stick to a single node (all executions will be located in a node)
#SBATCH -c 1                         # --cpus-per-task=<ncpus>, if your application is using multithreading, increase the number of cpus(cores), otherwise just use 1
#SBATCH --mem-per-cpu=16GB            # Stick to maximum size of memory

###### performance option ########################
#SBATCH --qos normal
#SBATCH --partition=batch

###### logging option ##############################
#SBATCH -o %j-%x.out          # Logfile: <jobid>-<jobname>.out
#SBATCH -e %j-%x.out          # Logfile: <jobid>-<jobname>.out
#
###############################################################
# SLURM: get root path of MOTIF
###############################################################
import os
import sys
if os.getenv('SLURM_JOB_ID') is not None and (
        os.getenv('SLURM_JOB_PARTITION') != 'interactive' and os.getenv('SLURM_JOB_QOS')  != 'debug'):
    # Executing by sbatch directly
    import subprocess
    print('SLURM_JOB_ID='+os.getenv('SLURM_JOB_ID') )
    cmd = "scontrol show job " + os.getenv('SLURM_JOB_ID') + " | awk -F= '/Command=/{print $2}'"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout.decode('utf-8')
    CURRENT_FILE_PATH = result.split(" ")[0]
    print('CURRENT_FILE_PATH='+CURRENT_FILE_PATH )
else:
    # executing the script directly
    CURRENT_FILE_PATH = __file__
MOTIF_PATH = os.path.abspath(os.path.join(os.path.dirname(CURRENT_FILE_PATH), '..'))
print("MOTIF_PATH= "+MOTIF_PATH)
sys.path.append(MOTIF_PATH)
###############################################################
# import os
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from pipeline import utils
import tools.utils


class HPCLogCollector():
    output = None
    records = []

    def __init__(self):
        # parameter setting
        params = self.parse_arg()

        # set basic paths
        exp_path = utils.makepath(params.basePath, params.expName)
        log_path = utils.makepath(exp_path, 'logs'+('-'+params.tagName if params.tagName is not None else ''))

        # set log command name
        log_cmd = params.expName
        if params.tagName is not None and params.tagName != '':
            log_cmd = log_cmd + '-' + params.tagName
        if params.phase is not None and params.phase != '':
            log_cmd = log_cmd + '-' + params.phase

        # get the command file
        cmd_file = utils.makepath(exp_path, log_cmd + '.cmd')
        cmds = self.get_commands_list(cmd_file)

        # get a list of files
        pattern = '%s\\.([0-9]+).*'% re.escape(log_cmd)
        # load all files related to results of fuzzer
        folders = tools.utils.expandDirs([{'path':log_path}], 'Folder', _ptn=pattern, _sort=True)
        log_files = tools.utils.getFiles(folders, 'Run', _ptn="([0-9]+).out", _sort=True)
        if len(log_files) == 0:
            print("Not found the related files", flush=True)
            return

        # get list of parallels
        # print("Get all target files ...", flush=True)
        parallel_files = tools.utils.getFiles(folders, 'Parallel', _ptn="(%s)"%re.escape("parallel.log"), _sort=True)
        parallel_files = [file['path'] for file in parallel_files]

        # call procedure for each applicatino
        self.analyze_HPC_log(log_files, parallel_files, cmds, params.phase, params.infoKeys)
        # getattr(self, 'analyze_'+params.phase)(log_files, parallel_files, cmds, params.infoKeys)
        # self.analyze_parallel_log(parallel_files)
        pass

    def get_commands_list(self, _command_file):
        cmds = open(_command_file, 'r').readlines()
        cmds = [cmd.strip() for cmd in cmds]

        cmds_dict = []
        for cmd in cmds:
            idx = cmd.find("--runID")
            if idx == -1:
                cmds_dict.append({'cmd':cmd, 'runID':None})
                continue
            idx2 = cmd.find(" ", idx+8)
            runID = int(cmd[idx+8:idx2])
            cmds_dict.append({'cmd':cmd, 'runID':runID})
        return cmds_dict

    def analyze_HPC_log(self, _logs, _parallels, _commands, _phase, _keys):
        check_result_function = getattr(self, 'check_'+_phase+'_success')
        failed = 0
        success = 0
        # print("Analyze HPC logs...", flush=True)
        for idx in range(0, len(_logs)):
            info = self.collect_values(_logs[idx]['path'], _keys)
            if check_result_function(_logs[idx]['path']):
                print("[ID: %d] Succeed, command: %s, info: %s" % (_logs[idx]['ID'], _commands[idx]['cmd'], str(info)), flush=True)
                success += 1
            else:
                print("[ID: %d] Failed, command: %s, info: %s"%(_logs[idx]['ID'], _commands[idx]['cmd'], str(info)), flush=True)
                failed += 1

        print("\n[HPC %s parallel execution analysis]" % _phase)
        print("%d/%d Succeed" % (success, len(_logs)))
        print("%d/%d Failed" % (failed, len(_logs)))
        pass

    ########################################################
    # analysis functions for each phase (preprocess, build, run)
    ########################################################
    def check_preprocess_success(self, _logfile):
        iterator = tools.utils.readline_reverse(_logfile, 20)

        for line in iterator:
            if line.startswith("Please go with `build` phase"):
                return True
        return False

    def check_build_success(self, _logfile):
        iterator = tools.utils.readline_reverse(_logfile, 10)

        for line in iterator:
            if line.startswith("Please fun fuzzer!!"):
                return True
        return False

    def check_fuzzing_success(self, _logfile):
        iterator = tools.utils.readline_reverse(_logfile, 30)

        # check error messages
        lines = []
        for line in iterator:
            if line.find("SYSTEM ERROR")>=0:
                return False
            lines.append(line)

        # find the result file
        result_file = None
        for line in lines:
            key = "Please find the results"
            if line.startswith(key):
                result_file = line[len(key)+2:].strip()
                break

        # final states check
        final_state = False
        for line in lines:
            if line.startswith("Finished fuzzing"):
                final_state = True

        if final_state is False or self.check_result_file(result_file) is False:
            return False
        return True

    def check_result_file(self, _filename):
        if _filename is None: return False

        cmd = "tar tf %s" % (_filename)
        ret, lines = utils.shell.execute(cmd)
        if ret != 0:
            return False
        return True

    def check_gen_success(self, _logfile):
        iterator = tools.utils.readline_reverse(_logfile, 2000)

        # check error messages
        lines = []
        for line in iterator:
            if line.find("Traceback")>=0:
                return False
            if line.find("Failed to generate test cases") >= 0:
                return False
            if line.find("AssertionError") >=0:
                return False
            lines.append(line)

        # find the result file
        result_file = None
        for line in lines:
            key = "Please find the results"
            if line.startswith(key):
                result_file = line[len(key)+2:].strip()
                break

        # final states check
        final_state = False
        for line in lines:
            if line.startswith("Finished test case generation"):
                final_state = True

        if final_state is False or self.check_result_file(result_file) is False:
            return False
        return True

    ########################################################
    # analysis functions for preprocess phase
    ########################################################
    def analyze_repr(self, _logs, _parallels, _commands):
        failed = 0
        success = 0
        check_count=0
        IDs = []
        for idx in range(0, len(_logs)):
            ret = self.check_repr_success(_logs[idx]['path'])
            if ret is not None:
                print("[ID: %d] Succeed to run fuzzer, report: %s" % (_logs[idx]['ID'], str(ret)))
                if ret["success"] > 0:
                    check_count += 1
                    IDs.append(_logs[idx])
                success += 1
            else:
                print("[ID: %d] Failed to run fuzzer, check the command: %s"%(_logs[idx]['ID'], _commands[idx]['cmd']))
                failed += 1

        print("\n[HPC preprocess parallel execution analysis]")
        print("%d/%d Succeed to verify" % (success, len(_logs)))
        print("%d/%d Failed to verify" % (failed, len(_logs)))
        print("%d results need to be checked among the succeed results" % (check_count))
        for item in IDs:
            print("\t\t%s" % (str(item)))
        pass

    def check_repr_success(self, _logfile):
        # REPORT - total: 6576, success: 0, abort: 6576
        iterator = tools.utils.readline_reverse(_logfile, 30)

        # check error messages
        for line in iterator:
            if line.startswith("REPORT - ") is False: continue

            # convert the report into dictionary
            ret = {}
            cols = line[9:].split(",")
            for x in range(0, len(cols)):
                key, value = cols[x].split(":")
                ret[key.strip()] = int(value)

            return ret
        return None

    ########################################################
    # Collect info
    ########################################################
    def collect_values(self, _logfile, _keys:str):
        # get list of keys to collect info
        if _keys is None: return {}
        keys = _keys.upper().split(",")

        # open file
        f = open(_logfile, "r")

        # check keys in the file
        result = {}
        count = 0
        while count < 20:
            line = f.readline()
            count += 1
            if line.startswith("SLURM_") is False: continue

            # extract key and values
            cols = line.split("=")
            cols[0] = cols[0].strip()
            cols[1] = cols[1].strip()

            # add item if the key is in the _keys
            if cols[0].strip()[6:] in keys:
                result[cols[0]] = cols[1]

        # close file
        f.close()
        return result

    ########################################################
    # File writer manager
    ########################################################
    def open_output(self, _output):
        self.output = None
        if _output is not None:
            self.output = open(_output, "w")
        pass

    def print(self, _msg):
        self.records.append(_msg)
        print(_msg)
        if self.output is not None:
            self.output.write(_msg+"\n")
        pass

    def close_output(self):
        if self.output is not None:
            self.output.close()
        pass

    ########################################################
    # parse parameters
    ########################################################
    def parse_arg(self):
        import argparse
        import sys
        parser = argparse.ArgumentParser(description='Paremeters')
        parser.add_argument('-b', dest='basePath', type=str, default=None, help='base path')
        parser.add_argument('-J', dest='expName', type=str, default=None, help='experiment name (job name)')
        parser.add_argument('-t', dest='tagName', type=str, default=None, help='sub dir pattern')
        parser.add_argument('-p', dest='phase', type=str, default=None, help='sub dir pattern')
        parser.add_argument('--keys', dest='infoKeys', type=str, default=None, help='type of data')

        # parameter parsing
        args = sys.argv[1:]  # remove executed file
        args = parser.parse_args(args=args)
        if args.basePath is None or len(args.basePath)==0:
            parser.print_help()
            exit(1)

        if args.expName is None or len(args.expName)==0:
            parser.print_help()
            exit(1)

        if args.phase is None or len(args.phase)==0:
            parser.print_help()
            exit(1)

        return args


if __name__ == "__main__":
    HPCLogCollector()

    ## Usages
    # ./venv/bin/python3 ./tools/HPCLogCollector.py -b case_studies/ASN1 -J _uniq -t test -p preprocess
    # ./venv/bin/python3 ./tools/HPCLogCollector.py -b case_studies/ASN1 -J _uniq -t test -p build
    # ./venv/bin/python3 ./tools/HPCLogCollector.py -b case_studies/ASN1 -J _test -t test -p run
    # python3 ./tools/HPCLogCollector.py -b case_studies/ASN1 -J _test -t test -p build
