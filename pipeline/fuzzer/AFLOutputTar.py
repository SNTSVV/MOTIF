import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shutil
import tarfile
from tarfile import TarInfo
from pathlib import Path
from pipeline import utils
from pipeline.fuzzer import AFLOutput



#####
# This class analyzes a tar file that contains fuzzing results and used to produce summary informations
# It is inherited ExpResult class to analyze the results and provides the files that ExpResults requires
#####
class AFLOutputTar(AFLOutput):
    TAR = None
    TAR_FILENAME = None
    DELETE_TEMP_DIR = True

    def __init__(self, _filename=None, _temp_dir=None, _num_seeds=3, _dist_basenum=5000, _isAFLpp=False):
        if os.path.exists(_filename) is False:
            print('Not exist tar file: %s'%_filename)
            exit(1)

        if _temp_dir is None:
            dirname = os.path.dirname(_filename)
            filename = os.path.basename(_filename)
            names = os.path.splitext(filename)
            self.INTERMEDIATE = os.path.join(dirname, names[0] + "_tar")
        else:
            self.INTERMEDIATE = _temp_dir

        self.TAR_FILENAME = os.path.abspath(_filename)
        self.TAR = tarfile.open(_filename)

        if self.DELETE_TEMP_DIR is True and os.path.exists(self.INTERMEDIATE):
            shutil.rmtree(self.INTERMEDIATE)

        super().__init__(self.INTERMEDIATE, _num_seeds, _dist_basenum, _isAFLpp)
        pass

    def extract_file(self, _target):
        # extract required files from tar file into a temp directory (self.INTERMEDIATE)
        try:
            cmd = "tar -xf %s %s"%(self.TAR_FILENAME, _target)
            if os.path.exists(self.INTERMEDIATE) is False:
                os.makedirs(self.INTERMEDIATE)
            ret, lines = utils.shell.execute(cmd, _working_dir=self.INTERMEDIATE)
            if ret != 0:
                raise KeyError()
            # self.TAR.extract(_target, path=self.INTERMEDIATE)
        except KeyError as e:
            # print(str(e))
            print("\t- "+ _target + ' file is not in the archive')
            return None
        return utils.makepath(self.INTERMEDIATE, _target)

    def extract_tar(self, _folder=None):
        if _folder is None:
            _folder = self.INTERMEDIATE

        try:
            cmd = "tar -xf %s"%(self.TAR_FILENAME)
            if os.path.exists(_folder) is False:
                path = Path(_folder)
                path.mkdir(parents=True)
            ret, lines = utils.shell.execute(cmd, _working_dir=_folder)
            if ret != 0:
                raise KeyError()
        except KeyError as e:
            print(str(e))
            return None
        return _folder

    def list_files(self, _target=None, _verbose=True, _onlyfiles=False):
        filepaths = []

        members = self.TAR.getmembers()
        for member in members:
            if _onlyfiles is True and member.isdir(): continue
            if _target is not None  and member.name.startswith(_target) is False: continue
            filepaths.append(member.name)

        if _target is not None and _verbose is False:
            filepaths = [filename[len(_target)+1:] for filename in filepaths]

        return filepaths

    def close(self):
        if self.DELETE_TEMP_DIR is True and os.path.exists(self.INTERMEDIATE):
            shutil.rmtree(self.INTERMEDIATE)
        self.TAR.close()

    ###############################################################
    # get total number of inputs that tested in the AFL (__num__ file)
    ###############################################################
    def get_number_of_inputs(self):
        filepath = self.extract_file(self.NUM_INPUT_FILENAME)
        if filepath is None: return None

        return super().get_number_of_inputs()

    ###############################################################
    # load plot data
    ###############################################################
    def load_plot(self, _reverse=False, _n_lines=0):
        # load file
        filepath = self.extract_file(utils.makepath(self.AFL_SUB_DIR, self.PLOT_DATA))
        if filepath is None: return None

        return super().load_plot(_reverse, _n_lines)

    ###############################################################
    # get total execution log information
    ###############################################################
    def load_stats_total_log(self, _remake=False):
        self.extract_file(self.TOTAL_LOG_STATS)
        # I do not check the existence of stats, because it will make stats if the stats file does not exist
        return super().load_stats_total_log(_remake)

    def make_stats_total_log(self):
        logfile = self.extract_file(self.TOTAL_LOG)
        if logfile is None: return None, None
        return super().make_stats_total_log()

    def load_total_execution_log(self):
        logfile = self.extract_file(self.TOTAL_LOG)
        if logfile is None: return None
        return super().load_total_execution_log()

    def convert_total_execution_log(self):
        logfile = self.extract_file(self.TOTAL_LOG)
        if logfile is None: return None
        return super().convert_total_execution_log()

    ###############################################################
    # load fuzzer
    ###############################################################
    def load_fuzzer_stats(self, _key=None):
        filepath = self.extract_file(utils.makepath(self.AFL_SUB_DIR, self.FUZZER_STATS))
        if filepath is None: return None

        return super().load_fuzzer_stats(_key)

    ########################################################
    # Test function
    ########################################################
    def check_fuzzing_result(self, _result_tar, _intermediate, _input_filter):
        tar = AFLOutputTar(_result_tar, _intermediate)

        # Check result in the plot data
        plot_data = tar.load_plot(_reverse=True, _n_lines=2)
        result = "ERROR"
        if plot_data is not None:
            if len(plot_data) == 0 : result = "NO_LINE"  # less than 1 cycle
            if plot_data[0]["unique_crashes"] > 0: result = "KILLED"
            if plot_data[0]["unique_crashes"] == 0: result = "LIVE"

        # Check result from the number of inputs (check whether crashed or not)
        if result == "NO_LINE":
            nInputs = tar.get_number_of_inputs()
            if nInputs is None: result = "ERROR"
            if nInputs > 0: result = "CRASHED"
            nSeed = tar.get_number_of_seeds()
            if nInputs != -1 and nInputs <= nSeed:      # AFL says CRASHED when it failed to execute SUT in perform_dry_run()
                result = "CRASHED"
        tar.close()

        # TODO :: Extract time information from plot_data
        return result


    ########################################################
    # Find issue executions in Tar file
    ########################################################
    def find_issue_executions(self):
        if self.extract_file( self.TOTAL_LOG ) is None: return None
        if self.extract_file( utils.makepath(self.AFL_SUB_DIR, self.FUZZER_STATS) ) is None: return None

        super().find_issue_executions()

    def get_timeIDs_from_detailed_logs(self):
        '''
        extracts all timeIDs from log list from the detailed logs folder
        :return:
        '''
        all_files = self.TAR.getmembers()

        timeIDs = set([])
        for afile in all_files:
            if afile.name.startswith(self.DETAILED_LOG_PATH) is False: continue
            if afile.name == self.DETAILED_LOG_PATH: continue  # ignore the folder itself

            filename = os.path.basename(afile.name)
            timeID = int(filename[:-4])  # remove extension (from <timeID>.log to <timeID>)
            timeIDs.add(timeID)

        return timeIDs

    def extract_inputs(self, _listID):
        print("Extracting input files...")
        for execID in _listID:
            print(" - %s "% str(execID), end='')
            if isinstance(execID, str) is True:
                execID = int(execID)

            # save input
            self.extract_file(self.get_input_detail_filepath(execID))
            self.extract_file(self.get_input_detail_filepath(execID, _revised=True))
            print("Done")

    def extract_detail_log(self, _listID):
        print("Extracting log files...")
        for execID in _listID:
            print(" - %s "% str(execID), end='')
            if isinstance(execID, str) is True:
                execID = int(execID)

            # save file
            self.extract_file(self.get_log_detail_filepath(execID))
            print("Done")


