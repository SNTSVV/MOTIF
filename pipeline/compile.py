#! /usr/bin/env python3

import os
import shutil
import re
import glob
if __package__ is None or __package__ == "":
    import utils
else:
    from pipeline import utils


def initialize_SUT(_repo, _bak_filter):
    '''
    Rollback all backup code into the original file
    It prevents the error caused by the previous execution.
    :return:
    '''
    files = utils.get_all_files(_repo, _bak_filter, _subName=False)

    count = 0
    for origin in files:
        mutant = origin[:-7]  # find the mutated code
        rollback_mutated_function(origin, mutant)
        count += 1

    if count>0:
        print("We found %d mutated files in the SUT, all they are rolled back: %s" % (count, files))
    return True


def inject_mutated_function( _code_file, _mutated_func_file, _func_name, _mut_prefix):
    '''
    inject mutated function into the _code_file
    if the mutated function is static, it can be an issue, so we remove static keyword
    :param _code_file:
    :param _mutated_function:
    :return:
    '''
    # # read original code and mutated code
    # mutated_code = open(_mutated_func_file, "r").read()
    #
    # # get the position of the end of the qualifiers (before the function name started)
    # # function parameters: r"[\w\s\*\[\]<>&]+" + r"(,[\w\s\*\[\]<>&]+)*"
    # rex = re.compile(r"\w+\s*\([\w\s\[\]*<>&]+(,[\w\s\[\]*<>&]+)*\)")
    # search_end = mutated_code.find("{")+1
    # q = rex.search(mutated_code, 0, search_end)
    # idx = q.span(0)[0]
    #
    # # check if the function is static
    # #  - It is acceptable because the mutated code has only the function code
    # static = True if mutated_code[:idx].rfind('static')>=0 else False
    # if static is True:
    #     print("Target function is static, we are trying to address this but there may be problems...")
    #     print('We just eliminate the `static` keyword from the functions')
    #     # eliminate "static" in mutated function declaration
    #     mutated_code = mutated_code[:idx].replace('static', '') + mutated_code[idx:]
    #
    #     ### TODO:: I need to update this code
    #     # eliminate "static" from the source file
    #     # declaration_line=$(grep -n " $info['func']" self.TARGET_CODE | grep "(" | grep "static" | cut -d : -f 1)
    #     # sed -i "$declaration_line s/static//" "self.TARGET_CODE"
    #     # code = code.replace('static', '')  ## this is error
    if _mutated_func_file is not None:
        with open(_mutated_func_file, "r") as f:
            mutated_code = f.read()
            mutated_code = remove_static_keyword(mutated_code, _mut_prefix+"_"+_func_name)

    with open(_code_file, "r") as f:
        code = f.read()
        code = remove_static_keyword(code, _func_name)

    # append mutated function to the source file
    with open(_code_file, "w") as f:
        f.write(code)
        if _mutated_func_file is not None:
            f.write('\n\n\n' + mutated_code)
    return True


def remove_static_keyword(_code, _function_name):
    regex  = r''                #
    # regex  = r'\s*'           # allow space
    regex += r'([\w\*]+\s+)*'   # classifier (allow multiple, include at least a space)
    regex += r'(static\s+)'     # static type
    regex += r'([\w\*\_\(\)]+\s+)+'   # return type or classifier (allow multiple, include at least a space)
    regex += r'(\w+)\s*'        # function name (allow space)
    regex += r'\('              # '('
    regex += r'[^)]*'           # args - total cop out
    regex += r'\)'              # ')'
    regex += r'\s*'             # allow space
    # regex += r'(\{|;)'          # prototype or definition
    pattern_func_prototype = re.compile(regex)
    # r'([\w\*]+\s+)*(static\s+)([\w\*\_\(\)]+\s+)+(\w+)\s*\([^)]*\)\s*'

    idx = 0
    while True:
        func = pattern_func_prototype.search(_code, idx)
        if func is None: break

        # set the next search point
        start, end = func.span(0)   # func.span(0) returns a tuple (start, end)
        idx = end + 1

        # check if it is the target function
        fname = func.groups()[-1]
        if fname != _function_name: continue

        # get the location of the function name
        fname_idx = len(func.groups())
        end = func.span(fname_idx)[0]     # the start point of function name will be the end range

        _code = _code[:start] + _code[start:end].replace("static", "") + _code[end:]
        idx -= 6        # reduce idx as many as the length of "static"
    return _code


def compile_SUT(_repo, _commands, _env=None):
    '''
    Generate SUT following the list of commands (COMPILE_SUT_CMDS)
    '''
    for command in _commands:
        ret_code = utils.shell.execute_and_check(command, "retcode", 0, _working_dir=_repo, _env=_env, _verbose=True)
        if ret_code is False:
            utils.error_exit("Failed to compile SUT using the command: %s"%command)
    return True


