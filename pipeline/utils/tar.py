import os
import tarfile
import re
import time
import shutil
from . import file, shell, error

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


def uncompress_tar_in_dir(_src_file, _dest_dir, _overwrite=False):
    '''
    :param _src_file: tar file to extract
    :param _dest_dir: root directory the _src_file to be extracted
    :param overwrite: if True, _dest_dir will be removed when it exists
    :return: False when the _src_file does not exist, the other errors will raise exception
    '''
    if os.path.exists(_dest_dir) is True:
        if _overwrite is True:
            shutil.rmtree(_dest_dir, ignore_errors=True)
        else:
            print("\tThe output directory exists.")
            return True

    # check if the tar file exists
    if os.path.exists(_src_file) is False:
        return False

    # extract tar
    file.prepare_directory(_dest_dir)
    cmd = "tar xf %s --directory %s" % (_src_file, _dest_dir)
    if shell.execute_and_check(cmd, "retcode", 0) is None:
        error.error_exit("Cannot extract the result file. Please check the tar file: %s"%_src_file)
    return True


def compress_directory(_src_dir, _dest_dir=None, _remove=False):
    '''
    :param _src_dir: target directory to be compressed (as tar)
    :param _dest_dir: output directory of the compressed file, <_src_dir>.tar will be created when it is None
    :param _remove: boolean whether remove _src_dir or not
    :return: the path of the tar file, raise exceptions with other errors
    '''
    ext = '.tar'
    tarfilename = os.path.basename(_src_dir) + ext
    cmd = "tar cf ../%s ." % (tarfilename)
    if shell.execute_and_check(cmd, "retcode", 0, _working_dir=_src_dir) is None:
        print("executed command: %s"%cmd)
        error.error_exit("Failed to compress the results: %s" % cmd)

    result_path = _src_dir + ext
    if _dest_dir is not None:
        file.prepare_directory(_dest_dir)
        final_path = os.path.join(_dest_dir, tarfilename)
        if final_path != result_path:
            shutil.move(result_path, final_path)
            result_path = final_path

    if _remove is True:
        shutil.rmtree(_src_dir)
    return result_path
