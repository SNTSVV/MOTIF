import os
import sys
import re
import subprocess
import psutil, signal
import time
from . import error


##################################################################
# Function to execute the given command and check the results
# :param _cmd: command that you want to execute in a shell
# :param _check_type: type of execution results that you want to check to confirm them
# :param _check_output: comparison value to check the execution results
# :param _working_dir: working directory
# :param _verbose: (boolean) whether the call print the execution log
# :param _line_no: an additional parameter when the _check_type is "text"
# :return: None if it has not satisfied the check condition otherwise return result
##################################################################
def execute(_cmd, _working_dir=None, _env=None, _verbose=False):
    process = None
    env_local = load_user_environment(_env)
    lines = []
    retcode = 0
    try:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        # execution
        process = subprocess.Popen(_cmd, shell=True, cwd=_working_dir, env=env_local,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while process.poll() is None:
            line = process.stdout.readline()
            if _verbose is True:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            line = ansi_escape.sub('', line.decode("utf-8", errors='ignore').strip())
            lines.append(line)

        retcode = process.returncode

    except subprocess.CalledProcessError as e:
        output = e.output.decode()
        error.error_exit("Error to execute the command: %s\nmsg: %s " % (_cmd, output))

    except KeyboardInterrupt:
        try:
            print("killing child process...")
            kill_child_processes()
            # if process is not None: process.terminate()
        except OSError:
            pass
        if process is not None: process.wait()
        error.error_exit("User canceled the execution")

    return retcode, lines


def execute_with_timeout(_cmd, _timeout, _working_dir=None, _env=None):
    process = None
    env_local = load_user_environment(_env)
    retcode = 0
    try:
        # execution
        process = subprocess.Popen(_cmd, shell=True, cwd=_working_dir, env=env_local)
        process.wait(timeout=_timeout)
        retcode = process.returncode

    except subprocess.CalledProcessError as e:
        output = e.output.decode()
        error.error_exit("Error to execute the command: %s\nmsg: %s " % (_cmd, output))

    except subprocess.TimeoutExpired as e:
        try:
            retcode = -9  # return code for timeout (killed by force)
            print(f'Timeout for {_cmd.split(" ")[1]} ({_timeout}s) expired, we force to kill the process ...', file=sys.stderr)
            kill_child_processes()
            # os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            time.sleep(1)  # Wait for the actual termination
        except OSError:
            pass
        # if process is not None: process.wait()

    except KeyboardInterrupt:
        try:
            print("killing child process...")
            kill_child_processes()
            # if process is not None: process.terminate()
        except OSError:
            pass
        if process is not None: process.wait()
        error.error_exit("User canceled the execution")

    return retcode


def execute_and_check(_cmd, _check_type, _check_output, _working_dir=None, _env=None, _verbose=False, _line_no=None):
    if _check_type not in [ 'retcode',  'file', 'lines', 'text', 'startswith']:
        error.error_exit("You provided a wrong _check_type: %s" % _check_type)

    # execute the command
    retcode, lines = execute(_cmd, _working_dir,_env,_verbose)

    # checking execution results
    if _check_type == "retcode":
        if isinstance(_check_output, list) is False:
            _check_output = [_check_output]
        return retcode if retcode in _check_output else None

    if _check_type == "lines":
        if len(lines) != _check_output:
            print('\n'.join(lines))
            return None
        return len(lines)

    if _check_type == "file":
        return _check_output if os.path.exists(_check_output) else None

    if _check_type == "text":
        return lines[_line_no] if lines[_line_no] == _check_output else None

    if _check_type == "startswith":
        if _line_no is not None:
            text = lines[_line_no]
        else:
            text = '\n'.join(lines)
        return _check_output if text.startswith(_check_output) else None

    return None


def kill_child_processes(sig=signal.SIGTERM):
    try:
        pid = os.getpid()
        parent = psutil.Process(pid)
        time.sleep(1)   # else /proc is not ready for read
        children = parent.children(recursive=True)
        for child in children:
            print("killing subprocess (%d): %s"%(child.pid, str(child.name())))
            child.send_signal(sig)

    except psutil.NoSuchProcess:
        return False
    return True


def load_user_environment(_env):
    env_local = os.environ.copy()

    if _env is not None:
        # convert all values into string
        for key in _env.keys():
            _env[key] = str(_env[key])

        # showing the values
        print("Additional Environment:", flush=True)
        for key in _env.keys():
            _env[key] = str(_env[key])
            print("export %s=%s"%(key, _env[key]), flush=True)

        # apply user environment
        env_local.update(_env)
    return env_local


def is_global_command(_command):
    if _command.find("/") < 0: return True
    return False


def exist_global_command(_command):
    ret, lines = execute("whereis "+_command)
    if ret != 0:
        error.error_exit("Cannot execute `whereis` command")
        return False

    for line in lines:
        line = line.strip()
        if len(line) == 0: continue

        # split the result
        cols = line.split(":")
        if len(cols) < 2: continue

        # strip each column
        cols[0] = cols[0].strip()
        cols[1] = cols[1].strip()
        if cols[0] != _command: continue

        # compare the final condition
        if len(cols[1].strip()) != 0:
            return True

    return False