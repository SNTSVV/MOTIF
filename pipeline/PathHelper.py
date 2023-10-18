import os
from pipeline import utils
from pipeline import Config


class PathHelper():
    config:Config = None

    FUNCTION_DRIVER_EXT = "wrapping_main.c"   # *.wrapping_main.c
    MUTANT_DRIVER_EXT = "main.c"              # *.main.c
    OBJECT_DRIVER_EXT = "obj"                 # *.obj
    PRESENTER_PREFIX = "presenter"            #
    EXPECTED_PREFIX = "expected"              #
    TESTCASE_PREFIX = "testcase"              #
    FALSE_POSITIVE_PREFIX = "false"           # driver for the false positive checking
    # DEPENDENCY_PREFIX = "dependency"          # driver for the dependency checking


    def __init__(self, _config:Config):
        global config
        config = _config

    def get_source_file_path(self):
        return utils.makepath(config.REPO_PATH, config.MUTANT.src_path)

    def get_repo_path(self):
        temp_dir = config.REPO_PATH
        if config.HPC_PARALLEL is True:
            temp_dir = utils.makepath(config.HPC_WORK_PATH, config.JOB_NAME)
            temp_dir = utils.makepath(temp_dir, "repos", config.MUTANT.dir_path, config.MUTANT.name)
            if config.RUN_ID is not None:
                temp_dir = utils.makepath(temp_dir, "Run%05d"%config.RUN_ID)
        return temp_dir

    # def get_extracted_mutant_path(self):
    #     return utils.makepath(config.REPO_PATH, config.MUTANT.src_path)


    #############################
    # phase paths
    #############################
    def get_func_driver_path(self):
        # 1-func-driver: directory for the fuzzing drivers
        return utils.makepath(config.FUNC_DRIVER_PATH, config.MUTANT.dir_path, config.MUTANT.func)

    def get_func_input_path(self, _base=None, _external=False):
        '''
        :param _base: path when user wan to use non-default name of the path
        :param _external: decide whether the _base will be located under config.OUTPUT_PATH
        :return:
        '''
        # 2-func-input: directory for the seed input
        if _base is not None:
            _base = utils.makepath(config.OUTPUT_PATH, _base) if _external is False else _base
        else:
            _base = config.FUNC_INPUT_PATH
        return utils.makepath(_base, config.MUTANT.dir_path, config.MUTANT.func)

    def get_mutant_func_path(self, _base=None, _external=False):
        # 3-mutant-func: directory for the extracted source code of mutants
        if _base is not None:
            _base = utils.makepath(config.OUTPUT_PATH, _base) if _external is False else _base
        else:
            _base = config.MUTANT_FUNC_PATH
        return utils.makepath(_base, config.MUTANT.dir_path)

    def get_mutant_func_file(self, _base=None, _external=False):
        # 3-mutant-func: directory for the extracted source code of mutants
        if _base is not None:
            _base = utils.makepath(config.OUTPUT_PATH, _base) if _external is False else _base
        else:
            _base = config.MUTANT_FUNC_PATH
        return utils.makepath(_base, config.MUTANT.fullpath)

    def get_mutant_bin_path(self, _base=None, _external=False):
        # 4-mutant-bin: directory for the executable fuzzing drivers
        if _base is not None:
            _base = utils.makepath(config.OUTPUT_PATH, _base) if _external is False else _base
        else:
            _base = config.MUTANT_BIN_PATH
        return utils.makepath(_base, config.MUTANT.dir_path)

    def get_fuzzing_output_path(self):
        # 5-fuzzing: directory for the fuzzing outputs
        output_dir = utils.makepath(config.FUZZING_OUTPUT_PATH, config.MUTANT.dir_path, config.MUTANT.name)
        if config.RUN_ID is not None:
            output_dir = utils.makepath(output_dir, "Run%05d"% config.RUN_ID)
        return output_dir

    def get_testcase_output_path(self):
        # 6-testcases: directory for the automatically generated test cases
        output_dir = utils.makepath(config.TESTCASE_OUTPUT_PATH, config.MUTANT.dir_path, config.MUTANT.name)
        if config.RUN_ID is not None:
            output_dir = utils.makepath(output_dir, "Run%05d"% config.RUN_ID)
        return output_dir

    #############################
    # executable driver path
    def get_driver_src_path(self, _path=None, _func_name=None, _appendix=""):
        _path = self.get_func_driver_path() if _path is None else _path
        _func_name = config.MUTANT.func if _func_name is None else _func_name
        if _appendix != "": _appendix = "." + _appendix
        return utils.makepath(_path, _func_name + _appendix + '.' + self.FUNCTION_DRIVER_EXT)

    def get_executable_driver_path(self, _appendix=""):
        if _appendix != "": _appendix = "." + _appendix
        return utils.makepath(config.MUTANT_BIN_PATH,
                              config.MUTANT.dir_path + _appendix,
                              config.MUTANT.name + _appendix + "." + self.OBJECT_DRIVER_EXT)


    #############################
    # HPC related path
    def get_HPC_temporary_path(self, _output_dir):
        temp_dir = _output_dir
        if config.HPC_PARALLEL is True:
            base_path = utils.makepath(config.HPC_WORK_PATH, config.JOB_NAME)
            temp_dir = temp_dir.replace(config.OUTPUT_PATH, "")   # reduce unnecessary path
            temp_dir = temp_dir[1:] if temp_dir.startswith("/") else temp_dir
            temp_dir = utils.makepath(base_path, temp_dir)
            # temp_dir = utils.makepath(config.HPC_EXEC_BASE, config.MUTANT.dir_path, config.MUTANT.name)
            # if config.RUN_ID is not None:
            #     temp_dir = utils.makepath(temp_dir, "Run%05d"% config.RUN_ID)
        return temp_dir
