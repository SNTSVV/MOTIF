import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from pipeline import utils
import tools.utils


#####
# This class analyzes a tar file that contains fuzzing results and used to produce summary informations
# It is inherited ExpResult class to analyze the results and provides the files that ExpResults requires
#####
class ExpResult():
    # target files in a tar file (all path should be started with './')
    PLOT_FILENAME = "./plot_data"     # plot data
    FUZZER_STATS = "./fuzzer_stats"   #
    TOTAL_LOG = "./total.log"         # simple log list
    NUM_INPUT_FILENAME = "./__num__"  # number of inputs in AFL  ( not used )
    DETAILED_LOG_PATH = "./logs"      # the folder that detailed logs are stored
    DETAILED_INPUT_PATH = "./inputs"  # the folder that all inputs are stored
    TOTAL_LOG_STATS = './stats.log'          # will be generated during analysis
    TOTAL_LOG_CONVERTED = './total_fix.log'  # will be generated during analysis

    # internal variable
    INPUT_FILTER = "A"
    DIST_BASENUM = 5000           # log distribution folder divider

    BASE_PATH = "./"
    AFL_RESULT_PATH = "./"

    def __init__(self, _basepath=None, _input_filter=None, _dist_basenum=None, _use_AFL_plus=False):
        self.BASE_PATH = _basepath
        self.INPUT_FILTER = _input_filter.strip() if _input_filter is not None else "A"
        self.DIST_BASENUM = _dist_basenum if _dist_basenum is not None else 5000
        if _use_AFL_plus is True:
            self.AFL_RESULT_PATH = "./default"
        pass

    ###############################################################
    # get total number of inputs that tested in the AFL (__num__ file)
    ###############################################################
    def get_number_of_inputs(self):
        filepath = utils.makepath(self.BASE_PATH, self.NUM_INPUT_FILENAME)
        if os.path.exists(filepath) is False: return None

        # find tar file
        value = open(filepath, "r").read()
        value = value.strip()

        if value is None or value == "":
            return -1
        return int(value)

    ###############################################################
    # load plot data
    ###############################################################
    def load_plot(self, _reverse=False, _n_lines=0):
        '''
        return plot_data as a list of dicts:
        [
            {
            "unix_time":time (unixtime, sec), "elapsed_time":time (sec), "cycles_done":N,
            "cur_path":N, "paths_total":N, "pending_total":N, "pending_favs":N,
             "map_size":R, "unique_crashes":N, "unique_hangs":N, "max_depth":N, "execs_per_sec":R]
            },
            ...
        ]

        :param _reverse:
        :param _n_lines:
        :return:
        '''
        # load file
        filepath = utils.makepath(self.BASE_PATH, self.AFL_RESULT_PATH, self.PLOT_FILENAME)
        if os.path.exists(filepath) is False: return None

        # get data
        data = []
        inital_time = 0
        if _reverse is False:
            with open(filepath, 'r') as read_obj:
                lines = read_obj.readlines()
                for line in lines:
                    if line == "": continue
                    if line.startswith("#") is True: continue
                    item = self.convert_plot_line(line)
                    if inital_time == 0: inital_time = item['unix_time']
                    item['elapsed_time'] = item['unix_time'] - inital_time
                    data.append(item)
        else:
            for line in tools.utils.readline_reverse(filepath, _n_lines if _n_lines >0 else None):
                if line == "": continue
                if line.startswith("#") is True: continue

                item = self.convert_plot_line(line)
                if inital_time == 0: inital_time = item['unix_time']
                item['elapsed_time'] = item['unix_time'] - inital_time
                data.append(item)

        return data

    def load_plot_load_times(self):
        data = self.load_plot()
        if data is None: return None
        values = [item['unix_time'] for item in data]
        return values

    def load_plot_crashes(self):
        data = self.load_plot()
        if data is None: return None
        values = [item['unique_crashes'] for item in data]
        return values

    def load_plot_total_paths(self):
        data = self.load_plot()
        if data is None: return None
        values = [item['paths_total'] for item in data]
        return values

    def convert_plot_line(self, _line):
        '''
        Convert plot line into a dictionary
        :param _line:
        :return:
        '''
        colnames = ["unix_time", "cycles_done", "cur_path", "paths_total", "pending_total", "pending_favs", "map_size", "unique_crashes", "unique_hangs", "max_depth", "execs_per_sec"]
        cols = _line.split(',')
        values = []
        for idx in range(0, len(cols)):
            value = cols[idx].strip()
            if idx == 6:
                value = float(value[:-1])*100
            elif idx == 10:
                value = float(value)
            else:
                value = int(value)
            values.append(value)

        res_dct = dict(zip(colnames, values))
        return res_dct

    ###############################################################
    # get total execution log after processing
    ###############################################################
    def load_stats_total_log(self, _remake=False):
        statsfile = utils.makepath(self.BASE_PATH, self.TOTAL_LOG_STATS)
        if _remake is True or os.path.exists(statsfile) is False:
            print("\t- Not exist stats file, we are going to make it now.")
            self.make_stats_total_log()

        file_content = open(statsfile, 'r').read()
        data = json.loads(file_content)
        return data

    def make_stats_total_log(self):
        # get data
        counts, elapsed = self.get_stats_total_log()
        data = {"counts":counts, "elapsed":elapsed}

        # store data
        statsfile = utils.makepath(self.BASE_PATH, self.TOTAL_LOG_STATS)
        with open(statsfile, "w") as f:
            json.dump(data, f)
        pass

    def get_stats_total_log(self):
        '''
        get basic statistics from the total log

        We do not consider the last execution if the execs_done (from AFL stats) is less than the actual number of executions,
        since we assume that AFL stopped during the last execution.
        :return:
        '''

        # get full path of the total log file
        filepath = utils.makepath(self.BASE_PATH, self.TOTAL_LOG)
        if os.path.exists(filepath) is False: return None, None

        # make statistics
        counts = {"all":0, "initial":0, "origin":0, "mutant":0, "comp":0}
        elapsed = {"all":-1, "initial":-1, "origin":-1, "mutant":-1, "comp":-1}
        stage = None
        flag_elapsed = False
        for record in self.iter_simple_execution_log(filepath):
            # some executions are missing. (I think this is timeout..but..we don't even have log...)
            # so I keep the last sequence ID
            counts['seq'] = record['seq']
            counts['all'] += 1

            # counts for each stage
            stage = None
            flag_elapsed = False
            if   record['initial'] is False: stage = 'initial'
            elif record['origin']  is False: stage = 'origin'
            elif record['mutant']  is False: stage = 'mutant'
            elif record['comp']    is False: stage = 'comp'
            if stage is not None:
                counts[stage] += 1
                if elapsed[stage] == -1:
                    flag_elapsed = True
                    elapsed[stage] = record['elapsed']

        # Rollback if the last execution is the non-completed execution
        #   - When a timeout of an execution happens, the execution is crashed, which will be considered in the analysis below.
        #   - When AFL finished during precondition checking, it has no _execs_done value, then we consider all the inputs.
        exec_done = self.load_fuzzer_stats(_key='execs_done')
        if exec_done is not None and exec_done < counts['seq']:
            counts['all'] -=1
            if stage is not None:
                counts[stage] -= 1
                if flag_elapsed is True: elapsed[stage] = -1

        return counts, elapsed

    def load_total_execution_log(self):
        filepath = utils.makepath(self.BASE_PATH, self.TOTAL_LOG)
        if os.path.exists(filepath) is False: return None

        data = []
        # add additional data
        for record in self.iter_simple_execution_log(filepath):
            data.append(record)
        return data

    def convert_total_execution_log(self):
        # get full path of the total log file
        filepath = utils.makepath(self.BASE_PATH, self.TOTAL_LOG)
        if os.path.exists(filepath) is False: return None

        output = utils.makepath(self.BASE_PATH, self.TOTAL_LOG_CONVERTED)
        out = open(output, "w")
        out.write("SeqID,TimeID,Time,Initial,Origin,Mutant,Comparison,ElapsedTime\n")

        for record in self.iter_simple_execution_log(filepath):
            out.write("%d,%d,%d,%s,%s,%s,%s,%.3f\n" % (record['seq'], record['timeID'], record['unixtime'],
                                                  record['initial'], record['origin'],
                                                  record['mutant'], record['comp'], record['elapsed']))
            out.flush()

        out.close()
        return output

    def iter_simple_execution_log(self, _filepath):
        '''
        return an execution result as a dict
        {'run':0         # execution Order (the same to the number of input in AFL)
         'timeID':0,     # execution ID (time ID)
         'unixtime':0,   # last executed time in seconds
         'check': [
                False,   # True if the execution passes the initialization code
                False,   # True if the execution passes the original function call code
                False,   # True if the execution passes the mutated function call code
                False    # True if the comparison results of both function executions are identical
            ]
        'elapsed':0000000000  # unix time in seconds
        }
        :return:
        '''
        # load specified file
        file = open(_filepath, "r")
        line = file.readline()       # throw away the first line (title line)

        # a record for one execution
        startTime = 0
        while True:
            line = file.readline()
            line = line.strip()
            if line == '': break

            # convert column values
            cols = line.split(',')
            seqID    = int(cols[0].strip())
            timeID   = int(cols[1].strip())
            initial  = int(cols[2].strip())
            original = int(cols[3].strip()) if len(cols)>3 else 0
            mutated  = int(cols[4].strip()) if len(cols)>4 else 0
            comp     = int(cols[5].strip()) if len(cols)>5 else 0

            item = {'seq':seqID, 'timeID':timeID, 'unixtime':0,
                    'initial': False,'origin': False,'mutant': False,'comp': False}

            # update current data
            item['initial'] = True if initial == 1 else False
            item['origin'] = True if original == 1 else False
            item['mutant'] = True if mutated == 1 else False
            item['comp'] = True if comp == 1 else False

            if startTime == 0:
                item['elapsed'] = 0
                startTime = timeID
            else:
                item['elapsed'] = (timeID - startTime) / 1000000  # convert the time to seconds

            yield item.copy()

        file.close()
        return True

    ###############################################################
    # get the number of seeds
    ###############################################################
    def get_number_of_seeds(self):
        # get the number of seed inputs
        if self.INPUT_FILTER.strip() == "": return 3

        cols = [item.strip() for item in self.INPUT_FILTER.split(';')]
        cols = list(filter(None, cols))
        if 'A' in cols:
            nSeed = 3
        else:
            nSeed = len(cols)
        return nSeed

    ###############################################################
    # load fuzzer
    ###############################################################
    def load_fuzzer_stats(self, _key=None):
        filepath = utils.makepath(self.BASE_PATH, self.AFL_RESULT_PATH, self.FUZZER_STATS)
        if os.path.exists(filepath) is False: return None

        lines = open(filepath, "r").readlines()

        data = {}
        for line in lines:
            line = line.strip()
            if line == '': continue
            cols = line.split(":")
            key = cols[0].strip()
            value = cols[1].strip()
            if value.isnumeric(): value = int(value)
            elif self.isdouble(value): value = float(value)
            elif self.ispercent(value): value = float(value[:-1])/100.0
            data[key] = value

        if _key is not None:
            if _key in data: return data[_key]
            else:            return None
        return data

    def get_num_execs(self):
        return self.load_fuzzer_stats("execs_done")

    def isdouble(self, _string:str):
        if _string.find(".") < 0: return False

        cols = _string.split(".")
        if len(cols) > 2: return False

        if cols[0].isnumeric() and cols[1].isnumeric():
            return True
        return False

    def ispercent(self, _string:str):
        if _string.endswith("%") is False: return False
        value = _string[:-1]
        if value.isnumeric() or self.isdouble(value): return True
        return False

    ########################################################
    # Find issue executions in Tar file
    ########################################################
    def find_issue_executions(self):
        crashes = self.load_plot_crashes()
        if crashes is None or len(crashes)==0: crashes = [0]
        print("\tNum of crashes: %d"%(crashes[-1]))

        counts = self.stat_execution_logs()
        print("\tstats: %s"%(str(counts)))

        execDone = self.load_fuzzer_stats(_key='execs_done')
        print("\tNumber of executions (finished): : %d"% execDone)

        log_IDs = self.get_timeIDs_from_detailed_logs()
        print("\tAll log executions: %d"% len(log_IDs))
        max_exec_ID = None
        if len(log_IDs)!=0:
            max_exec_ID = max(log_IDs)
            print("\tThe last execution ID: %d"%max_exec_ID)

        # check missing IDs in total log
        total_IDs = self.get_timeIDs_from_total_log()
        missing_IDs = log_IDs - total_IDs
        print("\tSee the missing IDs in `total.log`:")
        for ID in sorted(missing_IDs):
            if max_exec_ID is not None:
                if ID == max_exec_ID and execDone < len(log_IDs): continue
            distName = int(ID/self.DIST_BASENUM)*self.DIST_BASENUM
            print("\t\t> %s/logs/%11d/log_%d.txt"%(self.BASE_PATH, distName, ID))

            # executor = re.sub(r"(6-fuzzing[-\w]*)", '4-mutant-bins', self.BASE_PATH)+'.obj'
            # print("\t\t\t>> %s %s/inputs/%11d/input_%d.txt"%(executor, self.BASE_PATH, distName, ID))

    def stat_execution_logs(self):
        data = self.load_total_execution_log()

        counts = {"all":0, "initial":0, "origin":0, "mutant":0, "comp":0}
        for record in data:
            if record['check'][0] is False: counts['initial'] += 1
            elif record['check'][1] is False: counts['origin'] += 1
            elif record['check'][2] is False: counts['mutant'] += 1
            elif record['check'][3] is False: counts['comp'] += 1
            counts['all'] += 1
        return counts

    def get_timeIDs_from_total_log(self):
        filepath = utils.makepath(self.BASE_PATH, self.TOTAL_LOG)
        if os.path.exists(filepath) is False: return None

        lines = open(filepath, 'r').readlines()

        timeIDs = set([])
        for line in lines:
            if line.strip() == '': break
            cols = line.split(":")
            timeID = int(cols[0])
            timeIDs.add(timeID)

        return timeIDs

    def get_timeIDs_from_detailed_logs(self):
        workpath = utils.makepath(self.BASE_PATH, self.DETAILED_LOG_PATH)

        timeIDs = set([])
        subpaths = os.listdir(workpath)
        for subpath in subpaths:
            dist_path = utils.makepath(workpath, subpath)
            if os.path.isfile(dist_path) is True: continue
            logs = os.listdir(dist_path)
            for logfile in logs:
                timeID = int(logfile[:-4])  # remove extension (from <timeID>.log to <timeID>)
                timeIDs.add(timeID)

        return timeIDs

    ########################################################
    # Get path related to the dist number
    ########################################################
    def get_dist_num(self, _execID):
        return int(_execID/self.DIST_BASENUM)*self.DIST_BASENUM

    def get_input_detail_filepath(self, _execID, _revised=True):
        dist_num = self.get_dist_num(_execID)
        if _revised is False:
            filepath = utils.makepath(self.DETAILED_INPUT_PATH, "%d"%dist_num, "%d.inb"%_execID)
        else:
            filepath = utils.makepath(self.DETAILED_INPUT_PATH, "%d"%dist_num, "%d_revised1.inb"%_execID)
        return filepath

    def get_log_detail_filepath(self, _execID):
        dist_num = self.get_dist_num(_execID)
        filepath = utils.makepath(self.DETAILED_LOG_PATH, "%d"%dist_num, "%d.log"%_execID)
        return filepath


if __name__ == "__main__":
    # analysis for future
    targetDirs = [
        'case_studies/ASN1/_testAFL3/6-fuzzing-exp2/test/test.mut.11.1_5_38.ROR.test',
    ]
    for targetDir in targetDirs:
        print('::: Working with %s'%targetDir)
        obj = ExpResult(targetDir)
        # obj.convert_total_execution_log_from_non_tar(targetDir + '/total.log')
        obj.find_issue_executions()




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

