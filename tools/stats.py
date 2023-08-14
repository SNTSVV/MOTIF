import sys
import argparse
if __package__ is None or __package__ == "":
    from ExpResult import ExpResult
else:
    from tools.ExpResult import ExpResult


#############################################################################################
# This code provides a shell command to make statistics of the AFL execution results
# Basically, it calls a class ExpResult that is located in the tool folder
# , which provides the statistic functions for the AFL results data
#############################################################################################
########################################################
# parse parameters
########################################################
def parse_arg():
    parser = argparse.ArgumentParser(description='Paremeters')
    parser.add_argument('-w', dest='workingPath', type=str, default=None, help='')
    parser.add_argument('-f', dest='inputFilter', type=str, default=None, help='')
    parser.add_argument('--plus', dest='AFLplus', action='store_true', help='(boolean) the result made by AFL plus')

    # parameter parsing
    args = sys.argv[1:]  # remove executed file
    args = parser.parse_args(args=args)
    if args.workingPath is None or len(args.workingPath) == 0:
        parser.print_help()
        exit(1)

    if args.inputFilter is None or len(args.inputFilter) == 0:
        parser.print_help()
        exit(1)

    return args


if __name__ == "__main__":
    args = parse_arg()
    obj = ExpResult(args.workingPath, _input_filter=args.inputFilter, _use_AFL_plus=args.AFLplus)
    obj.make_stats_total_log()

