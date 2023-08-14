
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pipeline import utils
from pipeline import Config


#####
# This class copies AFL results and execute test driver with the inputs that caused crashes during AFL running
# Then, check if the crashed inputs reproduce the same crashes with the same input.
#####
class Reproducer():
    REPR_OUTPUT_NAME = '7-reproduce'

    # need to take
    # [-c CONFIG] [-J JOB_NAME] [-t TAG_NAME] [--uncompress] [--hpc] [--parallel] <MUTANT_NAME> <INPUT_FILTER> run
    # -c config.py -J _verify -t 5m --hpc memory.mut.11.1_1_49.ABS.long_to_string.c A run

    def __init__(self):
        global config
        params = Config.parse_arg()
        config = Config.configure(params)
        if config.NO_CONFIG_VIEW is False:
            config.print_config()
        config.verify_config()

        # proceed each phase
        if config.PHASE in ["all", "run"]:
            self.run()
        pass

    def run(self):
        # determine paths for working
        result_path = self.get_result_path()
        output_dir = self.get_output_path(self.REPR_OUTPUT_NAME)
        obj_file = utils.makepath(config.MUTANT_BIN_PATH, config.MUTANT.dir_path, config.MUTANT.name+".obj")

        if result_path is None or os.path.exists(result_path) is False:
            print("Cannot found the result file or path.")
            exit(1)

        # if we are working on HPC, change the working directory
        if config.HPC is True:
            working_dir = self.make_HPC_working_path(output_dir)
        else:
            working_dir = output_dir
        utils.prepare_directory(working_dir)

        # uncompress if the results is compressed
        if result_path.endswith(".tar"):
            result_path = self.extract_result(result_path, working_dir)
            if result_path is None:
                print("Failed to extract results!")
                exit(1)

        # execute each inputs
        self.execute_test_driver(obj_file, result_path, working_dir)

        # make a report
        self.make_report(working_dir)

        # compress the execution result
        ext = ""
        if config.UNCOMPRESS_RESULT is False:
            print("Compressing the execution results ...")
            ext = self.compress_working_dir(working_dir)

            print("Removing the execution results ...")
            self.remove_working_dir(working_dir)

        # move results
        if working_dir != output_dir:
            print("Moving the execution results to output directory ...")
            utils.prepare_directory(os.path.dirname(output_dir))
            self.move_execution_results(working_dir + ext, output_dir + ext)
        print("Please find the results: %s " % output_dir)

        print("Finished reproducing.")
        pass

    ########################################################
    # sub functions
    ########################################################
    def extract_result_all(self, _result_path, _working_dir):
        print("Uncompress AFL results into {} ...".format(_working_dir))

        # create directory for tarfile to be extracted
        extract_path = utils.makepath(_working_dir, "AFL")
        utils.prepare_directory(extract_path)

        # uncompress inputs
        abs_tar_file = os.path.abspath(_result_path)
        tar_cmd = "tar xf {}".format(abs_tar_file)
        ret = utils.shell.execute_and_check(tar_cmd, "retcode", 0, _working_dir=extract_path)
        if ret is None or ret is False:
            return None

        return extract_path

    def extract_result(self, _result_path, _working_dir):
        print("Uncompress AFL results into {} ...".format(_working_dir))

        # create directory for tarfile to be extracted
        extract_path = utils.makepath(_working_dir, "AFL")
        utils.prepare_directory(extract_path)

        # uncompress total.log
        abs_tar_file = os.path.abspath(_result_path)
        tar_cmd = "tar xf {} ./total.log".format(abs_tar_file)
        ret = utils.shell.execute_and_check(tar_cmd, "retcode", 0, _working_dir=extract_path)
        if ret is None or ret is False:
            print("There is no total.log")
            return None
        print("Uncompressed total.log")

        # uncompress inputs
        tar_cmd = "tar xf {} ./inputs".format(abs_tar_file)
        ret = utils.shell.execute_and_check(tar_cmd, "retcode", 0, _working_dir=extract_path)
        if ret is None or ret is False:
            print("There is no inputs - may be LIVE mutant")
            print("REPORT - total: 0, success: 0, abort: 0")
            return None
        print("Uncompressed inputs")
        return extract_path

    def execute_test_driver(self, _obj_file, _result_path, _working_dir):
        # get list of inputs
        input_path = utils.makepath(_result_path, "inputs")
        input_files = utils.get_all_files(input_path, "*.inb")

        print("Executing test driver: {} files found".format(len(input_files)))
        # print("Progress ", end="")
        count = 0
        update = int(len(input_files)/70)
        for filename in input_files:
            if update==0 or (count % update)==0:
                print("\t[{}/{}] {} ...".format(count, len(input_files), filename))
            # driver.obj <input> <output_path> [crash|all] [log]"
            exec_cmd = "{} {} {} crash log".format(_obj_file, filename, _working_dir)
            ret = utils.shell.execute_and_check(exec_cmd, "retcode", 0, _verbose=False)
            count += 1
            # if (count % update)==0:
                # print(".", end='')
        print("Done.")

    def make_report(self, _working_dir):
        f = open(utils.makepath(_working_dir, "total.log"), "r")
        lines = f.readlines()
        f.close()

        count_success = 0
        count_abort = 0
        for line in lines:
            line = line.strip()
            if line == "": continue
            cols = line.split(",")
            if cols[5] == 1:
                print("REPORT - Diff: {}".format(line))
                count_success += 1
            else:
                count_abort += 1

        print("REPORT - total: {}, success: {}, abort: {}".format(count_success+ count_abort, count_success, count_abort))
        return

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


    ########################################################
    # path utils
    ########################################################
    def get_result_path(self):
        result_path = utils.makepath(config.FUZZING_OUTPUT_PATH, config.MUTANT.dir_path, config.MUTANT.name)
        if config.RUN_ID is not None:
            result_path = utils.makepath(result_path, "Run%05d"% config.RUN_ID)

        # check if the path exists
        if os.path.exists(result_path) is False:
            result_path += ".tar"
            if os.path.exists(result_path) is True and os.path.isfile(result_path) is True:
                return result_path
            print("The result file is not properly specified. Please check you parameter.")
            print(" - expected result file: {}".format(result_path))
            return None

        if os.path.isdir(result_path) is True:
            # results check
            filepath = utils.makepath(result_path, "total.log")
            if os.path.exists(filepath) is True and os.path.isfile(filepath) is True:
                return result_path
            print("The result folder is not properly specified. Please check you parameter.")
            print(" - expected result folder: {}".format(result_path))
        return None

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

    def make_HPC_working_path(self, _output_dir):
        working_dir = _output_dir
        if config.HPC is True:
            working_dir = utils.makepath(config.HPC_EXEC_BASE, "__reproduce__", config.MUTANT.dir_path, config.MUTANT.name)
            if config.RUN_ID is not None:
                working_dir = utils.makepath(working_dir, "Run%05d"% config.RUN_ID)
        return working_dir


if __name__ == "__main__":
    Reproducer()
    exit(0)