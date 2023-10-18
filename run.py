#! /usr/bin/env python3
import os
import shutil
import sys
import json
import platform
import traceback
if platform.python_version().startswith("3.") is False:
    raise Exception("Must be using Python 3")

import math
from pipeline.FunctionExtractor import FunctionExtractor
from pipeline.TemplateGenerator import TemplateGenerator
from pipeline.InputGenerator import InputGenerator
from pipeline.PathHelper import PathHelper
from pipeline.fuzzer import AFLOutput
from pipeline import utils
from pipeline import compile
from pipeline import Config


class Runner(object):
    path:PathHelper = None
    config:Config = None
    AFLpp:bool = False

    #######################################################
    # initialization all the member variables
    #######################################################
    def __init__(self, _args=None):
        # Load config file and set the values
        global config
        params = Config.parse_arg(_args=_args)
        config = Config.configure(params)
        if config.NO_CONFIG_VIEW is False:
            config.print_config()
        config.verify_config()

        global path
        path = PathHelper(config)

        self.AFLpp = self.check_AFL_plusplus()

        # proceed each phase
        if config.PHASE in ["all", "preprocess"]:
            self.preprocess()
        if config.PHASE in ["all", "build"]:
            self.build()
        if config.PHASE in ["all", "fuzzing"]:
            self.fuzzing()
        if config.PHASE in ["all", "gen"]:
            self.generate()
        pass

    def does_execute_this_step(self, _step):
        '''
        check configuration whether we execute the specified step or not
        :param _step:
        :return:
        '''
        if config.STEP_FROM is not None:
            return True if _step >= config.STEP_FROM else False

        if config.STEP is not None:
            return True if config.STEP == _step else False

        return True

    ################################################
    # preprocess phase
    ################################################
    def preprocess(self):
        '''
        preprocess for the `build` phase
        :return:
        '''
        # clone repository
        config.REPO_PATH = self.prepare_repository()

        # step 1
        if self.does_execute_this_step(_step=1):
            ret = self.generate_driver_for_function()
            if ret is False:
                print("Failed to generate test driver for functions")
                return False

        print("Finished to generate test driver for functions")
        print("Please go with `build` phase", flush=True)
        return True

    ################################################
    # build phase
    ################################################
    def build(self):
        '''
        Build procedure for AFL fuzzing
        :return:
        '''
        # sanity check
        func_driver_dir = path.get_func_driver_path()
        if os.path.exists(func_driver_dir) is False:
            print('Cannot find the test driver for the function. Please do `preprocess`.')
            utils.error_exit("Test driver path: %s" % func_driver_dir)

        # clone repository (Can be changed to the temporary folder)
        config.REPO_PATH = self.prepare_repository()

        # step 1
        if self.does_execute_this_step(_step=1):
            self.extract_mutated_function()

        # step 2
        if self.does_execute_this_step(_step=2):
            print("[Step 2] Injecting mutant into SUT...")
            self.generate_binary_SUT(_inject_mutant=True)

        # step 3.1 (compile a test driver for AFL++)
        if self.does_execute_this_step(_step=3):
            self.compile_test_entry()
            self.compile_test_entry(path.PRESENTER_PREFIX)
            self.compile_test_entry(path.EXPECTED_PREFIX)
            if 'TEMPLATE_FALSE_POSITIVE_DRIVER' in config:
                self.compile_test_entry(path.FALSE_POSITIVE_PREFIX)
            # if 'TEMPLATE_DEPENDENCY_DRIVER' in config:
            #     self.compile_test_entry(path.DEPENDENCY_PREFIX)

        # if config.CLONE_REPO is True:
        #     print("Removing the repository directory: %s ..."% config.REPO_PATH, flush=True)
        #     shutil.rmtree(config.REPO_PATH, ignore_errors=True)

        print("Finished building executable SUT and input files")
        print("Please fun fuzzer!!", flush=True)
        return True

    ################################################
    # fuzzing phase
    ################################################
    def fuzzing(self):
        '''
        execute AFL fuzzing
        :return:
        '''
        # determine output and working dir
        fuzzing_output = path.get_fuzzing_output_path()
        temp_output = path.get_HPC_temporary_path(fuzzing_output)  # if executed in HPC, output_dir is changed
        utils.prepare_directory(temp_output)
        print("fuzzing_output: " + fuzzing_output)
        print("temp_output: " + temp_output)

        # set input paths and check
        func_input_dir = path.get_func_input_path()
        test_driver_file = path.get_executable_driver_path()

        if os.path.exists(func_input_dir) is False:
            utils.error_exit("Cannot find the input folder. Please do `build` phase first")

        if os.path.exists(test_driver_file) is False:
            utils.error_exit("Cannot find the object file. Please do `build` phase first")

        # execute fuzzer
        if self.execute_fuzzer(func_input_dir, temp_output, test_driver_file) is False:
            utils.error_exit("Failed to execute fuzzer: %s" % test_driver_file)

        # make stats of the fuzzer results
        KILLED = 0
        try:
            KILLED = self.postprocess(temp_output)

        except Exception as e:
            print(e)
            print("Error in doing Post-processing !")

        # compress the execution result
        if config.UNCOMPRESS_RESULT is False:
            print("Compressing the execution results ...")
            utils.compress_directory(temp_output, os.path.dirname(fuzzing_output), _remove=True)

        if KILLED > 0:
            print("MOTIF: Killed the mutant: %s" % config.MUTANT.name)
        else:
            print("MOTIF: Failed to kill the mutant: %s" % config.MUTANT.name)
        print("Finished fuzzing")
        pass

    ################################################
    # gen phase
    ################################################
    def generate(self):
        '''
        execute AFL fuzzing
        :return:
        '''
        # clone repository
        config.REPO_PATH = self.prepare_repository()

        # determine output and working dir for 'run' phase
        fuzzing_output = path.get_fuzzing_output_path()
        temp_output = path.get_HPC_temporary_path(fuzzing_output)  # if executed in HPC, output_dir is changed
        print("run_output_dir: "+fuzzing_output)
        print("working_dir: "+temp_output)

        # if UNCOMPRESS_RESULT flag is False, we assume that users did 'run' phase without UNCOMPRESS_RESULT
        if config.UNCOMPRESS_RESULT is False:
            result_file = fuzzing_output + ".tar"
            print("result_file: "+result_file)
            print("Uncompressing to %s" % temp_output, flush=True)
            if utils.uncompress_tar_in_dir(result_file, temp_output) is False:
                utils.error_exit("Cannot find the result file or directory. Please do `fuzzing` phase first")

        if os.path.exists(temp_output) is False:
            utils.error_exit("Error: cannot find the working directory for fuzzing.")

        # prepare input resources
        afl = AFLOutput(temp_output, _isAFLpp=self.AFLpp)
        input_dir = afl.input_dir_path
        source_file = path.get_source_file_path()

        # prepare output directory
        testcase_output = path.get_testcase_output_path()
        result_generated = False

        # check input files in the working directory
        if os.path.exists(input_dir) is False:
            print("No test inputs in the %s" % input_dir)
        else:
            print("Executing test inputs killing mutant ... ", end='')
            self.present_results(input_dir, testcase_output, path.PRESENTER_PREFIX, _result_prefix="inputs")
            self.present_results(input_dir, testcase_output, path.FALSE_POSITIVE_PREFIX, _result_prefix="inputs")
            print("Done")
            result_generated = True

        false_dir = utils.makepath(temp_output, "falses")
        if os.path.exists(false_dir) is False:
            print("No false-positive inputs in the  %s" % false_dir)
        else:
            print("Executing test inputs killing mutant but identified as false positive ...", end='')
            self.present_results(false_dir, testcase_output, path.PRESENTER_PREFIX, _result_prefix="falses")
            self.present_results(false_dir, testcase_output, path.FALSE_POSITIVE_PREFIX, _result_prefix="falses")
            print("Done")
            result_generated = True

        # generate test cases
        testcase_dir = utils.makepath(testcase_output, "testcases")
        print("Generate test cases ...")
        ninputs, failed = self.generate_testcases(source_file, temp_output, testcase_dir)
        print("Generated test cases: %d / %d" % (ninputs-failed, ninputs))
        if failed > 0:
            print("Failed to generate test cases!")

        # For the successfully generated test cases
        if ninputs-failed > 0:
            result_generated = True
            if config.COMPILE_TESTCASES is True:
                print("Compile test cases ...")
                self.compile_testcases(testcase_dir)
                print("Execute test cases ...")
                self.execute_testcases(testcase_dir, testcase_output)

            # compress results
            if config.COMPRESS_TESTCASES is True:
                print("Compressing the testcase files ...")
                utils.compress_directory(testcase_dir, _remove=True)

        # Organizing execution results
        #    When working in HPC, we are working in the temporary directory
        if config.UNCOMPRESS_RESULT is False:
            # close the temporary results
            print("Removing the temporary results ...")
            shutil.rmtree(temp_output)

        if result_generated is True:
            print("Please find the results: %s" % testcase_output)
        else:
            print("Please find the results: No inputs killing the mutant (at least false-positive)" )
        print("Finished test case generation phase")
        pass

    def uncompress_result(self, fuzzing_output, temp_output):
        if config.UNCOMPRESS_RESULT is False:
            result_file = fuzzing_output + ".tar"
            print("result_file: "+result_file)
            print("Uncompressing to %s" % temp_output, flush=True)
            if utils.uncompress_tar_in_dir(result_file, temp_output) is False:
                utils.error_exit("Cannot find the result file or directory. Please do `fuzzing` phase first")

    ################################################
    # Clone repository
    ################################################
    def prepare_repository(self, _runID=None):
        # determine the target directory for the repository
        temp_repo_dir = path.get_repo_path()

        print("Preparing code repository...")
        if os.path.exists(temp_repo_dir) is False:
            print("\tUncompressing to %s" % temp_repo_dir, flush=True)
            # copy the repository
            utils.uncompress_tar_in_dir(config.REPO_FILE, temp_repo_dir)
        else:
            print("\tRepository exists: %s" % temp_repo_dir)
        print("Done", flush=True)
        return temp_repo_dir

    ################################################
    # Step 1 (preprocess): generate template
    ################################################
    def generate_driver_for_function(self):
        func_driver_dir = path.get_func_driver_path()
        print("[Step 1] Generating test driver for the mutated function into %s ..."% func_driver_dir)

        # Path setting
        src_file        = path.get_source_file_path()
        driver_src_file = path.get_driver_src_path()
        func_input_dir = path.get_func_input_path()

        # check if the driver source file already exists
        if (os.path.exists(driver_src_file) is True and config.OVERWRITE is False): return True

        # prepare parameters for the TemplateGenerator
        include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
        compilation_cflags = config.SUT_COMPILE_FLAGS+" " + include_txt
        # print(compilation_cflags)

        # generate fuzzing driver
        generator = TemplateGenerator(src_file, config, compilation_cflags)
        if generator.generate(config.MUTANT.func, driver_src_file, config.TEMPLATE_FUZZING_DRIVER) is False:
            return False

        # generate input files
        InputGenerator(config.TEMPLATE_CONFIG).generate(generator.prototypes[config.MUTANT.func], func_input_dir)
        print("Generated input files for {} in {}".format(config.MUTANT.func, func_input_dir))

        # generate presenter driver
        driver_src_file = path.get_driver_src_path(_appendix=path.PRESENTER_PREFIX)
        if generator.generate(config.MUTANT.func, driver_src_file, config.TEMPLATE_PRESENTER_DRIVER) is False:
            return False

        # generate expected driver
        driver_src_file = path.get_driver_src_path(_appendix=path.EXPECTED_PREFIX)
        if generator.generate(config.MUTANT.func, driver_src_file, config.TEMPLATE_EXPECTED_DRIVER) is False:
            return False

        # generate testcase driver
        if 'TEMPLATE_FALSE_POSITIVE_DRIVER' in config:
            driver_src_file = path.get_driver_src_path(_appendix=path.FALSE_POSITIVE_PREFIX)
            if generator.generate(config.MUTANT.func, driver_src_file, config.TEMPLATE_FALSE_POSITIVE_DRIVER) is False:
                return False

        return True

    ################################################
    # Step 1 (build): extract_mutated_function
    ################################################
    def extract_mutated_function(self ):
        '''
        - extract a mutated function from a mutant
        - save it into the self.FUNC_MUTANT_PATH
        - change the function name from 'fname' to 'mut_fname'
        :return:
        '''
        print("[Step 1] Extracting mutated function from %s ..." % (config.MUTANT.fullpath))

        # get function name
        function_output_file = path.get_mutant_func_file()

        # prepare folders to be stored the mutated function
        mutant_func_dir = os.path.dirname(function_output_file)
        utils.prepare_directory(mutant_func_dir)
        # config.MUTANT_FUNC_PATH

        # extract mutant file from the tar
        #   - This command extract the file _mutant.fullpath into the folder _mutant_func_dir, which is the same to function_output_file
        if utils.extract_file_from_tar(config.MUTANT.fullpath, config.MUTANTS_FILE, _output=config.MUTANT_FUNC_PATH) is False:
            utils.error_exit("Failed to extract mutant code from the archive: '%s'" % (config.MUTANT.fullpath))

        # convert CRLF to LF from the mutant code (CR, '\r',  will cause an error in libclang)
        utils.convert_CRLF_to_LF(function_output_file)

        # extract the mutated function from a mutant
        include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
        compilation_cflags = config.SUT_COMPILE_FLAGS+" " + include_txt

        extractor = FunctionExtractor(compilation_cflags, _prefix=config.MUTANT_FUNC_PREFIX)
        ret = extractor.extract(function_output_file, config.MUTANT.func, function_output_file)
        if ret is False:
            print("failed to parse function under test: '%s' in '%s'" % (config.MUTANT.func, config.MUTANT.src_path))
            exit(1)
        # mutated_func_name = config.MUTANT_FUNC_PREFIX + config.MUTANT.func
        sys.stdout.flush()
        print("\tCompleted to extract mutated function from the mutant")
        print("\tPlease check the mutated function from: %s" % function_output_file)
        return extractor.get_mutated_func_name(config.MUTANT.func)

    ################################################
    # Step 2 (build): generate binary file of SUT with a mutated function
    ################################################
    def generate_binary_SUT(self, _inject_mutant=False, _backup_suffix=".origin"):
        compile.initialize_SUT(config.REPO_PATH, "*.c" + _backup_suffix)  # process for previous error results

        code_origin = path.get_source_file_path()
        code_backup = None
        if _inject_mutant is True:
            # backup original source file
            code_backup = code_origin + _backup_suffix  # set path for backup code
            shutil.copyfile(code_origin, code_backup)

            # set mutant_function file path (extracted function)
            mutated_func_file = path.get_mutant_func_file()

            # injecting mutated function
            compile.inject_mutated_function(code_origin, mutated_func_file,
                                            config.MUTANT.func, config.MUTANT_FUNC_PREFIX)

        print("Compiling SUT ...", flush=True)
        self.compile_SUT(code_origin)

        if _inject_mutant is True:
            compile.rollback_mutated_function(code_backup, code_origin)
        return True

    def check_existance_of_binary_SUT(self):
        obj_files = compile.get_target_files(config.COMPILED_OBJECTS, config.REPO_PATH)  # _includes are already relative path from REPO_PATH
        if obj_files is None or len(obj_files) == 0:
            return False
        return True

    def compile_SUT(self, _code_origin):
        print('REPO:        ' + config.REPO_PATH, flush=True)
        print('code_origin: ' + _code_origin, flush=True)
        if config.COMPILE_SUT_CMDS is not None and len(config.COMPILE_SUT_CMDS) > 0:
            compile_envs={
                "CC": os.path.abspath(config.COMPILER_FILEPATH),
                "AS": os.path.abspath(config.COMPILER_FILEPATH),
                "CXX": os.path.abspath(config.CPP_COMPILER_FILEPATH),
            }
            compile.compile_SUT(config.REPO_PATH, config.COMPILE_SUT_CMDS, compile_envs)
            print("\tCompleted to compile the SUT (software under test) with the mutated function.")
            print("\tPlease find the result files in: %s" % config.REPO_PATH)

        else:
            SUT_files = [] if config.COMPILE_SUT_FILES is None else config.COMPILE_SUT_FILES
            if _code_origin.startswith(config.REPO_PATH):
                _code_origin = _code_origin[len(config.REPO_PATH)+1:]
            SUT_files += [_code_origin]

            compile.compile_SUT_files(config.COMPILER_FILEPATH, SUT_files, config.COMPILE_OUTPUT,
                                      config.INCLUDES, config.SUT_COMPILE_FLAGS, config.REPO_PATH)

            compile_output =  config.COMPILE_OUTPUT if  config.COMPILE_OUTPUT is not None else "./"
            print("\tCompleted to compile the SUT (software under test) with the mutated function.")
            print("\tPlease find the objective files in: %s" % utils.makepath(config.REPO_PATH, compile_output))
        return True

    ################################################
    # Step 3 (build): generate binary for test entry
    ################################################
    def compile_test_entry(self, _appendix=""):
        print("[Step 3] Compiling mutation testing entrypoint (%s) ..." % (_appendix if _appendix != "" else "fuzzing driver"), flush=True)

        # set path
        entry_code_file = path.get_driver_src_path(_appendix=_appendix)
        executable_file = path.get_executable_driver_path(_appendix=_appendix)

        # preparing path
        utils.prepare_directory(os.path.dirname(executable_file))

        # make absolute path for the entry code file (test driver) and an executable file
        entry_code_file = os.path.abspath(entry_code_file)
        executable_file = os.path.abspath(executable_file)

        # checking the existence of the entry code file (if this compilation is not optional, return False)
        if os.path.exists(entry_code_file) is False:
            print("Pass to compile driver that does not exist source code.")
            return True

        compile_flags = config.SUT_COMPILE_FLAGS + " " + config.LINKER_FLAGS

        # compile test driver
        compile.compile_test_driver(config.COMPILER_FILEPATH, entry_code_file, executable_file,
                                    config.COMPILED_OBJECTS, config.INCLUDES, compile_flags, config.REPO_PATH)
        print("\tThe object file of test driver is located in %s" % executable_file)
        return True

    ################################################
    # [Fuzzing] helper function for fuzzing phase
    ################################################
    def execute_fuzzer(self, _mutant_input_dir, _working_dir, _executable_test_driver):
        # check the number of intpus
        if self.check_num_inputs(_mutant_input_dir) == 0:
            utils.error_exit("We have no inputs for fuzzing, Please check input generation.")

        # create command for fuzzer
        # cmd = "timeout -k 60 %d" % config.FUZZING_TIMEOUT    # kill in 60 seconds if the program is not finished
        cmd = "timeout %d" % config.FUZZING_TIMEOUT
        fuzz_cmd = "%s -i %s -o %s" % (config.FUZZER_FILEPATH, _mutant_input_dir, _working_dir,)
        if config.TEST_EXEC_TIMEOUT is not None or config.TEST_EXEC_TIMEOUT != 0:
            fuzz_cmd += ' -t %d'% config.TEST_EXEC_TIMEOUT
        if self.AFLpp is True:
            # set timeout for total fuzzing
            cmd = ""
            fuzz_cmd += " -V %d" % config.FUZZING_TIMEOUT
            # check the length of input file
            input_size = self.get_size_input_file(_mutant_input_dir)
            fuzz_cmd += ' -g %d -G %d'% (input_size, input_size)

        # create test driver command
        obj_cmd = "%s @@ %s" % (_executable_test_driver, _working_dir)
        if config.FUZZER_PRINT_INPUTS is False:
            if config.FUZZER_PRINT_CRASHES is True: obj_cmd += " crash"
        else:
            obj_cmd += " all"
        if config.FUZZER_PRINT_LOG_DETAILS is True: obj_cmd += " log"

        # create final command and execute (ret code 124 is timeout) in working directory
        cmd = "%s %s %s"%(cmd, fuzz_cmd, obj_cmd)
        # if the fuzzer is not stopped after the timeout, we kill it by force in 60 seconds
        ret = utils.shell.execute_with_timeout(cmd, _timeout=config.FUZZING_TIMEOUT+60, _env=config.FUZZER_ENVS)
        if ret is None:
            utils.error_exit("executed command: %s"%cmd)
        return ret

    def postprocess(self, _working_dir):
        print("Post processing ...")

        # set filter
        afl = AFLOutput(_working_dir, _isAFLpp=self.AFLpp)
        afl.store_stats_total_log()
        afl.copy_missing_inputs()
        cnt = afl.remove_duplicate_inputs()
        if cnt > 0:
            print("%d inputs are removed due to duplicate" % cnt)

        self.remove_false_positive(afl, _working_dir)

        KILLED = len(afl.get_input_files(_subName=False))
        print("%d inputs killing the mutant are found."%KILLED)

        return KILLED

    def remove_false_positive(self, _afl:AFLOutput, _working_dir):
        false_driver_file = path.get_executable_driver_path(path.FALSE_POSITIVE_PREFIX)
        if os.path.exists(false_driver_file) is False:
            print("Cannot find the test driver file for representing.")
            print("If you want to do check false positive, Please do `build` phase first")
            return False

        # All the crashed inputs due to the difference of return values will be stored
        input_files = _afl.get_input_files(_subName=False)
        false_positives = []
        for input_file in input_files:
            ret = self.execute_driver_timeout(false_driver_file, input_file, _timeout_ms=config.TEST_EXEC_TIMEOUT*2)
            # timeout also filtered as a false-positive (there is possible to timeout in mutated function)
            if ret is None:
                false_positives.append(input_file)

        _afl.update_stats_false_positive(false_positives)
        print("%d false positives are excluded."%len(false_positives))
        return True

    def check_AFL_plusplus(self):
        cmd = "%s -h" % (config.FUZZER_FILEPATH)
        return True if utils.shell.execute_and_check(cmd, "startswith", "afl-fuzz++", _line_no=0) is not None else False

    def check_num_inputs(self, _input_path):
        if os.path.exists(_input_path) is False: return 0

        files = os.listdir(_input_path)
        files = [f for f in files if f.startswith(".") is False]
        return len(files)

    def get_size_input_file(self, _input_path):
        files = os.listdir(_input_path)
        files = [f for f in files if f.startswith(".") is False]
        filepath = os.path.join(_input_path, files[0])
        fstat = os.stat(filepath)
        return fstat.st_size

    def move_execution_results(self, _from, _to):
        cmd = "mv %s %s" % (_from, _to)
        if utils.shell.execute_and_check(cmd, "retcode", 0) is None:
            print("executed command: %s"%cmd)
            utils.error_exit("Failed to move the results: %s" % cmd)

    ################################################
    # Utilities
    ################################################
    def execute_driver_timeout(self, _driver, _input=None, _verbose=False, _timeout_ms=None):
        # create command for verifying
        if _timeout_ms is None:  _timeout_ms = config.TEST_EXEC_TIMEOUT
        timeout_s = math.ceil(_timeout_ms / 1000)
        cmd = "timeout %d %s " % (timeout_s, _driver)
        if _input is not None:
            cmd += _input if isinstance(_input, str) else " ".join(_input)
        ret, lines = utils.shell.execute(cmd, _verbose=_verbose)
        if _verbose is True:
            print("execution return: %d"%ret, flush=True)
        if ret != 0:
            return None
        return (ret, lines)

    ################################################
    # [GEN] printing out of results
    ################################################
    def present_results(self, _input_dir, _output_dir, _driver_prefix, _result_prefix=None):
        # set driver path
        test_driver_file = path.get_executable_driver_path(_driver_prefix)

        if os.path.exists(test_driver_file) is False:
            utils.error_exit("Cannot find the test driver file for representing. Please do `build` phase first")

        input_files = utils.file.get_all_files(_input_dir, "*.inb", _only_files=True)

        # load list of inputs
        utils.prepare_directory(_output_dir)
        filename = "%s.exec_results.N%d%s_driver.txt" % (_result_prefix if _result_prefix is not None else "",
                                                    len(input_files), "."+ _driver_prefix)
        output_file = utils.makepath(_output_dir, filename)

        # print header
        init_msg = '# Executing results of test driver (%s)\n- Number of inputs: %d\n'
        init_msg = init_msg % (_driver_prefix, len(input_files))
        self.output_log_header(output_file, init_msg)

        # print results with input values
        input_files = sorted(input_files)
        for input_file in input_files:
            # presenter driver execute
            results = self.execute_driver_timeout(test_driver_file, input_file, _verbose=False, _timeout_ms=config.TEST_EXEC_TIMEOUT*2)
            if results is not None:
                self.output_log_execution(output_file, results[0], results[1], input_file)
        return True

    def output_log_header(self, _filename, _msg):
        f = open(_filename, "wt")
        f.write("####################################################\n")
        f.write(_msg)
        f.write("####################################################\n\n")
        f.close()

    def output_log_execution(self, _filename, _ret, _lines, _input=None):
        f = open(_filename, "at")
        f.write("===================================================\n")
        if _input is not None:
            f.write("Working mutant: %s\n" % os.path.dirname(_input))
            f.write("Input file: %s\n\n" % os.path.basename(_input))
        for line in _lines:
            f.write(line+'\n')
        f.write("\n\n\n[ExitCode]: %d\n"%_ret)
        f.write("===================================================\n")
        f.write("===================================================\n")
        f.close()

    ################################################
    # [GEN] generating test cases
    ################################################
    def generate_testcases(self, _src_file, _working_dir, _testcase_dir):
        '''
        execute AFL fuzzing
        Working directory is the same as the location of run.py
        :return:
        '''
        num_failed = 0

        # load list of input files
        afl = AFLOutput(_working_dir, _isAFLpp=self.AFLpp)
        input_files = afl.get_input_files(_subName=False)
        num_cases = len(input_files)
        if len(input_files) <= 0:
            print("No input file exists")
            return num_cases, num_failed

        # path settings
        expected_driver_file = path.get_executable_driver_path(path.EXPECTED_PREFIX)
        utils.prepare_directory(_testcase_dir)

        # create TemplateGenerator
        include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
        compilation_cflags = config.SUT_COMPILE_FLAGS+" " + include_txt
        generator = TemplateGenerator(_src_file, config, compilation_cflags)

        # generate test cases
        utils.prepare_directory(afl.expected_dir_path)
        input_files = sorted(input_files)
        for input_file in input_files:
            try:
                # prepare path
                sub_path = input_file[len(afl.input_dir_path):]
                sub_path = sub_path[1:] if sub_path.startswith("/") else sub_path
                expected_file = utils.makepath(afl.expected_dir_path, sub_path)
                utils.prepare_directory(os.path.dirname(expected_file))

                # presenter driver execute
                print("Input %s:"% sub_path)
                self.execute_driver_timeout(expected_driver_file, (input_file, expected_file), _timeout_ms=config.TEST_EXEC_TIMEOUT*2)
                data = {
                    "input": self.load_binary_array(input_file),
                    "params": self.load_binary_array(expected_file+".params"),
                    "returns": self.load_binary_array(expected_file+".returns"),
                }

                # generate an output folder (test case)
                testcase_file = sub_path.replace(".inb", ".test.c")
                testcase_path = utils.makepath(_testcase_dir, testcase_file)
                utils.prepare_directory(os.path.dirname(testcase_path))

                # generate "TEST CASE"
                ret = generator.generate(config.MUTANT.func, testcase_path, config.TEMPLATE_TESTCASE_DRIVER, _appendix=data)
                if ret is False: num_failed += 1
            except Exception as e:
                traceback.print_exc()
                num_failed += 1

        return num_cases, num_failed

    def compile_testcases(self, _testcase_dir):
        '''
        compile test cases generated from the fuzzing inputs
        Working directory is the same as the location of run.py
        :return:
        '''
        # load list of input files
        testcase_files = utils.file.get_all_files(_testcase_dir, "*.test.c", _subName=True, _only_files=True)
        if len(testcase_files) <= 0:
            print("No test case file exists")
            return True

        # generate SUT codes
        if self.check_existance_of_binary_SUT() is False:
            self.generate_binary_SUT(_inject_mutant=False)

        # generate test cases
        testcase_files = sorted(testcase_files)
        for item in testcase_files:
            # generate an output folder (test case)
            testcase_file = utils.makepath(_testcase_dir, item)
            excutable_file = testcase_file.replace(".test.c", ".obj")

            testcase_abspath = os.path.abspath(testcase_file)
            excutable_abspath = os.path.abspath(excutable_file)

            # compile test driver
            compile_flags = config.SUT_COMPILE_FLAGS + " " + config.LINKER_FLAGS
            compile.compile_test_driver(config.COMPILER_FILEPATH,
                                        testcase_abspath,
                                        excutable_abspath,
                                        config.COMPILED_OBJECTS, config.INCLUDES,
                                        compile_flags, config.REPO_PATH)
            print("\tThe object file of test driver is located in %s" % excutable_file)
        return True

    def execute_testcases(self, _testcase_dir, _output_dir):
        '''
        compile test cases generated from the fuzzing inputs
        Working directory is the same as the location of run.py
        :return:
        '''
        # load list of input files
        testcase_files = utils.file.get_all_files(_testcase_dir, "*.obj", _subName=True, _only_files=True)
        if len(testcase_files) <= 0:
            print("No executable test case file exists")
            return True

        # load list of inputs
        filename = "testcases.results.N%d.txt" % (len(testcase_files))
        output_file = utils.makepath(_output_dir, filename)

        # print header
        init_msg = '# Executing results of test driver (%s)\n- Number of inputs: %d\n'
        init_msg = init_msg % ("test cases", len(testcase_files))
        self.output_log_header(output_file, init_msg)

        # executes test cases
        testcase_files = sorted(testcase_files)
        for item in testcase_files:
            testcase_file = utils.makepath(_testcase_dir, item)
            testcase_abspath = os.path.abspath(testcase_file)

            # execute
            results = self.execute_driver_timeout(testcase_abspath, _verbose=False, _timeout_ms=config.TEST_EXEC_TIMEOUT*2)
            if results is not None:
                self.output_log_execution(output_file, results[0], results[1], testcase_file)
        return True

    def load_binary_array(self, _filename):
        f = open(_filename, "rb")
        data = f.read()
        f.close()
        binarylist = list(data)
        return binarylist


if __name__ == "__main__":
    pipeline = Runner()
    exit(0)

