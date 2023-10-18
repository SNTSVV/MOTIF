

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pipeline import utils
from pipeline import Config
import tools.utils
from pipeline.fuzzer import AFLOutputTar


class TarExtractor():
    EXTRACT_TARGET = '5-fuzzing'
    REDIRECT_TARGET= '8-test'

    def __init__(self):
        args = self.arg_parse()
        if args['target'] is not None:
            self.EXTRACT_TARGET = args['target']
        if args['redirect'] is not None:
            self.REDIRECT_TARGET = args['redirect']

        global config
        params = Config.parse_arg()
        config = Config.configure(params)
        if config.NO_CONFIG_VIEW is False:
            config.print_config()
        config.verify_config()

    def get_output_path(self, _type_name):
        # create output path
        if config.has_value('EXP_TAG_NAME'):
            new_type_name = "%s-%s" % (_type_name, config.EXP_TAG_NAME)
            work_path = utils.makepath(config.OUTPUT_PATH, new_type_name)
        else:
            work_path = utils.makepath(config.OUTPUT_PATH, _type_name)

        # add mutant path after output path
        work_path = utils.makepath(work_path, config.MUTANT.dir_path, config.MUTANT.name)

        # add run ID
        if config.RUN_ID is not None:
            work_path = utils.makepath(work_path, "Run%05d"% config.RUN_ID)
        return work_path

    def extract(self, _tarfile, _target=None):
        print('::: Extracting tar with %s'%_tarfile)
        if _target is None:
            dirpath = _tarfile[:-4]
        else:
            dirpath = _target
        os.makedirs(dirpath, exist_ok=True)
        obj = AFLOutputTar(_tarfile, dirpath)
        obj.DELETE_TEMP_DIR = False
        obj.extract_tar()
        obj.close()

    def run(self):
        output_base = self.get_output_path(self.EXTRACT_TARGET)
        result_filepath = output_base + ".tar"

        # extract location
        ext_path = output_base
        if self.REDIRECT_TARGET is not None and self.REDIRECT_TARGET !="":
            ext_path = self.get_output_path(self.REDIRECT_TARGET)

        self.extract(result_filepath, ext_path)
        pass

    ########################################################
    # arg parsing
    ########################################################
    def arg_parse(self):
        info = [
            {"name":"redirect", "key":"--redir", "default":None, "type":"string"},
            {"name":"target", "key":"--target", "default":None, "type":"string"}
        ]
        return tools.utils.parse_args_with_remove(info)


if __name__ == "__main__":
    # basic arguments: [--redir redirect] [--target target]
    #   * --target: specify the target name to load the tar file (e.g., 6-fuzzing, 7-reproduce ...)
    #   * --redir: specify the output dir name to be extracted the tar file  (e.g., 8-test, 9-test ...)
    # config arguments: [-c CONFIG] [-J JOB_NAME] [-t TAG_NAME] <MUTANT_NAME> <INPUT_FILTER> run
    # -c config.py -J _verify -t 5m --runID 1 timestamp.mut.13.2_7_56.AOR.timestamp_add.c A run # -c config.py -J _verify -t 5m --runID 1 memory.mut.8.1_1_9.ABS.long_to_string.c A run
    obj=TarExtractor()
    obj.run()


