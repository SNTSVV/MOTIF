
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pipeline import utils
from pipeline import Config
import tools.utils


class InputConvertor():
    REPR_OUTPUT_NAME = '9-test'
    ENDIAN = "little"

    def __init__(self):
        args = self.arg_parse()
        if args['target'] is not None:
            self.REPR_OUTPUT_NAME = args['target']

        global config
        params = Config.parse_arg()
        config = Config.configure(params)
        if config.NO_CONFIG_VIEW is False:
            config.print_config()
        config.verify_config()

        # proceed each phase
        if config.PHASE in ["all", "run"]:
            self.run(config.MUTANT['func'], _AFLinput=args['AFL'])
        pass

    def run(self, _func_name, _AFLinput=False):
        # error check
        if hasattr(self, _func_name) is False:
            print("We have no function to deal with : %s\nPlease implement it."%_func_name)
            return 0

        # determine paths for working
        result_path = self.get_output_path(self.REPR_OUTPUT_NAME)
        if result_path is None or os.path.exists(result_path) is False:
            print("Cannot found the result file or path.")
            exit(1)

        # get list of inputs
        print("Searching inputs in %s"% result_path)
        input_files = self.get_list_inputs(result_path, _AFLinput=_AFLinput)

        print("The number of inputs: {}".format(len(input_files)))
        count = 0
        for filename in input_files:
            # driver.obj <input> <output_path> [crash|all] [log]"
            ID = self.get_ID_from_file(filename, _AFLinput=_AFLinput)
            count += getattr(self, _func_name)(ID, filename)
            # if count==10: break
        print("We found %d inputs that we concern"%count)
        print("Done.")

        pass

    ########################################################
    # path utils
    ########################################################
    def get_list_inputs(self, _result_path, _AFLinput=True):
        if _AFLinput is True:
            input_path = utils.makepath(_result_path, "default", "crashes")
            input_files = utils.get_all_files(input_path, "id*")
            input_files = sorted(input_files)
        else:
            input_path = utils.makepath(_result_path, "inputs")
            input_files = utils.get_all_files(input_path, "*.inb")
            input_files = sorted(input_files)
        return input_files

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

    def get_ID_from_file(self, _filename, _AFLinput=True):
        if _AFLinput is True:
            fname = os.path.basename(_filename)
            items = fname.split(",")
            key, value = items[0].split(":")
            ID = int(value)
        else:
            ID = int(os.path.basename(_filename)[:-4])
        return ID

    ########################################################
    # sub functions
    ########################################################
    def num_digits(self, _num):
        digits = 0
        while _num != 0:
            _num //= 10
            digits += 1
        return digits

    def timestamp_add(self, _ID, _filename):
        bytes = open(_filename, "rb").read()

        base_sec = int.from_bytes(bytes[:4], byteorder=self.ENDIAN, signed=False)
        base_nsec = int.from_bytes(bytes[4:8], byteorder=self.ENDIAN, signed=False)
        add_sec = int.from_bytes(bytes[8:12], byteorder=self.ENDIAN, signed=False)
        add_nsec = int.from_bytes(bytes[12:16], byteorder=self.ENDIAN, signed=False)

        COND = 1000000000
        if base_sec + add_sec > 4294967295:  # for buggy 1
        # if base_nsec + add_nsec > 2*COND:  # for buggy 2
        # if base_nsec >= COND and add_nsec >= COND:  # for buggy 2
            print("[%d] base: {%d, %d}, add: {%d, %d}"%(_ID, base_sec, base_nsec, add_sec, add_nsec))
            # found what we target
            return 1
        return 0

    def long_to_string(self, _ID, _filename):
        bytes = open(_filename, "rb").read()

        buf = bytes[:21].decode("utf-8", errors="ignore")
        buf_size = int.from_bytes(bytes[21:29], byteorder=self.ENDIAN, signed=False)
        lvalue = int.from_bytes(bytes[29:37], byteorder=self.ENDIAN, signed=True)

        digits = self.num_digits(abs(lvalue))
        if lvalue < 0: digits +=10 # add 9 because the target function returns "Unkonwn(%ld)" when it deals with negative value

        if buf_size >= digits:
            buf_hex = ','.join(['0x%02X'%item for item in bytes[:21]])
            print("[%5d] value: %-20ld, buf_size: %-20ld, buf: %-24s, buf_hex: %s}"%(_ID,  lvalue, buf_size, buf, buf_hex))
            # found what we target
            return 1
        return 0

    def gs_clock_from_string(self, _ID, _filename):
        bytes = open(_filename, "rb").read()

        buf = bytes[:21].decode("utf-8", errors="ignore")
        ts_sec = int.from_bytes(bytes[21:25], byteorder=self.ENDIAN, signed=False)
        ts_nsec = int.from_bytes(bytes[25:29], byteorder=self.ENDIAN, signed=False)

        cols = buf.split(".")
        if len(cols)==2 and cols[0].isnumeric() and cols[1].isnumeric() and self.num_digits(abs(int(cols[1])))>10:
        # if len(cols)==2 and cols[0].isnumeric() and cols[1].isnumeric():
        # if len(cols)==2 and cols[0].strip().isnumeric() and cols[1].strip().isnumeric():
        # if len(cols)==2:
        # if True:
            buf_hex = ','.join(['0x%02X'%item for item in bytes[:21]])
            print("[%5d] ts: {%10ld, %10ld}, str: %-24s, str_hex: %s}"%(_ID,  ts_sec, ts_nsec, buf, buf_hex))
            # found what we target
            return 1
        return 0

    def timestamp_diff(self, _ID, _filename):
        bytes = open(_filename, "rb").read()

        base_sec = int.from_bytes(bytes[:4], byteorder=self.ENDIAN, signed=False)
        base_nsec = int.from_bytes(bytes[4:8], byteorder=self.ENDIAN, signed=False)
        diff_sec = int.from_bytes(bytes[8:12], byteorder=self.ENDIAN, signed=False)
        diff_nsec = int.from_bytes(bytes[12:16], byteorder=self.ENDIAN, signed=False)

        # if base_sec < diff_sec  and base_nsec < diff_nsec:  # for buggy 1 (missing one condition)
        if base_sec < diff_sec or  (base_sec == diff_sec and base_nsec < diff_nsec): # for buggy 1
        # if True:
        # if base_nsec < diff_nsec:
                print("[%d] base: {%d, %d}, diff: {%d, %d}"%(_ID, base_sec, base_nsec, diff_sec, diff_nsec))
                # found what we target
                return 1
        COND = 1000000000

        return 0

    ########################################################
    # arg parsing
    ########################################################
    def arg_parse(self):
        info = [
            {"name":"AFL", "key":"--AFL", "default":False, "type":"bool"},
            {"name":"target", "key":"--target", "default":None, "type":"string"}
        ]
        return tools.utils.parse_args_with_remove(info)


if __name__ == "__main__":
    # basic arguments: [--AFL] [--target target]
    #   * --AFL: (boolean) convert inputs from the AFL crashes folder otherwise from our test driver
    #   * --target: specify the target name to load the input files (e.g., 6-fuzzing, 8-test ...)
    # config arguments: [-c CONFIG] [-J JOB_NAME] [-t TAG_NAME] <MUTANT_NAME> <INPUT_FILTER> run
    # -c config.py -J _verify -t 5m --runID 1 timestamp.mut.13.2_7_56.AOR.timestamp_add.c A run # -c config.py -J _verify -t 5m --runID 1 memory.mut.8.1_1_9.ABS.long_to_string.c A run

    InputConvertor()
    exit(0)
