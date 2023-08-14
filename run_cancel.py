#! /usr/bin/env python3
import os
import platform
if platform.python_version().startswith("3.") is False:
    raise Exception("Must be using Python 3")
from pipeline import Config
from pipeline import utils


###
# This class is for the HPC to cancel submitted jobs
# to do this, you need to specify the following four parameters be same with the one that used for ./run_list.py
#       : EXP_NAME, EXP_TAG_NAME, MUTANT_LIST, PHASE
# For example, if you executed ./run_list.py with the following command:
#        ./run_list.py --hpc --parallel -J test -t 10ks case_studies/ASN1/live_mutant preprocess
# ./run_cancel.py would be as below:
#        ./run_cancel.py -J test -t 10ks case_studies/ASN1/live_mutant preprocess
###
class RunCancel(object):

    def __init__(self):
        # Load config file and set the values
        global confList
        params = Config.parse_arg(_multi=True)
        confList = Config.configure(params, _multi=True)
        confList.print_config(_multi=True)
        confList.verify_config(_multi=True)

        self.execute()
        pass

    def execute(self):
        jobIDs = self.load_jobIDs()
        if len(jobIDs)==0:
            print("No list of job IDs.")
            return

        for jobID in jobIDs:
            cmd = "scancel %d" % (jobID)
            if confList.DRY_RUN is True:
                print('\n'+cmd)
                continue
            print("execute: "+cmd)
            utils.shell.execute_and_check(cmd, 'retcode', 0, _verbose=True)
        return True

    def get_jobs_path(self):
        filepath = utils.makepath(confList.LIST_JOBID_PATH, confList.JOB_NAME+".list")
        return filepath

    def load_jobIDs(self):
        filepath = self.get_jobs_path()
        if os.path.exists(filepath) is False:
            print("Not found the job list file: %s"%filepath)
            return []

        f = open(filepath, "r")
        lines = f.readlines()
        f.close()

        jobIDs = []
        for line in lines:
            if line.strip() == "": continue
            jobIDs.append(int(line.strip()))
        return jobIDs


if __name__ == "__main__":
    obj = RunCancel()
    exit(0)