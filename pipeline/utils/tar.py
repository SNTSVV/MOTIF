import os
import tarfile
import re
import time
from . import file

mem_tarfiles = {}


def exists_in_tar(_filename, _tarfile):
    # load all files in tar file
    if _tarfile not in mem_tarfiles:
        tar = tarfile.open(_tarfile)
        mem_tarfiles[_tarfile] = tar.getnames()

    # check the file exists in the tar file
    filepath = file.makepath('./', _filename)
    if filepath not in mem_tarfiles[_tarfile]:
        return False
    return True


def find_fullpath_in_tar(_filename, _tarfile):
    # load all files in tar file
    if _tarfile not in mem_tarfiles:
        tar = tarfile.open(_tarfile)
        mem_tarfiles[_tarfile] = tar.getnames()

    # check the file exists in the tar file
    # target = _filename.copy()
    target = os.path.basename(_filename)
    for filepath in mem_tarfiles[_tarfile]:
        if os.path.basename(filepath) != target: continue
        return filepath
    return None


def get_all_files_in_tar(_tar_file, _match="*", _only_basename=False):
    # get all file names in the tar file
    tar = tarfile.open(_tar_file)
    all_files = tar.getmembers()
    if _match is None: _match = "*"

    # change the match to regex
    _match = _match.replace(".", "\.")
    _match = _match.replace("*", ".*")

    # filter of the file
    ptn = re.compile(_match)
    target_files = []
    for afile in all_files:
        if afile.type == tarfile.DIRTYPE: continue
        filepath = afile.name
        fname = os.path.basename(filepath)
        if ptn.match(fname) is None: continue
        if _only_basename is False:
            target_files.append(filepath)
        else:
            target_files.append(fname)
    return target_files


def extract_file_from_tar(_filename, _tar_file, _output):
    ret = True
    TRY_MAX = 3
    try_cnt = 0

    while try_cnt < TRY_MAX:
        try_cnt += 1

        tar_obj = tarfile.open(_tar_file)
        try:
            tar_obj.extract(_filename, _output)
            break
        except OSError as e:
            print(e)
            print("retry to extract file after 1 sec...")
            time.sleep(1)
            continue
        except:
            ret = False
            break
        finally:
            tar_obj.close()

    return ret

