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


import tarfile
from pipeline import utils
from tools.TarResult import TarResult


class RunCollector():
    HPC = False
    HPC_TEMP_PATH = '/tmp/MOTIF/RunCollector'
    AFL_PLUS = False
    RECALCULATE_STATS = False

    def __init__(self, _basePath=None, _expName=None, _tagName=None, _mutantsPath=None, _outputPath=None, _max_time=None, _max_run=0, _AFL_plus=False, _HPC=False, _stats=False):
        # parameter setting
        if _basePath is None:
            params = self.parse_arg()
            _basePath = params.basePath
            _expName = params.expName
            _tagName = params.tagName
            _mutantsPath = params.mutantsPath
            _outputPath = params.outputPath
            _max_time = params.MAX_TIME
            _max_run = params.MAX_RUN
            _AFL_plus = params.AFLplus
            _HPC = params.HPC

        # set result path
        _resultPath = os.path.join(_basePath, _expName, "5-fuzzing")
        if _tagName is not None and _tagName != '':
            _resultPath += '-' + _tagName        # 5-fuzzing[-tagName]

        # Set mutants path
        _mutantsPath = os.path.join(_basePath, _mutantsPath)

        # Set output path (default: <_basePath>/<_expName>/summary[_tagName].csv
        if _outputPath is None or _outputPath == '':
            _outputPath = os.path.join(_basePath, _expName, "summary")
            if _tagName is not None and _tagName != '':
                _outputPath += '_' + _tagName
            _outputPath += ".csv"
        print("basePath    = " + _basePath)
        print("resultPath  = " + _resultPath)
        print("mutantsPath = " + _mutantsPath)
        print("outputPath  = " + _outputPath)
        print("\n")

        self.HPC = _HPC
        self.AFL_PLUS = _AFL_plus
        self.RECALCULATE_STATS = _stats
        self.MAX_TIME = _max_time

        # load all the tar files related to the results of fuzzer
        print("Loading a list of tar files ... ", end='')
        tarfiles = utils.get_all_files(_resultPath, _match="*.tar", _subName=True)
        print("(%d files)"%len(tarfiles))
        if len(tarfiles) == 0:
            print("Result files do not exist. Please check the result directory: %s" % (_resultPath))
            exit(1)

        print("Checking the result of fuzzing ... ")
        data = self.run(tarfiles, _outputPath, _resultPath, _mutantsPath, _max_time, _max_run)
        self.make_statistics(data)
        pass

    def run(self, _tarfiles, _output, _location, _mutant_list_path, _max_time, _max_run=0):
        self.open_output(_output)
        self.print_header()

        # check for all the mutants
        results = []
        for mutant in self.get_iter_mutants(_mutant_list_path):
            print("[%d] %s ..."%(mutant['ID'], mutant['name']))

            # select the corresponding tar files
            mutant_tars = self.get_mutant_tarfiles(mutant['name'], _tarfiles)

            # collect data without multi runs
            if _max_run == 0:
                if len(mutant_tars) == 0:
                    results.append(self.tar_analysis(_location, None, None, mutant))
                else:
                    results.append(self.tar_analysis(_location, mutant_tars[0], None, mutant))
                continue

            # collect data for multi runs
            for runID in range(1, _max_run+1):
                # find the corresponding tar file name
                tar_name = None
                for afile in mutant_tars:
                    runID_from_tar = self.get_mutant_runID(afile)
                    if runID_from_tar != runID: continue
                    tar_name = afile
                    break

                # do analysis
                results.append(self.tar_analysis(_location, tar_name, runID, mutant))

        self.close_output()
        return results

    def tar_analysis(self, _location, _tar_name, _runID, _mutant):
        if _tar_name is None:
            self.print_line(_mutant, _runID, "NOT_EXIST_TAR")  # NOT_EXIST_TAR or ERR_TAR_OPEN
            return [_mutant['ID'], _runID, "NOT_EXIST_TAR"]

        tar = self.get_tar_object(_location, _tar_name)
        if isinstance(tar,TarResult) is False:
            self.print_line(_mutant, _runID, tar)  # NOT_EXIST_TAR or ERR_TAR_OPEN
            return [_mutant['ID'], _runID, tar]

        # extract tar data
        execs_done = tar.get_num_execs()   # get number of executions that are finished in time
        plot_data = tar.load_plot(_reverse=True, _n_lines=2)
        stats = tar.load_stats_total_log(_remake=self.RECALCULATE_STATS)
        tar.close()
        counts = stats["counts"]
        elapsed = stats["elapsed"]

        # post-process for checking KILLED mutants
        if 'false_positives' in stats:
            counts['false'] = len(stats['false_positives'])

        # analysis plot data
        plot_result = self.check_fuzzing_result_from_plot_data(plot_data)

        # analysis customized log data
        if counts is None:
            self.print_line(_mutant, _runID, "ERR_LOG_OPEN")
            return [_mutant['ID'], _runID, "ERR_LOG_OPEN"]
        log_result = self.check_fuzzing_result_from_logs(counts, elapsed, execs_done, self.MAX_TIME)


        # print result
        self.print_line(_mutant, _runID, plot_result, execs_done, counts, log_result)
        return [_mutant['ID'], _runID, log_result['result']]

    #################################################
    # print data out
    #################################################
    def print_header(self):
        header = "Mutant ID,Filename,Run ID,Initial Result, Num Execs"
        header += ",All Inputs,Crash Initial,Crash Origin,Crash Mutant,Crash Comparison,False-Positive"
        header += ",Result,Crashed Time (s), Num Timeout,LAST_SEQ_ID"
        self.print(header)

    def print_line(self, mutant, runID, plot_result, execs_done=-1, counts:dict=None, log_result:dict=None):
        # add basic info
        line = "%d,%s,%s,%s,%s"%(mutant['ID'], mutant['name'], str(runID), plot_result, str(execs_done))

        # add counts
        line += ",%d" % (counts['all'] if counts is not None else 0)
        line += ",%d" % (counts['initial'] if counts is not None else 0)
        line += ",%d" % (counts['origin'] if counts is not None else 0)
        line += ",%d" % (counts['mutant'] if counts is not None else 0)
        line += ",%d" % (counts['comp'] if counts is not None else 0)
        line += ",%d" % (counts['false'] if counts is not None and 'false' in counts else 0)

        # add additional results
        line += ",%s" % (log_result['result'] if log_result is not None else "NO_TAR")
        line += ",%.3f" % (log_result['crashed_time']if log_result is not None else -1)
        line += ",%d" % (log_result['num_timeout']if log_result is not None else 0)
        line += ",%d" % (counts['seq'] if counts is not None else 0)
        self.print(line)

    def get_tar_object(self, _location, _tar_name):

        tar_temp_path = utils.makepath(_location, "__temp_tar__")
        if self.HPC is True:
            tar_temp_path = utils.makepath(self.HPC_TEMP_PATH, tar_temp_path)
        tar_filepath = os.path.join(_location, _tar_name)  # make a full path
        if os.path.exists(tar_filepath) is False: return "NOT_EXIST_TAR"

        try:
            tar = TarResult(tar_filepath, tar_temp_path, _use_AFL_plus=self.AFL_PLUS)
        except tarfile.ReadError as e:
            print(e)
            print("Cannot open")
            return "ERR_TAR_OPEN"
        return tar

    def make_statistics(self, _data):
        # make statistics
        count = {'LIVE':0, 'KILLED':0, 'CRASHED':0}
        for mutantID, runID, result in _data:
            # count for statistics
            if result not in count: count[result] = 0
            count[result] += 1

        # report statistics
        print("\n\n")
        print("Total mutants: %d" % (sum(count.values())))
        for key in count.keys():
            print("Total %s mutant: %d" % (key, count[key]))
        print("Done.")
        pass

    ###############################################################
    # checking fuzzing result from logs
    ###############################################################
    def check_fuzzing_result_from_logs(self, _counts, _elapsed, _execs_done, _maxTime):
        '''
        check the mutant is LIVE or KILLED (also crashed time and additional information for recording)
        :param _counts:
        :param _elapsed:
        :param _maxTime:
        :return:
        '''
        # calculate number of executions that are out of time
        num_timeout = (_counts['all'] - _execs_done) if _execs_done is not None else 0

        # check result state
        result = "LIVE"
        if _counts['comp'] > 0:    result = "KILLED"
        elif _counts['mutant'] > 0: result = "KILLED"
        elif _counts['origin'] > 0: result = "FAILED_IN_ORIGIN"

        # check crashed time
        crashed_time = _maxTime
        if _counts['comp'] > 0:    crashed_time = _elapsed['comp']
        elif _counts['mutant'] > 0: crashed_time = _elapsed['mutant']
        elif _counts['origin'] > 0: crashed_time = _elapsed['origin']

        # check false-positives
        if 'false' in _counts and _counts['false']>0:

            _counts['comp'] = max(_counts['comp'] - _counts['false'], 0)
            if _counts['comp'] == 0:
                result = "LIVE-ASSUMED"

        return {'result': result, 'crashed_time':crashed_time, "num_timeout":num_timeout}

    ###############################################################
    # checking fuzzing result from plot data
    ###############################################################
    def check_fuzzing_result_from_plot_data(self, _plot_data):
        # check whether the mutant is  killed or lived
        result = "ERROR"
        if _plot_data is not None:
            if len(_plot_data) == 0 : result = "NO_LINE"  # less than 1 cycle
            elif _plot_data[0]["unique_crashes"] > 0: result = "KILLED"
            elif _plot_data[0]["unique_crashes"] == 0: result = "LIVE"

        # Check result from the number of inputs (check whether crashed or not)
        if result == "NO_LINE":
            # AFL says CRASHED when it failed to execute SUT in perform_dry_run()
            # perform_dry_run() generates a set of inputs based on seed inputs
            # nInputs = _tar.get_num_execs()   # replaced _tar.get_number_of_inputs()
            # if nInputs is None: result = "ERROR"
            # elif nInputs > 0: result = "CRASHED"
            # nSeed = _tar.get_number_of_seeds()
            # if nInputs != -1 and nInputs <= nSeed:
            #     result = "CRASHED"
            # Changed to just to be crashed.
            result = "CRASHED" # when there is no line, fuzzer_stats file also does not exist

        return result

    ###############################################################
    # utils to get mutant runID from the tar file name
    ###############################################################
    def get_mutant_runID(self, _tar_name):
        '''
        get experiment run id from tar file name (single execution has the name as a mutant name)
        if we run multiple experiments, the tar file will be RunXXXX.tar
        otherwise, the tar file will be <mutant name>.tar.
        :param _tar_name:
        :return:
        '''
        onlyname = os.path.basename(_tar_name)[:-4]  # remove extension (.tar)
        cols = onlyname.split(".")
        if len(cols)>1:
            return None
        return int(cols[0][3:])   # remove 'Run'

    ###############################################################
    # utils for tar and mutant list
    ###############################################################
    def get_iter_mutants(self, _mutant_list_path):
        file = open(_mutant_list_path, "r")
        lines = file.readlines()
        file.close()

        mutantID = 0
        for line in lines:
            if line == "": continue
            mutantID += 1
            cols = line.split(";")
            mutant = cols[0].strip()
            mutant_path = os.path.dirname(mutant)
            mutant = os.path.basename(mutant)
            input_filter = ';'.join(cols[1:]).strip()
            yield {'ID':mutantID, 'name':mutant, 'path':mutant_path, 'filter':input_filter}
            # (, mutant, mutant_path, input_filter)
        return True

    def get_mutant_tarfiles(self, _mutant_name, _tarfiles):
        target_name = _mutant_name[:_mutant_name.rfind(".")]
        for afile in _tarfiles:
            name = os.path.basename(afile)[:-4]  # remove ".tar"
            if name == target_name: return [afile]

        # if failed to find a single file
        files = []
        for afile in _tarfiles:
            dirname = os.path.dirname(afile)
            name = os.path.basename(dirname)
            if name == target_name: files.append(afile)
        return files

    ########################################################
    # File writer manager
    ########################################################
    def open_output(self, _output):
        self.output = None
        self.records = []

        if _output is not None:
            self.output = open(_output, "w")
        pass

    def print(self, _msg):
        self.records.append(_msg)
        print("\t- "+_msg, flush=True)
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
        parser = argparse.ArgumentParser(description='Parameters')
        parser.add_argument('-b', dest='basePath', type=str, default=None, help='base path')
        parser.add_argument('-J', dest='expName', type=str, default=None, help='experiment name (job name)')
        parser.add_argument('-t', dest='tagName', type=str, default=None, help='sub dir pattern')
        parser.add_argument('-o', dest='outputPath', type=str, default=None, help='relative path from the base path')
        parser.add_argument('-m', dest='mutantsPath', type=str, default=None, help='target mutant file to fuzz; relative path from the base path')
        parser.add_argument('--time', dest='MAX_TIME', type=int, default=None, help='the maximum execution time of AFL fuzzing')
        parser.add_argument('--runs', dest='MAX_RUN', type=int, default=0, help='the maximum number of runs')
        parser.add_argument('--hpc', dest='HPC', action='store_true', help='(boolean) working in HPC (working in /tmp folder')
        parser.add_argument('--plus', dest='AFLplus', action='store_true', help='(boolean) the result made by AFL plus')
        parser.add_argument('--stats', dest='calculateStats', action='store_true', help='(boolean) the result made by AFL plus')

        # parameter parsing
        args = sys.argv[1:]  # remove executed file
        args = parser.parse_args(args=args)
        if args.basePath is None or len(args.basePath)==0:
            parser.print_help()
            exit(1)
        if args.expName is None or len(args.expName)==0:
            parser.print_help()
            exit(1)
        if args.mutantsPath is None or len(args.mutantsPath)==0:
            parser.print_help()
            exit(1)

        if args.MAX_TIME is None:
            parser.print_help()
            exit(1)

        return args


if __name__ == "__main__":
    RunCollector()
    pass
    ## Usages
    # ./tools/RunCollector.py -b case_studies/ASN1 -J _exp001 -m list/target_mutants --time 100 --plus
    # ./tools/RunCollector.py -b case_studies/ASN1 -J _exp001 -m list/target_mutants --time 100 --plus --hpc
    # ./tools/RunCollector.py -b case_studies/ASN1 -J _exp001 -m list/target_mutants --time 100 --runs 10 --plus --hpc

