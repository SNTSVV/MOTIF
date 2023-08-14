import os
import tools.utils


class Statistics():
    output = None
    records = []

    def __init__(self):
        # parameter setting
        global params
        params = self.parse_arg()

        # set work names
        logName = 'logs'
        workName = params.expName
        if params.tagName is not None and params.tagName != '':
            logName = logName + '-' + params.tagName        # logs[-tagName]
            workName = workName + '-' + params.tagName      # regress[-tagName]

        target = os.path.join(params.basePath, params.expName, logName)
        pattern = "%s-run.*" % workName
        cmdName = "%s-run.cmd" % workName
        command_file = os.path.join(params.basePath, params.expName, cmdName)

        # load all files related to results of fuzzer
        targets = tools.utils.expandDirs([{'path':target}], 'Log', _ptn=pattern, _sort=True)
        targets = tools.utils.getFiles(targets, 'Run', _ptn="([0-9]+).out", _sort=True)

        # counts live, killed and crashed mutants
        counts = self.check_results(targets, command_file)

        # report statistics
        print("\n\n")
        print("Total mutants: %d" % (sum(counts.values())))
        for key in counts.keys():
            print("Total %s mutant: %d" % (key, counts[key]))
        print("Done.")
        pass

    def check_results(self, _targets, _cmd_file):
        self.open_output(params.outputPath)
        self.print("CommandNo,MutantID,Filemame,RunID,Result,Description")

        # count variables
        count = {'LIVE':0, 'KILLED':0, 'CRASHED':0}

        # count variables
        for target in _targets:
            log_results_filepath = target['path']
            line_no = target['ID']

            mutant_filename, runID = self.get_execution_info_from_commands_file(_cmd_file, _line_no=line_no)
            mutantID = self.get_mutant_id(mutant_filename)

            # read each line of code
            for line in self.readline_reverse(log_results_filepath, _max=50):
                exitType = self.check_exit_type_in_line(line)
                if exitType is None: continue

                count[exitType] += 1
                self.print("%d,%s,%s,%s,%s,%s"%(target['ID'],
                                                str(mutantID),
                                                mutant_filename,
                                                str(runID),
                                                exitType,
                                                line.strip())
                )
                break

        self.close_output()
        return count

    def check_exit_type_in_line(self, _line):
        # check crashed item
        if _line.find("the program crashed with one of the test cases provided.") >= 0:
            return 'CRASHED'

        # check live/killed item
        if _line.find("Fuzzing test case") < 0: return None
        if _line.find(" 0 uniq") >= 0:
            return 'LIVE'

        return 'KILLED'

    def get_mutant_id(self, _mutant_name):
        if params.mutantPath is None: return None

        mutants = open(params.mutantPath, "r").readlines()

        for idx in range(0, len(mutants)):
            if mutants[idx].find(_mutant_name) < 0: continue
            return idx + 1  # return ID

        return None

    ########################################################
    # Utils
    ########################################################
    def get_execution_info_from_commands_file(self, _command_file, _line_no):
        lines = open(_command_file, "r").readlines()
        line = lines[_line_no-1]

        cmds = line.split(" ")
        runID = None
        for idx in range(0, len(cmds)):
            if cmds[idx] != "--runID": continue
            runID = int(cmds[idx+1])
            break
        return (cmds[-3], runID)   # mutant filename, runID

    def readline_reverse(self, _file_name, _max=None):
        count = 0

        # Open file for reading in binary mode
        with open(_file_name, 'rb') as read_obj:
            # Move the cursor to the end of the file
            read_obj.seek(0, os.SEEK_END)
            # Get the current position of pointer i.e eof
            pointer_location = read_obj.tell()
            # Create a buffer to keep the last read line
            buffer = bytearray()
            # Loop till pointer reaches the top of the file
            while pointer_location >= 0:
                # Move the file pointer to the location pointed by pointer_location
                read_obj.seek(pointer_location)
                # Shift pointer location by -1
                pointer_location = pointer_location -1
                # read that byte / character
                new_byte = read_obj.read(1)
                # If the read byte is new line character then it means one line is read
                if new_byte == b'\n':
                    # Fetch the line from buffer and yield it
                    yield buffer.decode()[::-1]
                    if _max is not None:
                        count += 1
                        if count >= _max: break
                    # Reinitialize the byte array to save next line
                    buffer = bytearray()
                else:
                    # If last read character is not eol then add it in buffer
                    buffer.extend(new_byte)
            # As file is read completely, if there is still data in buffer, then its the first line.
            if len(buffer) > 0:
                # Yield the first line too
                yield buffer.decode()[::-1]
                if _max is not None:
                    count += 1
        return True

    ########################################################
    # File writer manager
    ########################################################
    def open_output(self, _output):
        self.output = None
        if _output is not None:
            self.output = open(_output, "w")
        pass

    def print(self, _msg):
        self.records.append(_msg)
        print(_msg)
        if self.output is not None:
            self.output.write(_msg+"\n")
        pass

    def close_output(self):
        if self.output is not None:
            self.output.close()
        pass

    ########################################################
    # parse parameters
    ########################################################
    def parse_arg(self):
        import argparse
        import sys
        parser = argparse.ArgumentParser(description='Paremeters')
        parser.add_argument('-b', dest='basePath', type=str, default=None, help='base path')
        parser.add_argument('-J', dest='expName', type=str, default=None, help='experiment name (job name)')
        parser.add_argument('-t', dest='tagName', type=str, default=None, help='sub dir pattern')
        parser.add_argument('-o', dest='outputPath', type=str, default=None, help='')
        parser.add_argument('-m', dest='mutantPath', type=str, default=None, help='target mutant file to fuzz')

        # parameter parsing
        args = sys.argv[1:]  # remove executed file
        args = parser.parse_args(args=args)
        if args.basePath is None or len(args.basePath)==0:
            parser.print_help()
            exit(1)

        if args.expName is None or len(args.expName)==0:
            parser.print_help()
            exit(1)

        return args


if __name__ == "__main__":
    Statistics()

    ## Usages
    # python3 ./tools/collector.py -b case_studies/ASN1 -J regress -t multi10h -o case_studies/ASN1/regress/summary_multi10.csv -m case_studies/ASN1/live_mutants