def test(obj, _filename):
    data = obj.load_total_execution_log()
    out = open(_filename, "w")
    out.write("TestID,Time,Origin,Mutant,Comparison\n")

    for record in data:
        out.write("%d,%d,%s,%s,%s\n" % (record['run'], record['unixtime'], record['check'][0], record['check'][1], record['check'][2]))

    out.close()


if __name__ == "__main__":
    baseDir = 'case_studies/ASN1/_Multi/6-fuzzing-24H'
    targetDirs = [
        './test/test.mut.11.1_1_49.ABS.long_to_string.tar',
    ]

    for idx in range(0, len(targetDirs)):
        print('::: Working with %s'%targetDirs[idx])
        obj = AFLOutputTar(os.path.join(baseDir,targetDirs[idx]), utils.makepath(baseDir, "__tmp_dir__", str(idx)))
        files = obj.list_files("./inputs/", _onlyfiles=True)
        for file in files:
            print(file)
        # obj.convert_total_execution_log()
        # obj.find_issue_executions()
        # obj.extract_inputs(targetIDs[idx])
        # obj.extract_detail_log(targetIDs[idx])
        obj.close()




    #
    # # load plot data and print
    # data = obj.load_plot()
    # print("Plot data: ")
    # for row in data:
    #     print(row)
    # print("number of inputs: %d" % obj.get_number_of_inputs())
    #
    # filename = obj.convert_total_execution_log()
    # print("saved execution log: %s"%filename)
    pass


