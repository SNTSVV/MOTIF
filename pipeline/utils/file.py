import os
import sys
import stat
import importlib
import glob
from . import error

##################################################################
# Import a module from a file (load a python file as a variable)
# :param _filepath: filepath that contains a python module
# :return: return an object that contains a module loaded from the _filename
##################################################################
# load python module from the specified file
def load_module(_filepath):
    path, filename = os.path.split(_filepath)
    filename, ext = os.path.splitext(filename)
    sys.path.insert(0, path)
    module = importlib.import_module(filename, path)
    importlib.reload(module)  # Might be out of date
    del sys.path[0]
    return module


##################################################################
# Listing all directories that contain files that match with a _filefilter
# :param _path:
# :param _filefilter:
# :param _subName: if it is True, return the relative filepath from the _path
# :return: list of all directory paths
##################################################################
def get_all_directories(_path, _filefilter, _subName=False):
    files = get_all_files(_path, _filefilter, _subName)

    folders = set()
    for file in files:
        dirname = os.path.dirname(file)
        folders.add(dirname)

    return folders


##################################################################
# Listing all files that match with a condition (including directory)
# :param _path: the root folder to search files
# :param _match: condition for finding files
# :param _subName: if it is True, return the relative filepath from the _path
# :return: list of all file paths
##################################################################
def get_all_files(_path, _match, _subName=False, _only_files=True):

    files = [f for f in glob.glob(os.path.join(_path, "**",_match), recursive=True)]

    if _only_files is True:
        files = [item for item in files if os.path.isfile(item) is True]

    if _subName is True:
        sIdx = len(_path)
        files = [file[sIdx:] for file in files]
        files = [file[1:] if file.startswith("/") else file for file in files]
    return files


##################################################################
# Create directories through the path hierarchy if the directories are not exists
# :param _path:
# :return:
##################################################################
def prepare_directory(_path):
    if os.path.exists(_path) is False:
        try:
            os.makedirs(_path, exist_ok=True)
        except Exception as e:
            error.error_exit("failed to create output dir `%s`"% _path)
    return True


##################################################################
# replacement of the os.path.join()
# :param *args: list of paths, can be variable
# :return: the well-organized path
##################################################################
def makepath(*args):
    path = ""
    for arg in args:
        path = os.path.join(path, arg)

    # remove error path `./`
    dirs = path.split("/")
    for idx in range(len(dirs)-1, 0, -1): # idx 0 is not check
        if dirs[idx] == "":
            del dirs[idx]

    # remove redundant `./`
    for idx in range(len(dirs)-1, 0, -1): # idx 0 is not check
        if dirs[idx] == ".":
            del dirs[idx]

    # process `../`
    start_point = 0
    idx = 0
    while idx < len(dirs): #for idx in range(0, len(dirs)): # idx 0 is not check
        if not (start_point == 0 and dirs[idx] == ".."):
            start_point = idx
            if dirs[idx] == "..":
                del dirs[idx]
                del dirs[idx-1]
                idx -= 2
        idx += 1

    if dirs[0] == "." and dirs[1] == "..":
        del dirs[0]

    return '/'.join(dirs)


##################################################################
# find fullpath from specified dir
##################################################################
def find_fullpath_in_dir(_dir, _target_name, _match):
    '''
    Find full path of mutant in the given directory _dir
    This function is designed for the mutant has provided only the name
    :param _mutant_name: the file name of the mutant that we want to find
    :return: relative path of the mutant from the directory _dir
    '''
    mutant_path = None
    for f_path in get_all_files(_dir, _match=_match):
        filename = os.path.basename(f_path)
        if _target_name == filename:
            mutant_path = f_path
            break

    if mutant_path is None:
        return None

    return mutant_path[len(_dir)+1:]


def convert_CRLF_to_LF(_filename):
    '''
    remove a CR('\r') from a file, CR can cause an error in libclang (locating of elements)
    :param _filename:
    :return:
    '''

    f = open(_filename, "r")
    text = f.read()
    f.close()

    text_to_remove = '\r'
    text = text.replace(text_to_remove, "")

    f = open(_filename, "w")
    f.write(text)
    f.close()
    return True


def make_pure_relative_path(path):
    while True:
        if path.startswith("./"):
            path = path[2:]
            continue
        if path.startswith("../"):
            path = path[3:]
            continue
        idx = path.find("/./")
        if idx >=0:
            path = path[idx+3:]
        idx = path.find("/../")
        if idx >=0:
            path = path[idx+4:]
        break

    return path


##################################################################
# read a file
##################################################################
def readline_reverse(_file_name, _max=None):
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
                yield buffer.decode(errors='backslashreplace')[::-1]
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


##################################################################
# read a file
##################################################################
def make_executable(_file_name):
    st = os.stat(_file_name)
    os.chmod(_file_name, st.st_mode | stat.S_IEXEC)
    return True