#! /usr/bin/env python3
import os
import shutil
import sys
import json
import platform
if platform.python_version().startswith("3.") is False:
    raise Exception("Must be using Python 3")

from pipeline.FunctionExtractor import FunctionExtractor
from pipeline.TemplateGenerator import TemplateGenerator
from pipeline import utils
from pipeline import compile
from pipeline import Config


class Runner(object):

    FUNCTION_DRIVER_EXT = "wrapping_main.c"   # *.wrapping_main.c
    MUTANT_DRIVER_EXT = "main.c"              # *.main.c
    OBJECT_DRIVER_EXT = "obj"                 # *.obj
    PRESENTER_PREFIX = "presenter"            #
    TESTCASE_PREFIX = "testcase"              #
    FALSE_POSITIVE_PREFIX = "false"           # driver for the false positive checking
    # DEPENDENCY_PREFIX = "dependency"          # driver for the dependency checking

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

        # proceed each phase
        if config.PHASE in ["all", "preprocess"]:
            self.preprocess()
        if config.PHASE in ["all", "build"]:
            self.build()
        if config.PHASE in ["all", "run"]:
            self.run()
        if config.PHASE in ["all", "verify"]:
            self.verify()
        pass

    ################################################
    # preprocess phase
    ################################################
    def preprocess(self):
        '''
        preprocess for the `build` phase
        :return:
        '''
        # clone repository
        config.REPO_PATH = self.unzip_repository()

        # set file path
        source_file = utils.makepath(config.REPO_PATH, config.MUTANT.src_path)
        func_driver_dir = utils.makepath(config.FUNC_DRIVER_PATH, config.MUTANT.dir_path, config.MUTANT.func)
        func_input_dir = utils.makepath(config.FUNC_INPUT_PATH, config.MUTANT.dir_path, config.MUTANT.func)

        # step 1
        if self.does_execute_this_step(_step=1):
            ret = self.generate_driver_for_function(source_file, func_driver_dir, func_input_dir, config.MUTANT.func, config.OVERWRITE)
            if ret is False:
                print("Failed to generate test driver for functions")
                return False

        print("Finished to generate test driver for functions")
        print("Please go with `build` phase", flush=True)
        return True

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
    # build phase
    ################################################
    def build(self):
        '''
        Build procedure for AFL fuzzing
        :return:
        '''
        # set paths for the mutant
        func_driver_dir = utils.makepath(config.FUNC_DRIVER_PATH, config.MUTANT.dir_path, config.MUTANT.func)
        mutant_func_dir = utils.makepath(config.MUTANT_FUNC_PATH, config.MUTANT.dir_path)
        mutant_binary_dir = utils.makepath(config.MUTANT_BIN_PATH, config.MUTANT.dir_path)

        if os.path.exists(func_driver_dir) is False:
            print('Cannot find the test driver for the function. Please do `preprocess`.')
            utils.error_exit("Test driver path: %s" % func_driver_dir)

        # clone repository (Can be changed to the temporary folder)
        config.REPO_PATH = self.unzip_repository()

        # step 1
        if self.does_execute_this_step(_step=1):
            self.extract_mutated_function(config.MUTANT, config.MUTANT_FUNC_PATH)

        # step 2
        if self.does_execute_this_step(_step=2):
            self.generate_binary_SUT(config.MUTANT.src_path, mutant_func_dir)

        # step 3.1 (compile a test driver for AFL++)
        if self.does_execute_this_step(_step=3):
            self.compile_test_entry(func_driver_dir, mutant_binary_dir)

        # step 3.2 (compile a driver for input presenter)
        if self.does_execute_this_step(_step=3):
            appendix = "."+ self.PRESENTER_PREFIX
            self.compile_test_entry(func_driver_dir, mutant_binary_dir+appendix, appendix)

        # step 3.3 (compile a driver for test case printing)
        if self.does_execute_this_step(_step=3):
            appendix = "."+ self.TESTCASE_PREFIX
            self.compile_test_entry(func_driver_dir, mutant_binary_dir+appendix, appendix)

        # step 3.4 (compile a driver for false positive checking)
        if self.does_execute_this_step(_step=3):
            appendix = "."+ self.FALSE_POSITIVE_PREFIX
            self.compile_test_entry(func_driver_dir, mutant_binary_dir+appendix, appendix, _optional=True)

        # step 3.5 (compile a driver for dependency checking)
        # if self.does_execute_this_step(_step=3):
        #     appendix = "."+ self.DEPENDENCY_PREFIX
        #     self.compile_test_entry(func_driver_dir, mutant_binary_dir+appendix, appendix, _optional=True)

        # if config.CLONE_REPO is True:
        #     self.remove_cloned_repository()

        print("Finished building executable SUT and input files")
        print("Please fun fuzzer!!", flush=True)
        return True

    ################################################
    # run phase
    ################################################
    def run(self):
        '''
        execute AFL fuzzing
        :return:
        '''
        # determine output and working dir
        output_dir = self.make_output_path()
        working_dir = self.make_working_path(output_dir)
        utils.prepare_directory(working_dir)

        # set input paths
        func_input_dir = utils.makepath(config.FUNC_INPUT_PATH, config.MUTANT.dir_path, config.MUTANT.func)
        test_driver_file = utils.makepath(config.MUTANT_BIN_PATH, config.MUTANT.dir_path, config.MUTANT.name + "." + self.OBJECT_DRIVER_EXT)

        if os.path.exists(func_input_dir) is False:
            utils.error_exit("Cannot find the input folder. Please do `build` phase first")

        if os.path.exists(test_driver_file) is False:
            utils.error_exit("Cannot find the object file. Please do `build` phase first")

        # execute fuzzer
        if self.execute_fuzzer(func_input_dir, working_dir, test_driver_file) is False:
            utils.error_exit("Failed to execute fuzzer: %s" % test_driver_file)

        # make stats of the fuzzer results
        print("Generating statistics of fuzzing results ...")
        try:
            self.generate_stats(working_dir)
        except Exception as e:
            print("Failed to generate statistics!")

        # make additional results at stats
        print("Checking false positive of fuzzing results ...")
        try:
            self.checking_false_positive(working_dir)
        except Exception as e:
            print("Failed to generate statistics!")

        # compress the execution result
        if config.UNCOMPRESS_RESULT is True:
            if working_dir != output_dir:
                print("Moving the execution results to output directory ...")
                utils.prepare_directory(os.path.dirname(output_dir))
                self.move_execution_results(working_dir, output_dir)
            print("Please find the results: %s " % output_dir)

        else:
            print("Compressing the execution results ...")
            ext = self.compress_working_dir(working_dir)

            print("Removing the execution results ...")
            self.remove_working_dir(working_dir)

            if working_dir != output_dir:
                print("Moving the execution results to output directory ...")
                utils.prepare_directory(os.path.dirname(output_dir))
                self.move_execution_results(working_dir + ext, output_dir + ext)

            print("Please find the results: %s" % (output_dir + ext))

        print("Finished fuzzing")
        pass

    ################################################
    # verify phase
    ################################################
    def verify(self):
        '''
        execute AFL fuzzing
        :return:
        '''
        # determine output and working dir for 'run' phase
        output_dir = self.make_output_path()
        working_dir = self.make_working_path(output_dir)
        utils.prepare_directory(working_dir)
        print("output_dir: "+output_dir)
        print("working_dir: "+working_dir)

        # uncompress result_file into working_dir
        result_file = output_dir + ".tar" if config.UNCOMPRESS_RESULT is False else ""
        print("result_file: "+result_file)
        if os.path.exists(result_file) is False:
            utils.error_exit("Cannot find the result file or directory. Please do `run` phase first")
        if config.UNCOMPRESS_RESULT is False:
            # uncompress result
            self.unzip_results(result_file, working_dir)

        # check input files in the working directory
        input_dir = utils.makepath(working_dir, "inputs")
        if os.path.exists(input_dir) is True:
            # ====================================================
            # set driver path
            appendix = "."+ self.PRESENTER_PREFIX
            test_driver_file = utils.makepath(config.MUTANT_BIN_PATH, config.MUTANT.dir_path + appendix ,
                                              config.MUTANT.name + appendix + "." + self.OBJECT_DRIVER_EXT)
            if os.path.exists(test_driver_file) is False:
                utils.error_exit("Cannot find the test driver file for representing. Please do `build` phase first")

            # some information should go to configuration
            output_dir_verification = self.make_verification_path()

            # verifying results
            utils.prepare_directory(os.path.dirname(output_dir_verification))
            self.reproduce(test_driver_file, input_dir, output_dir_verification)
            # ====================================================
            print("Please find the results: %s" % output_dir_verification)
            print("Finished verification")
        else:
            print("Cannot find the test inputs. We have no inputs for this mutant leading non-identical results of original and mutated functions.")

        # Organizing execution results
        #    When working in HPC, we are working in the temporary directory
        if config.UNCOMPRESS_RESULT is False or config.HPC_PARALLEL is True:
            print("Removing the temporary results ...")
            self.remove_working_dir(working_dir)
        pass

    ################################################
    # Clone repository
    ################################################
    def copy_repository(self):
        '''
        [deprecated] Currently we do not use this way. (would take long time, sometimes miss soft link files)
        :return:
        '''
        # determine the target directory for the repository
        temp_repository_dir = config.REPO_PATH
        if config.HPC_PARALLEL is True:
            temp_repository_dir = utils.makepath(config.HPC_BUILD_BASE, config.MUTANT.dir_path, config.MUTANT.name)

        # copy the repository
        print("Copying code repository...")
        print("   - From: %s" % config.REPO_PATH)
        print("   - To: %s" % temp_repository_dir, flush=True)
        utils.prepare_directory(os.path.dirname(temp_repository_dir))
        if os.path.exists(temp_repository_dir) is False:
            cmd = "cp -a %s %s" % (config.REPO_PATH, temp_repository_dir)
            ret = utils.shell.execute_and_check(cmd, "retcode", 0)
            if ret is None:
                utils.error.error_exit("Failed to copy repository file")
        else:
            print("The repository exists.", flush=True)
        print("Done.", flush=True)
        return temp_repository_dir

    def unzip_repository(self):
        # determine the target directory for the repository
        temp_repository_dir = config.REPO_PATH
        if config.HPC_PARALLEL is True:
            temp_repository_dir = utils.makepath(config.HPC_BUILD_BASE, config.MUTANT.dir_path, config.MUTANT.name)

        # copy the repository
        print("Unzipping code repository...")
        print("   - From: %s" % config.REPO_FILE)
        print("   - To: %s" % temp_repository_dir, flush=True)
        if os.path.exists(temp_repository_dir) is False:
            utils.prepare_directory(temp_repository_dir)
            cmd = "tar xf %s --directory %s" % (config.REPO_FILE, temp_repository_dir)
            if utils.shell.execute_and_check(cmd, "retcode", 0) is None:
                utils.error.error_exit("Cannot unzip the code files. Please check the type of compressing. It should be a 'tar' with out '-z' option.")
        else:
            print("The repository exists.", flush=True)
        print("Done.", flush=True)
        return temp_repository_dir

    def remove_cloned_repository(self):
        print("Removing the cloned repository %s ..."% config.REPO_PATH, flush=True)
        shutil.rmtree(config.REPO_PATH, ignore_errors=True)
        pass

    ################################################
    # Step 1 (preprocess): generate template
    ################################################
    def generate_driver_for_function(self, _src_file, func_driver_dir, _input_dir, _func_name, _overwrite=False):
        print("[Step 1] Generating test driver for the mutated function into %s ..."% func_driver_dir)

        # generate an output folder
        utils.prepare_directory(func_driver_dir)

        # check if the file already exists
        func_driver_file = utils.makepath(func_driver_dir, config.MUTANT.func + "." + self.FUNCTION_DRIVER_EXT)
        if (os.path.exists(func_driver_file) is True and _overwrite is False): return True

        # generate a test driver for a function and input files
        include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
        compilation_cflags = config.SUT_COMPILE_FLAGS+" " + include_txt
        # print(compilation_cflags)

        generator = TemplateGenerator(_src_file, func_driver_dir, config, compilation_cflags, _input_dir)
        return generator.process(_func_name)

    ################################################
    # Step 1 (build): extract_mutated_function
    ################################################
    def extract_mutated_function(self, _mutant, _mutant_func_dir):
        '''
        - extract a mutated function from a mutant
        - save it into the self.FUNC_MUTANT_PATH
        - change the function name from 'fname' to 'mut_fname'
        :return:
        '''
        print("[Step 1] Extracting mutated function from %s ..." % (_mutant.fullpath))

        # prepare folders to be stored the mutated function
        utils.prepare_directory(_mutant_func_dir)
        function_output_file = utils.makepath(_mutant_func_dir, _mutant.fullpath)

        # extract mutant file from the tar
        #   - This command extract the file _mutant.fullpath into the folder _mutant_func_dir, which is the same to function_output_file
        if utils.extract_file_from_tar(_mutant.fullpath, config.MUTANTS_FILE, _output=_mutant_func_dir) is False:
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
    # Step 2 (build): generate test driver for a mutant (not used)
    ################################################
    def generate_driver_for_mutant(self, _func_driver_dir, _mutant_driver_path):
        '''
        copy test driver for a function into the mutant-drivers folder
        :return:
        '''
        print("[Step 2] Generating test driver for mutation testing ...")
        src_file = utils.makepath(_func_driver_dir, config.MUTANT.func + "." + self.FUNCTION_DRIVER_EXT)
        dest_file = utils.makepath(_mutant_driver_path, config.MUTANT.name + "." + self.MUTANT_DRIVER_EXT)

        # make output path
        utils.prepare_directory(_mutant_driver_path)

        #  copy test driver for a function into a mutant driver folder
        shutil.copyfile(src_file, dest_file)
        sys.stdout.flush()
        print("\tCompleted to generate source code of the test driver: %s"%dest_file)
        return True

    ################################################
    # Step 2 (build): generate binary file of SUT with a mutated function
    ################################################
    def generate_binary_SUT(self, _code_origin, _mutant_func_dir, _backup_suffix=".origin"):
        print("[Step 2] Injecting mutant into SUT...")
        compile.initialize_SUT(config.REPO_PATH, "*.c" + _backup_suffix)  # process for previous error results

        # backup original source file
        code_origin = utils.makepath(config.REPO_PATH,_code_origin)
        code_backup = code_origin + _backup_suffix  # set path for backup code
        shutil.copyfile(code_origin, code_backup)

        # set mutant_function file path (extracted function)
        mutated_func_file = utils.makepath(_mutant_func_dir, config.MUTANT.filename)

        # injecting mutated function
        compile.inject_mutated_function(code_origin, mutated_func_file)

        print("[Step 2] Compiling SUT ...", flush=True)
        # print('REPO:' + config.REPO_PATH, flush=True)
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
            SUT_files += [_code_origin]

            compile.compile_SUT_files(config.COMPILER_FILEPATH, SUT_files, config.COMPILE_OUTPUT,
                                      config.INCLUDES, config.SUT_COMPILE_FLAGS, config.REPO_PATH)

            compile_output =  config.COMPILE_OUTPUT if  config.COMPILE_OUTPUT is not None else "./"
            print("\tCompleted to compile the SUT (software under test) with the mutated function.")
            print("\tPlease find the objective files in: %s" % utils.makepath(config.REPO_PATH, compile_output))

        compile.rollback_mutated_function(code_backup, code_origin)
        return True

    ################################################
    # Step 3 (build): generate binary for test entry
    ################################################
    def compile_test_entry(self, _driver_dir, _binary_dir, _appendix="", _optional=False):
        print("[Step 3] Compiling mutation testing entrypoint (%s) ..." % (_appendix if _appendix != "" else "fuzzing driver"), flush=True)

        # preparing path
        utils.prepare_directory(_binary_dir)

        entry_code_file = utils.makepath(_driver_dir, config.MUTANT.func + _appendix + "." + self.FUNCTION_DRIVER_EXT)
        executable_file = utils.makepath(_binary_dir, config.MUTANT.name + _appendix + '.' + self.OBJECT_DRIVER_EXT)

        # make absolute path for the entry code file (test driver) and an executable file
        entry_code_file = os.path.abspath(entry_code_file)
        executable_file = os.path.abspath(executable_file)

        # checking the existence of the entry code file (if this compilation is not optional, return False)
        if os.path.exists(entry_code_file) is False:
            if _optional is False:
                raise Exception("Not found the driver source code: %s" % entry_code_file)
            else:
                print("Pass to compile driver that does not exist source code.")
                return True

        compile_flags = config.SUT_COMPILE_FLAGS + " " + config.LINKER_FLAGS

        # compile test driver
        compile.compile_test_driver(config.COMPILER_FILEPATH, entry_code_file, executable_file,
                                    config.COMPILED_OBJECTS, config.INCLUDES, compile_flags, config.REPO_PATH)
        print("\tThe object file of test driver is located in %s" % executable_file)
        return True

    ################################################
    # Step 4 (build): prepare inputs for a test entry (not used)
    ################################################
    def prepare_inputs_for_test_entry(self, _func_driver_dir, _mutant_input_dir):
        '''
        copy inputs from the func-drivers folder into the mutant-inputs folder
        :return:
        '''
        print("[Step 4] Preparing inputs for test entry ...", flush=True)

        # prepare path
        utils.prepare_directory(_mutant_input_dir)
        func_input_file_base = utils.makepath(_func_driver_dir, config.MUTANT.func)

        # copy inputs
        for tag in config.INPUT_FILTER:
            filename = config.MUTANT.func + "." + tag
            shutil.copy(func_input_file_base+"."+tag,
                        utils.makepath(_mutant_input_dir, filename))
        print("\tStored input files in %s"%_mutant_input_dir)
        return True

    ################################################
    # helper function for run phase
    ################################################
    def execute_fuzzer(self, _mutant_input_dir, _working_dir, _executable_test_driver):
        # check AFL++
        is_AFL_plus = self.check_AFL_plusplus()

        # check the number of intpus
        if self.check_num_inputs(_mutant_input_dir) == 0:
            utils.error_exit("We have no inputs for fuzzing, Please check input generation.")

        # create command for fuzzer
        # cmd = "timeout -k 60 %d" % config.FUZZING_TIMEOUT    # kill in 60 seconds if the program is not finished
        cmd = "timeout %d" % config.FUZZING_TIMEOUT
        fuzz_cmd = "%s -i %s -o %s" % (config.FUZZER_FILEPATH, _mutant_input_dir, _working_dir,)
        if config.TEST_EXEC_TIMEOUT is not None or config.TEST_EXEC_TIMEOUT != 0:
            fuzz_cmd += ' -t %d'% config.TEST_EXEC_TIMEOUT
        if is_AFL_plus is True:
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

    def generate_stats(self, _working_dir):
        # We execute ExpResult by subprocess to prevent unexpected error when the tools are changed.
        # check whether AFL++ is used
        is_AFL_plus = self.check_AFL_plusplus()

        # set filter
        filter = ';'.join([item[0].upper() for item in config.INPUT_FILTER])

        # execute stats to make statistics of fuzzing results
        cmd = "%s tools/stats.py -w %s -f \"%s\" %s" % (config.PYTHON_CMD, _working_dir, filter, "--plus" if is_AFL_plus is True else "")
        utils.shell.execute_and_check(cmd, "lines", 0)
        pass

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

    def make_output_path(self):
        output_dir = utils.makepath(config.FUZZING_OUTPUT_PATH, config.MUTANT.dir_path, config.MUTANT.name)
        if config.RUN_ID is not None:
            output_dir = utils.makepath(output_dir, "Run%05d"% config.RUN_ID)
        return output_dir

    def make_working_path(self, _output_dir):
        working_dir = _output_dir
        if config.HPC_PARALLEL is True:
            working_dir = utils.makepath(config.HPC_EXEC_BASE, config.MUTANT.dir_path, config.MUTANT.name)
            if config.RUN_ID is not None:
                working_dir = utils.makepath(working_dir, "Run%05d"% config.RUN_ID)
        return working_dir

    def compress_working_dir(self, _working_dir):
        ext = '.tar'
        cmd = "tar cf ../%s%s ." % (os.path.basename(_working_dir), ext)
        if utils.shell.execute_and_check(cmd, "retcode", 0, _working_dir=_working_dir) is None:
            print("executed command: %s"%cmd)
            utils.error_exit("Failed to compress the results: %s" % cmd)
        return ext

    def remove_working_dir(self, _working_dir):
        parent = os.path.dirname(_working_dir)
        cmd = "rm -rf %s" % os.path.basename(_working_dir)
        if utils.shell.execute_and_check(cmd, "retcode", 0, _working_dir=parent) is None:
            print("executed command: %s"%cmd)
            utils.error_exit("Failed to remove the results: %s" % cmd)

    def move_execution_results(self, _from, _to):
        cmd = "mv %s %s" % (_from, _to)
        if utils.shell.execute_and_check(cmd, "retcode", 0) is None:
            print("executed command: %s"%cmd)
            utils.error_exit("Failed to move the results: %s" % cmd)

    ################################################
    # helper function for verify phase
    ################################################
    def unzip_results(self, _result_file, _working_dir):
        # copy the repository
        print("Unzipping code repository...")
        print("   - From: %s" % _result_file)
        print("   - To: %s" % _working_dir, flush=True)
        if os.path.exists(_working_dir) is True:
            shutil.rmtree(_working_dir, ignore_errors=True)

        # unzip
        utils.prepare_directory(_working_dir)
        cmd = "tar xf %s --directory %s" % (_result_file, _working_dir)
        if utils.shell.execute_and_check(cmd, "retcode", 0) is None:
            utils.error.error_exit("Cannot unzip the result file. Please check the result file or retry.")
        return True

    def reproduce(self, _driver_obj_path, _input_dir, _output_path):
        # load list of inputs
        input_files = utils.file.get_all_files(_input_dir, "*", _only_files=True)

        # create command for verifying
        output_file = "%s.N%d.%s.txt" % (_output_path, len(input_files), self.PRESENTER_PREFIX)
        self.output_initialize(output_file)
        for input_file in input_files:
            # presenter driver execute
            cmd = "%s %s" % (_driver_obj_path, input_file)
            ret, lines = utils.shell.execute(cmd)
            self.output_execution_log(output_file, ret, lines, input_file)

        # create command for verifying
        output_file = "%s.N%d.%s.txt" % (_output_path, len(input_files), self.TESTCASE_PREFIX)
        self.output_initialize(output_file)
        _driver_obj_path = _driver_obj_path.replace("."+self.PRESENTER_PREFIX,"."+self.TESTCASE_PREFIX)
        for input_file in input_files:
            # presenter driver execute
            cmd = "%s %s" % (_driver_obj_path, input_file)
            ret, lines = utils.shell.execute(cmd)
            self.output_execution_log(output_file, ret, lines, input_file)

        # ## original test driver
        # _driver_obj_path = _driver_obj_path.replace("."+self.TESTCASE_PREFIX,"")
        # for input_file in input_files:
        #     log_file = utils.makepath(_output_dir, "%s.log"%os.path.basename(input_file))
        #     cmd = "%s %s %s" % (_driver_obj_path, input_file, _output_dir)
        #     ret, lines = utils.shell.execute(cmd)
        #     self.output_execution_log(log_file, ret, lines)

        return True

    def output_execution_log(self, _filename, _ret, _lines, _input=None):
        f = open(_filename, "a")
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

    def output_initialize(self, _filename):
        f = open(_filename, "w")
        f.write("")
        f.close()

    def make_verification_path(self):
        output_dir = utils.makepath(config.VERIFY_OUTPUT_PATH, config.MUTANT.dir_path, config.MUTANT.name)
        if config.RUN_ID is not None:
            output_dir = utils.makepath(output_dir, "Run%05d"% config.RUN_ID)
        return output_dir

    ################################################
    # checking false positive
    ################################################
    def checking_false_positive(self, _working_dir):
        # set driver file
        appendix = "."+ self.FALSE_POSITIVE_PREFIX
        test_driver_file = utils.makepath(config.MUTANT_BIN_PATH,
                                          config.MUTANT.dir_path + appendix ,
                                          config.MUTANT.name + appendix + "." + self.OBJECT_DRIVER_EXT)
        if os.path.exists(test_driver_file) is False:
            print("Cannot find the test driver file for representing.")
            print("If you want to do check false positive, Please do `build` phase first")

        # All the crashed inputs due to the difference of return values will be stored
        # in "./inputs" with ".inb" extension.
        input_files = utils.get_all_files(_working_dir, "inputs/**/*.inb", _subName=True)
        if len(input_files) == 0:
            # We assume it is live mutants
            # Some mutants can be considered as "KILLED" if they crashed in the execution of mutated function
            pass
        else:
            false_positives = []
            for input_file in input_files:
                target = os.path.join(_working_dir, input_file)
                if self.execute_false_driver(test_driver_file, target) is False:
                    false_positives.append(input_file)

            # update stats log
            fp = open(os.path.join(_working_dir, "stats.log"), "r")
            stats = json.load(fp)
            fp.close()
            stats["false_positives"] = false_positives
            fp = open(os.path.join(_working_dir, "stats.log"), "w")
            json.dump(stats, fp)
            fp.close()
        return True

    def execute_false_driver(self, _driver, _input):
        # create command for verifying
        cmd = "%s %s" % (_driver, _input)
        ret, lines = utils.shell.execute(cmd)
        if ret != 0:
            for line in lines:
                print(line)
            print("Return code: %d\n"%ret)
            print("Please check this input: %s" % _input)
            return False
        return True


if __name__ == "__main__":
    pipeline = Runner()
    exit(0)