def compile_SUT_files(_compiler_path:str, _files:list, _build:str, _includes:list, _compile_flags:str, _repo_path:str):
    '''
    :param _compiler_path:  the file path of the compiler
    :param _files: list of source code paths to be compiled (preferred relative path from the repository)
    :param _build: output directory for the compilation result (preferred relative path from the repository)
    :param _includes: list of directories to be used as include paths (preferred relative path from the repository)
    :param _repo_path: repository path
    :return:
    '''
    # Set compiler
    compiler_path = _compiler_path
    if utils.is_global_command(compiler_path) is False:
        compiler_path = os.path.abspath(compiler_path)

    # generate compile parameters
    include_txt = get_gcc_params_include(_includes) # config.REPO_PATH

    # set compile output path
    #   - It should not be deleted because the output directory can be the same to the repository root
    compile_output = _build if _build is not None else "./"

    # select all the target files to compile
    #   - we exclude the files that starts with "!"
    target_files = [filename for filename in _files if filename.startswith("!") is False]
    excluded_files = [filename[1:] for filename in _files if filename.startswith("!") is True]
    target_files = get_target_files(target_files, _repo_path)
    excluded_files = get_target_files(excluded_files, _repo_path)
    target_files = list(set(target_files) - set(excluded_files))

    # Create objective files for each the source codes in the list (-c option is to compile objective files)
    # we assume the filepath is relative from the config.REPO_PATH
    cnt = 0
    for code_file in target_files:
        cnt += 1

        # set output path
        output_path = os.path.splitext(code_file)[0] + ".o"
        output_path = utils.makepath(compile_output, output_path)

        # prepare build output dir (by absolute path)
        os.makedirs(os.path.join(_repo_path, os.path.dirname(output_path)), exist_ok=True)

        # execute compile
        cmd = "%s -c -o %s %s %s %s"%(compiler_path, output_path, code_file, _compile_flags, include_txt)
        if utils.shell.execute_and_check(cmd, "retcode", 0, _working_dir=_repo_path, _verbose=True) is None:
            utils.error_exit("[%d/%d] Failed to compile %s" % (cnt, len(target_files), code_file))
        print("\t[%d/%d] compiled %s" % (cnt, len(target_files), code_file))

    return True


def compile_test_driver(_compiler_path:str, _driver_file:str, _output_file:str,
                        _objects:list, _includes:list, _linker_option:str, _repo_path:str):
    '''
    :param _compiler_path:  the file path of the compiler
    :param _driver_file: a source code of test driver (preferred absolute path)
    :param _output_file: a path of the compiled output (preferred absolute path)
    :param _objects: list of objective files to be included in the test driver (preferred relative path from the repository)
    :param _includes: list of directories to be used as include paths (preferred relative path from the repository)
    :param _linker_option: additional compile flags for linking and compiling the test driver
    :param _repo_path: repository path
    :return:
    '''
    # set compiler path
    compiler_path = _compiler_path
    if utils.is_global_command(compiler_path) is False:
        compiler_path = os.path.abspath(compiler_path)

    # generate compile parameters
    include_txt = get_gcc_params_include(_includes) # _includes are already relative path from REPO_PATH
    obj_files = get_target_files(_objects, _repo_path)  # _includes are already relative path from REPO_PATH
    if obj_files is None or len(obj_files) == 0:
        utils.error_exit("Failed to find listed object files: %s" % obj_files)
    obj_files_txt = " ".join(obj_files)

    # set compile options (default: reduce warning)
    compile_flags = "-Wno-implicit-function-declaration -Wno-format-security -Wno-int-conversion -Wno-unused-result -Wno-conversion-null"
    compile_flags += " " + _linker_option

    # execute
    cmd = "%s -o %s %s %s %s %s "%(compiler_path, _output_file, _driver_file, obj_files_txt, compile_flags, include_txt)
    # print (cmd)
    if utils.shell.execute_and_check(cmd, "retcode", 0, _working_dir=_repo_path, _verbose=True) is None:
        utils.error_exit("Failed to compile Entry point: %s" % _driver_file)
    pass


def rollback_mutated_function(_backup, _origin):
    shutil.copy(_backup, _origin)
    os.remove(_backup)


################################################
# related includes
################################################
def get_automatic_include_files(_repo_path):
    '''
    [deprecated] it is hard to apply all subjects
    :return:
    '''
    # generate list of folders that contains headers (generate automatically...?)
    includes = utils.get_all_directories(_repo_path, "*.h", _subName=True)

    # Remove test and build folders
    includes = [include for include in includes if include.startswith("tst") is False]
    includes = [include for include in includes if include.startswith("test") is False]
    includes = [include for include in includes if include.startswith("build") is False]
    # includes.append("include")

    # To include upper folders that only have folders containing headers
    new_includes = set()
    for include in includes:
        while include != "":
            new_includes.add(include)
            include = os.path.dirname(include)
    includes = list(new_includes)

    return includes


def get_gcc_params_include(_includes, _location=None):
    if _includes is None: return ""
    params = ""
    for include_name in _includes:
        inc_path = utils.makepath(_location, include_name) if _location is not None else include_name
        params += " -I" + inc_path
    return params


def get_gcc_params_files(_file_list, _location=None):
    if _file_list is None: return ""
    params = ""
    for filename in _file_list:
        file_path = utils.makepath(_location, filename) if _location is not None else filename
        params += " " + file_path
    return params


def get_target_files(_list, _location):
    '''
    make a list of files by solving predicate of file path such as (**, *)
    :param _list: list of file predicates
    :param _location: relative path root (all the result list will be relative path of this location)
    :return:
    '''
    file_list = []

    abs_location = os.path.abspath(_location)
    for filepath in _list:
        path_predicate = os.path.join(abs_location, filepath) if filepath.startswith("/") is False else filepath

        # get files using the predicate
        files = glob.glob(path_predicate, recursive=True)
        if len(files) == 0:
            continue

        # make relative path from _location
        files = [os.path.abspath(f) for f in files]
        files = [f[len(abs_location)+1:] for f in files]

        file_list += files

    # remove duplicate
    return list(set(file_list))
