from __future__ import absolute_import
import os
import sys
import shutil
import argparse

if __package__ is None or __package__ == "":
    import utils
    from mutant import Mutant
else:
    from pipeline import utils
    from pipeline import Mutant


class Config(utils.dotdict):

    def __init__(self, seq=None, **kwargs):
        super().__init__(seq, **kwargs)
        # dotdict class does not allow to define member variables
        # Instead, define variables in a function like below

        # for get_single_run_arguments_template function
        self.sysargs = sys.argv                # keep sys.args
        self.stored_argument_template = None   # reduce execution time
        pass

    @staticmethod
    def configure(_params, _multi=False):
        conf = Config.load_default_config(_params.CONFIG)

        obj = Config(vars(conf))
        obj.update_config_with_params(_params)
        obj.augment_config()

        if _multi is False:
            obj.configure_mutant_information(_params.MUTANT, _params.INPUT_FILTER)
        else:
            obj.configure_mutant_list(_params.MUTANT_LIST)
        return obj

    @staticmethod
    def parse_arg(_multi=False, _args=None):
        '''
        Parsing command line arguments
        # Please set PARAMETER DESTINATION VARIABLE NAMES in the upper case
        #    If the default value is None,
        #    the argument values will not replace the config file variables
        #    when the parameter is not provided from the command line.
        #    See the update_config_with_params() function
        :param _multi: if it is True, the arguments will be parsed for the ListRunner class
        :param _args: if it is not provided, this function parse arguments from the system library (sys.args)
        :return:
        '''
        # We do not allow abbreviation for the long options, users should use full option name
        parser = argparse.ArgumentParser(description='Parameters', allow_abbrev=False)
        # necessary parameters
        if _multi is False:
            parser.add_argument("MUTANT", metavar="<mutant-file>", help="target mutant file to fuzz")
            parser.add_argument("INPUT_FILTER", metavar="<input-filter>", help="semicolon separated list of input filters for a mutated function (N:negative, Z:zero, P:positive, A:all)\n e.g.: `N;Z`, `N;Z;P`, `A`")
        else:
            parser.add_argument("MUTANT_LIST", metavar="<mutant-list-file>", help="target mutant list file to fuzz")
        parser.add_argument("PHASE", metavar="<phase>", help="pipeline execution phase, select one among {'preprocess', 'build', 'run'}")
        parser.add_argument('-c', dest='CONFIG', type=str, default="config.py", help='config file that defines default parameter values')

        # optional parameters (related controlling run.py and run_list.py)
        if _multi is False:
            parser.add_argument('--runID', dest='RUN_ID', type=int, default=None, help='specified run identity to fuzz a mutant')
        else:
            parser.add_argument('--runs', dest='RUNS', type=int, default=None, help='number of runs to fuzz a mutant')
            parser.add_argument('--resume', dest='RESUME', type=int, default=1, help='number of job sequence, for HPC execution')
        parser.add_argument('--singularity', dest='SINGULARITY', action='store_true', help='(boolean) paramter whether the pipeline works on HPC or not. on HPC, the command will be executed in Singularity')
        parser.add_argument('--hpc', dest='HPC', action='store_true', help='(boolean) paramter whether the pipeline works on HPC or not. on HPC, the command will be executed in Singularity')
        # following parameters for the run_list.py, but run.py uses them for storing temporary files into the SSD (non-network drive)
        parser.add_argument('--parallel', dest='HPC_PARALLEL', action='store_true', help='(boolean) paramter whether the pipeline works in parallel on HPC')
        if _multi is True:
            parser.add_argument('--parallel-nodes', dest='N_PARALLELS_PER_JOB', type=int, default=None, help='(integer) number of tasks to be executed in parallel')
            parser.add_argument('--parallel-ntasks', dest='N_TASKS_PER_JOB', type=int, default=None, help='(integer) number of tasks to be executed in one parallel job')


        # following parameters for the run.py but run_list.py can provide
        parser.add_argument('--timeout', dest='FUZZING_TIMEOUT', type=int, default=None, help='timeout for fuzzing in seconds (e.g., 3600*3 for 3 hours)')
        parser.add_argument('--uncompress', dest='UNCOMPRESS_RESULT', action='store_true', help='(boolean) Uncompress the experiment results')
        parser.add_argument('--overwrite', dest='OVERWRITE', action='store_true', help='(boolean) Uncompress the experiment results')

        # optional parameters (related to paths)
        parser.add_argument('-b', dest='EXP_BASE', type=str, default=None, help='work base directory for the experiments data')
        parser.add_argument('-J', dest='EXP_NAME', type=str, default=None, help='experiment name and output folder name')
        parser.add_argument('-t', dest='EXP_TAG_NAME', type=str, default=None, help='experiment sub name and output path for fuzzing')

        # HPC parallel parameter
        parser.add_argument('--dependency', dest='DEPENDENCY', type=str, default=None, help='list of dependency IDs, format follows https://slurm.schedmd.com/sbatch.html. (e.g., "afterok:399912:399913" means that execute the current job if the jobs 399912 and  399913 finished successfully')
        parser.add_argument('--sbatch', dest='SBATCH_PARAMETERS', type=str, default=None, help='additional parameters for sbatch')

        # optional parameters (for debugging)
        parser.add_argument('--step', dest='STEP', type=int, default=None, help='build for the specific step (mutually exclusive with the stepfrom parameter)')
        parser.add_argument('--stepfrom', dest='STEP_FROM', type=int, default=None, help='build from the specific step (mutually exclusive with the step parameter)')

        # only works in the run_list.py
        parser.add_argument('--dry', dest='DRY_RUN', action='store_true', help='(boolean) Test without actual command execution')
        parser.add_argument('--noconfview', dest='NO_CONFIG_VIEW', action='store_true', help='(boolean) Do not show the configuration values')
        # parser.add_argument('--verbose', dest='VERBOSE', action='store_true', help='(boolean) Print detail results')

        # Parsing arguments
        args = sys.argv if _args is None else _args
        args = args[1:]  # remove executed file (as it is the name of source code file)
        args = parser.parse_args(args=args)
        return args

    @staticmethod
    def load_default_config(_config_file):
        # check the config file exists
        if os.path.exists(_config_file) is False:
            shutil.copy('./pipeline/_config.py', _config_file)
            utils.error_exit("This pipeline requires config file. \n Please take a look and update the auto generated config file: %s" % _config_file)

        return utils.load_module(_config_file)

    def update_config_with_params(self, _params):
        '''
        Overwrite config values from _params if the arguments (parameters) are not None
        :param _params:
        :return:
        '''
        param_dicts = vars(_params)
        for key, value in param_dicts.items():
            if value is None: continue
            self[key] = value

        # Add params that should be existed during pipeline process
        #    if it is not provided from _params, it should be None.
        if self.has_value("RUNS") is False:         self.RUNS = None
        if self.has_value("RUN_ID") is False:       self.RUN_ID = None
        if self.has_value("STEP") is False:         self.STEP = None
        if self.has_value("STEP_FROM") is False:    self.STEP_FROM = None
        if self.has_value("DEPENDENCY") is False:    self.DEPENDENCY = None
        if self.has_value("SBATCH_PARAMETERS") is False:    self.SBATCH_PARAMETERS = ""

        # specify special options
        # if parallel is on, HPC is on automatically
        if self.HPC_PARALLEL is True:  self.HPC = True

        # STEP parameter has higher priority than STEP_FROM
        if self.STEP is not None: self.STEP_FROM = None
        pass

    ###
    # generate additional configs for convineient
    ###
    def augment_config(self):
        # current working folder
        self.PIPELINE_DIR = os.getcwd()

        # Experiment paths setting
        self.REPO_FILE      = utils.makepath(self.EXP_BASE, self.REPO_FILE)
        self.REPO_PATH      = utils.makepath(self.EXP_BASE, self.REPO_PATH)
        self.MUTANTS_FILE   = utils.makepath(self.EXP_BASE, self.MUTANTS_FILE)

        # setting OUTPUT_PATH
        self.OUTPUT_PATH = utils.makepath(self.EXP_BASE, self.EXP_NAME)

        # set sub output paths
        self.FUNC_DRIVER_PATH    = utils.makepath(self.OUTPUT_PATH, self.FUNC_DRIVER_NAME)
        self.FUNC_INPUT_PATH     = utils.makepath(self.OUTPUT_PATH, self.FUNC_INPUT_NAME)
        self.MUTANT_FUNC_PATH    = utils.makepath(self.OUTPUT_PATH, self.MUTANT_FUNC_NAME)
        self.MUTANT_BIN_PATH     = utils.makepath(self.OUTPUT_PATH, self.MUTANT_BIN_NAME)

        fuzzing_name = self.FUZZING_OUTPUT_NAME
        verify_name = self.VERIFY_OUTPUT_NAME
        if self.has_value('EXP_TAG_NAME'):
            fuzzing_name = fuzzing_name + "-" + self.EXP_TAG_NAME
            verify_name = verify_name + "-" + self.EXP_TAG_NAME
        self.FUZZING_OUTPUT_PATH = utils.makepath(self.OUTPUT_PATH, fuzzing_name)
        self.VERIFY_OUTPUT_PATH = utils.makepath(self.OUTPUT_PATH, verify_name)

        # HPC setting
        self.JOB_NAME = self.EXP_NAME
        if self.has_value('EXP_TAG_NAME'):
            self.JOB_NAME = "%s-%s" % (self.EXP_NAME, self.EXP_TAG_NAME)
        if self.has_value('PHASE'):
            self.JOB_NAME = "%s-%s" % (self.JOB_NAME, self.PHASE.lower())

        # HPC log output path setting
        self.HPC_LOG_PATH = utils.makepath(self.OUTPUT_PATH, self.HPC_LOG_PREFIX)
        if self.has_value('EXP_TAG_NAME'):
            log_nmae = "%s-%s" % (self.HPC_LOG_PREFIX, self.EXP_TAG_NAME)
            self.HPC_LOG_PATH = utils.makepath(self.OUTPUT_PATH, log_nmae)

        # HPC temporary directory setting
        self.HPC_BUILD_BASE = utils.makepath(self.HPC_WORK_PATH, "repos")
        if self.has_value('EXP_TAG_NAME'):
            self.HPC_EXEC_BASE = utils.makepath(self.HPC_WORK_PATH, self.EXP_NAME, self.EXP_TAG_NAME)
        else:
            self.HPC_EXEC_BASE = utils.makepath(self.HPC_WORK_PATH, self.EXP_NAME, "__base__")

        # remove unnecessary variables
        del self['FUNC_DRIVER_NAME']
        del self['FUNC_INPUT_NAME']
        del self['MUTANT_FUNC_NAME']
        del self['MUTANT_BIN_NAME']
        del self['FUZZING_OUTPUT_NAME']
        del self['VERIFY_OUTPUT_NAME']
        pass

    def configure_mutant_information(self, _mutant_name, _input_filter):
        # configure MUTANT information
        # If the mutant has only the mutant name, get the whole path in the case study mutants folder
        if os.path.dirname(_mutant_name) == "":
            target = utils.find_fullpath_in_tar(_mutant_name, self.MUTANTS_FILE) #, '*.%s.*.c'%self.MUTANT_FUNC_PREFIX)
            if target is None:
                utils.error_exit("Cannot find the mutant in the MUTANTS_FILE: %s"% _mutant_name)
            _mutant_name = target

        # Parsing mutant information
        self.MUTANT = Mutant.parse(_mutant_name)

        # set input filter for a function
        self.INPUT_FILTER_ALL = ["negative", "zero", "positive"]

        # set input filter for the mutation testing
        self.INPUT_FILTER = set() # This filter can have subset of {"negative", "zero", "positive"}
        filters = _input_filter.split(";")
        for filter in filters:
            if filter.upper() == "A" or filter.upper() == "N" or filter.lower() == "negative":
                self.INPUT_FILTER.add("negative")
            if filter.upper() == "A" or filter.upper() == "Z" or filter.lower() == "zero":
                self.INPUT_FILTER.add("zero")
            if filter.upper() == "A" or filter.upper() == "P" or filter.lower() == "positive":
                self.INPUT_FILTER.add("positive")
        pass

    def configure_mutant_list(self, _mutant_list):
        self.MUTANT_LIST = _mutant_list

        # Especially apply the mutant list to be under EXP_BASE
        # if self.is_relative_path(self.MUTANT_LIST) is True:
        #     self.MUTANT_LIST = utils.makepath(self.EXP_BASE, self.MUTANT_LIST)

        # set all input filters
        self.INPUT_FILTER_ALL = ["negative", "zero", "positive"]
        pass

    def verify_config(self, _multi=False):
        # check valid phase
        valid_phases = ["preprocess", "build", "run", "all", "verify"]
        if self.PHASE not in valid_phases:
            utils.error_exit("The pipeline has no `%s` phase. Please select one of the %s" % (self.PHASE, str(valid_phases)))

        # verify repository directory
        if os.path.exists(self.EXP_BASE) is False:
            utils.error_exit("failed to find BASE working directory: %s" % self.EXP_BASE)

        # verify repository directory
        if os.path.exists(self.REPO_FILE) is False:
            utils.error_exit("failed to reach repository directory: %s" % self.REPO_FILE)

        # verify mutants directory
        if os.path.exists(self.MUTANTS_FILE) is False:
            utils.error_exit("failed to reach the archive of mutants: %s" % self.MUTANTS_FILE)

        # verify target source code
        if _multi is True:
            list_file = utils.makepath(self.MUTANT_LIST)
            if os.path.exists(list_file) is False or os.path.isfile(list_file) is False:
                utils.error_exit("The file that contains a list of mutants does not exist: %s" % list_file)
        else:
            if utils.exists_in_tar(self.MUTANT.src_path, self.REPO_FILE) is False:
                utils.error_exit("The specified source does not exist in the repository: %s" % self.MUTANT.src_path)

            # verify AFL fuzzer
            if os.path.exists(self.FUZZER_FILEPATH) is False:
                utils.error_exit("No fuzzer exists. Please build the fuzzer or check the path: %s" % self.FUZZER_FILEPATH)
            else:
                if os.access(self.FUZZER_FILEPATH, os.X_OK) is False:
                    utils.error_exit("The fuzzer is not executable. Please check the access right of %s" % self.FUZZER_FILEPATH)

            # verify AFL compiler
            if utils.is_global_command(self.COMPILER_FILEPATH) is False:
                if os.path.exists(self.COMPILER_FILEPATH) is False:
                    utils.error_exit("No compiler exists. Please build the fuzzer: %s" % self.COMPILER_FILEPATH)
                else:
                    if os.access(self.COMPILER_FILEPATH, os.X_OK) is False:
                        utils.error_exit("The compiler is not executable. Please check the access right of %s" % self.COMPILER_FILEPATH)
            else:
                if utils.exist_global_command(self.COMPILER_FILEPATH) is False:
                    utils.error_exit("Cannot found COMPILER_FILEPATH. Please check the command: %s" % self.COMPILER_FILEPATH)

            # verify gcc
            if self.PHASE == "build" and utils.exist_global_command("gcc") is False:
                utils.error_exit("Cannot found `gcc`. Please install `gcc` in this OS")

        # Check for read access
        # os.access('my_file', os.W_OK) # Check for write access
        # os.access('my_file', os.X_OK) # Check for execution access
        # os.access('my_file', os.F_OK) # Check for existence of file
        self.verify_template_config()
        pass

    def print_config(self, _multi=False):
        # keys = self.keys()
        # keys = set([key for key in keys if key.startswith("__") is False]) - set(['PIPELINE_DIR'])
        #
        # hpc_keys = set([key for key in keys if key.startswith("HPC")])
        # keys -= hpc_keys
        #
        # path_keys = set([key for key in keys if key.endswith("PATH") or key.endswith("NAME") or key.endswith("BASE") or key.startswith("REPO")])
        # keys -= path_keys
        #
        # template_keys = set([key for key in keys if key.startswith("TEMPLATE")])
        # keys -= template_keys
        #
        # mutant_keys = set([key for key in keys if key.startswith("MUTANT")])
        # keys -= mutant_keys
        #
        # boolean_keys = set([key for key in keys if isinstance(self[key], bool)])
        # keys -= boolean_keys
        #
        # print("######################################################################")
        # print("  - %-25s: %s" % ("The pipeline root", self.PIPELINE_DIR))
        # print("[PATHs]")
        # for key in sorted(path_keys):       print("  - %-25s: %s" % (key, self[key]))
        # print("[MUTANT]")
        # for key in sorted(mutant_keys):     print("  - %-25s: %s" % (key, self[key]))
        # print("[TEMPLATEs]")
        # for key in sorted(template_keys):   print("  - %-25s: %s" % (key, self[key]))
        # print("[HPCs]")
        # for key in sorted(hpc_keys):        print("  - %-25s: %s" % (key, self[key]))
        # print("[Booleans]")
        # for key in sorted(boolean_keys):    print("  - %-25s: %s" % (key, self[key]))
        # print("[Others]")
        # for key in sorted(keys):            print("  - %-25s: %s" % (key, self[key]))
        # print("######################################################################")
        # print("")
        # print("")

        print("######################################################################")
        print("  - The Pipeline root     : %s" % self.PIPELINE_DIR)
        print("[Experiment working folders and files]")
        print("  - EXP_BASE              : %s" % self.EXP_BASE)
        print("  - REPO_FILE             : %s" % self.REPO_FILE)
        print("  - REPO_PATH             : %s" % self.REPO_PATH)
        print("  - MUTANTS_FILE          : %s" % self.MUTANTS_FILE)
        print("  - OUTPUT_PATH           : %s" % self.OUTPUT_PATH)
        print("  - FUNC_DRIVER_PATH      : %s" % self.FUNC_DRIVER_PATH)
        print("  - FUNC_INPUT_PATH       : %s" % self.FUNC_INPUT_PATH)
        print("  - MUTANT_FUNC_PATH      : %s" % self.MUTANT_FUNC_PATH)
        print("  - MUTANT_BIN_PATH       : %s" % self.MUTANT_BIN_PATH)
        print("  - FUZZING_OUTPUT_PATH   : %s" % self.FUZZING_OUTPUT_PATH)
        print("[Fuzzer]")
        print("  - FUZZER                : %s" % self.FUZZER_FILEPATH)
        print("  - COMPILER              : %s" % self.COMPILER_FILEPATH)
        print("  - TEST_EXEC_TIMEOUT     : %d" % self.TEST_EXEC_TIMEOUT)
        print("  - FUZZER_PRINT_LOG_DETAILS: %s" % self.FUZZER_PRINT_LOG_DETAILS)
        print("  - FUZZER_PRINT_INPUTS   : %s" % self.FUZZER_PRINT_INPUTS)
        print("  - FUZZER_PRINT_CRASHES  : %s" % self.FUZZER_PRINT_CRASHES)
        print("[Template]")
        print("  - TEMPLATE_ROOT_DIR       : %s" % self.TEMPLATE_ROOT_DIR)
        print("  - TEMPLATE_FUZZING_DRIVER : %s" % self.TEMPLATE_FUZZING_DRIVER)
        print("  - TEMPLATE_PRESENTER_DRIVER: %s" % self.TEMPLATE_PRESENTER_DRIVER)
        print("  - TEMPLATE_TESTCASE_DRIVER: %s" % self.TEMPLATE_TESTCASE_DRIVER)
        print("  - TEMPLATE_CONFIG         : %s" % self.TEMPLATE_CONFIG)
        print("[SUT Compilation]")
        print("  - SUT_COMPILE_FLAGS       : %s" % self.SUT_COMPILE_FLAGS)
        print("  - INCLUDES                : %s" % self.INCLUDES)
        print("  - COMPILE_SUT_FILES       : %s" % self.COMPILE_SUT_FILES)
        print("  - COMPILE_SUT_CMDS        : %s" % self.COMPILE_SUT_CMDS)
        print("  - COMPILED_OBJECTS        : %s" % self.COMPILED_OBJECTS)
        print("[Executions]")
        print("  - PHASE                 : %s" % self.PHASE)
        print("  - EXP_NAME              : %s" % self.EXP_NAME)
        print("  - EXP_TAG_NAME          : %s" % self.EXP_TAG_NAME)

        print("  - MUTANT_FUNC_PREFIX    : %s" % self.MUTANT_FUNC_PREFIX)
        print("  - INPUT_FILTER_ALL      : %s" % self.INPUT_FILTER_ALL)
        if _multi is False:
            print("  - INPUT_FILTER          : %s" % self.INPUT_FILTER)
        print("  - - - - - - - - - - - - ")
        print("  - SINGULARITY           : %s" % self.SINGULARITY)
        print("  - SINGULARITY_FILE      : %s" % self.SINGULARITY_FILE)
        print("  - FUZZING_TIMEOUT       : %s" % self.FUZZING_TIMEOUT)
        print("  - COMPRESS_RESULT       : %s" % self.COMPRESS_RESULT)
        if _multi is False:
            print("  - RUN_ID                : %s" % self.RUN_ID)
        else:
            print("  - Number of RUNS        : %s" % self.RUNS)
            print("  - RESUME                : %s" % self.RESUME)

        #### showing mutant information
        if _multi is False:
            self.MUTANT.print()
        else:
            print("  - - - - - - - - - - - - ")
            print("  - MUTANT_LIST           : %s" % self.MUTANT_LIST)
        print("  - STEP                  : %s" % self.STEP)
        print("  - STEP_FROM             : %s" % self.STEP_FROM)

        # the number of tasks in one parallel job
        print("[HPC Settings]")
        if _multi is True:
            print("  - HPC                   : %s" % self.HPC)
        print("  - HPC_LOG_PATH          : %s" % self.HPC_LOG_PATH)
        print("  - HPC_BUILD_BASE        : %s" % self.HPC_BUILD_BASE)
        print("  - HPC_EXEC_BASE         : %s" % self.HPC_EXEC_BASE)
        print("  - HPC_WORK_PATH         : %s" % self.HPC_WORK_PATH)
        print("  - LOG_FILE_NAME         : %s" % self.LOG_FILE_NAME)
        print("  - SBATCH_PARAMETERS     : %s" % self.SBATCH_PARAMETERS)
        print("[Parallel settings]")
        print("  - HPC_PARALLEL          : %s" % self.HPC_PARALLEL)
        print("  - JOB_NAME              : %s" % self.JOB_NAME)
        print("  - N_TASKS_PER_JOB       : %s" % self.N_TASKS_PER_JOB)
        print("  - N_PARALLELS_PER_JOB   : %s" % self.N_PARALLELS_PER_JOB)
        print("  - REPORT_EMAIL          : %s" % self.REPORT_EMAIL)
        print("  - SBATCH_PARAMETERS     : %s" % self.SBATCH_PARAMETERS)
        print("  - PYTHON_CMD            : %s" % self.PYTHON_CMD)
        print("  - SINGLE_RUN_FILE       : %s" % self.SINGLE_RUN_FILE)
        print("  - MULTI_RUN_FILE        : %s" % self.MULTI_RUN_FILE)
        print("  - SLURM_PARALLEL_EXECUTOR:%s" % self.SLURM_PARALLEL_EXECUTOR)
        print("  - SLURM_SINGLE_EXECUTOR : %s" % self.SLURM_SINGLE_EXECUTOR)
        print("[Others]")
        print("######################################################################")
        print("")
        print("")

        sys.stdout.flush()
        pass

    def verify_template_config(self):
        default_usage = '''\nPlease check the following example:
        TEMPLATE_CONFIG = { 
            "DEFAULT_ARRAY_SIZE": 100,
            "PARAMETER_FORMAT": [
                {'function': function0, 'parameter':'parameter_name0', type':'int', 'size': 100},"       # replace int[100]
                {'function':'function1','parameter':'parameter_name1', 'size':21, 'format':'ISO8601'},   # replace <original pointee type>[21]
            ]
            'INPUT_VALUES_MAP': {
                "default":  {"N":-1, "Z":0, "P":1},
                "char":     {"N":b'\xFF', "Z":b'\x00', "P":b'\x41'},
                "ISO8601":  {"N":"2145916800.999999999", "Z":"1970-01-01T00:00:00Z", "P":"2038-01-01T00:00:00Z"},
            }
            'STRUCT_FIELD_BUFFER':{
                     'BitStream': {
                            "user_fields":[ {"name": "buf", "type": "byte", "size": 2000, "string": 1, "print_format": "%s"}, 
                                            {"name": "pushDataPrm", "type": "byte", "size": 2000, "string": 1, "print_format": "%s"},
                                            {"name": "fetchDataPrm", "type": "byte", "size": 2000, "string": 1, "print_format": "%s"}],
                            "before_statements": ""
                            "after_statements": "BitStream_Init2(&{param}, {field.1}, {size.1}, {field.2}, {field.3});",
                     },
            },
            'INITIALIZE':{"source code filepath":["statement","statement", ...],},
            'NO_EXTERNS': [ {"file":"", "function":""}, ... ]
            
        } 
        
        '''
        item_format = {
            "AUTO_EXCLUDE_HEADERS":bool,
            "EXCLUDE_HEADERS":list,
            "DEFAULT_ARRAY_SIZE":int,
            "PARAMETER_FORMAT":list,
            "INPUT_VALUES_MAP":dict,
            "STRUCT_FIELD_BUFFER":dict,
            "INITIALIZE":dict,
            "NO_EXTERNS":list,
        }

        # missing config keys
        diff = item_format.keys() - self.TEMPLATE_CONFIG.keys()
        assert len(diff) == 0, "Missing config key: {}\n{}".format(diff, default_usage)

        for k, v in self.TEMPLATE_CONFIG.items():
            assert k in item_format.keys(), "Invalid config key: {}.\n{}".format(k, default_usage)
            assert type(v) == item_format[k], "Data type of {} is not correct.\n{}".format(k, default_usage)

        # check the PARAMETER_FORMAT grammar
        for item in self.TEMPLATE_CONFIG["PARAMETER_FORMAT"]:
            assert isinstance(item, dict), "Invalid data type of: {}.\nPlease check the following usages:\n{}".format(item, default_usage)
            # if 'type' in item:
            #     assert not ('file' in item or 'function' in item or 'parameter' in item), \
            #         "Invalid key values in: {}.\nPlease check the following usages:\n{}".format(item, default_usage)
            #     assert type(item['type']) == str and len(item['type']), \
            #         "Invalid data type of item: {}.\nPlease check the following usages:\n{}".format(item, default_usage)

            if 'parameter' in item:
                # assert ('type' not in item), \
                #     "Invalid key values in: {}.\nPlease check the following usages:\n{}".format(item, default_usage)
                assert ('function' in item), \
                    "Invalid key values in: {}.\nPlease check the following usages:\n{}".format(item, default_usage)
                if 'file' in item:
                    assert type(item['file']) in [type(None), str] and type(item['function']) == str and type(item['parameter']) == str, \
                        "Invalid value of the key: {}.\nPlease check the following usages:\n{}".format(item, default_usage)

            assert ('size' in item and 'format' in item), \
                "Missing expected key values in: {}.\nPlease check the following usages:\n{}".format(item, default_usage)

        # check the STRUCT_FIELD_BUFFER grammar
        for k, v in self.TEMPLATE_CONFIG["STRUCT_FIELD_BUFFER"].items():
            assert isinstance(v, dict), "Invalid data type: '{}' in STRUCT_FIELD_BUFFER\n{}".format(k, default_usage)
            diff = set(["user_fields", "before_statements", "after_statements"]) - v.keys()
            assert len(diff) == 0, "Invalid key values: '{}' in STRUCT_FIELD_BUFFER\n{}".format(k, default_usage)
            assert isinstance(v['user_fields'], list), "Invalid data type of 'fields': '{}' in STRUCT_FIELD_BUFFER\n{}".format(k, default_usage)
            for item in v['user_fields']:
                diff = set(["name", "type", "size"]) - item.keys()
                assert len(diff) == 0, "Invalid key values of field item: '{}' in STRUCT_FIELD_BUFFER\n{}".format(k, default_usage)

        # check the INPUT_VALUES_MAP grammar
        for k, v in self.TEMPLATE_CONFIG["INPUT_VALUES_MAP"].items():
            assert isinstance(v, dict), "Invalid data type of: '{}' in INPUT_VALUES_MAP\n{}".format(k, default_usage)
            diff = set(['N', 'Z', 'P']) - v.keys()
            assert len(diff) == 0, "Missing values filter key: '{}' in INPUT_VALUES_MAP\n{}".format(k, default_usage)

        # format consistency check
        user_defined_format_list = set([item['format'] for item in self.TEMPLATE_CONFIG["PARAMETER_FORMAT"]])
        user_defined_format_list -= set([None])
        input_template_keys = set(self.TEMPLATE_CONFIG["INPUT_VALUES_MAP"].keys())
        diff = user_defined_format_list - input_template_keys
        assert len(diff) == 0, "Missing values in INPUT_VALUES_MAP that is used in the PARAMETER_FORMAT: {}\n{}".format(diff, default_usage)
        return True

    #############################################
    # Utilities
    #############################################
    def is_relative_path(self, _path):
        if _path.startswith("./") is True:
            return True
        elif _path.startswith("../") is True:
            return True
        elif _path.startswith("/") is False:
            return True
        return False

    def get_single_run_arguments_template(self):
        if self.stored_argument_template is None:
            args = self.sysargs.copy()

            # Set main source file
            args[0] = self.SINGLE_RUN_FILE

            # remove not used parameters in run.py
            idx = 0
            while idx < len(args):
                if args[idx] in ["--runs", "--resume", "--dependency", "--parallel-ntasks", "--parallel-nodes", "--sbatch"]:
                    del args[idx+1]  # value of the parameter
                    del args[idx]    # parameter key
                    continue
                if args[idx] in ["--hpc", "--dry", "--singularity"]:
                    del args[idx]    # parameter key
                    continue
                idx += 1

            # change necessary parameters for run.py
            del args[-2]   # remove mutant_list
            args.insert(-1, "mutant")
            args.insert(-1, "A")
            self.stored_argument_template = args
        return self.stored_argument_template.copy()
