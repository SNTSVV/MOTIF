import os
import re
import sys


def expandDirs(_dirList, _findKey='', _ptn=None, _sort=False,_exceptionPtn=None):
    rex = None
    if _ptn is not None:
        rex = re.compile(_ptn)
    rexEx = None
    if _exceptionPtn is not None:
        rexEx = re.compile(_exceptionPtn)

    ret = []
    for dirItem in _dirList:
        data = []
        flist = os.listdir(dirItem['path'])
        for fname in flist:
            fullpath = os.path.join(dirItem['path'], fname)
            if os.path.isfile(fullpath): continue          # pass not a directory
            if fname.startswith(".") is True: continue  # pass hidden dir
            if rexEx is not None and rexEx.search(fname) != None: continue  # if the name is an exception

            if rex is not None:
                result = rex.search(fname)
                if result == None:
                    # print("\tPattern ('%s') doesn't matach: %s"%(_ptn, fullpath))
                    continue
                fname = result.group(0)
            newItem = dirItem.copy()
            newItem[_findKey] = fname
            newItem['path'] = fullpath
            data.append(newItem)
        if _sort is True:
            def selectKey(_item):
                return _item[_findKey]
            data.sort(key=selectKey)
        ret += data
    return ret


def getFiles(_dirList, _findKey='', _ptn=None, _sort=False):
    rex = None
    if _ptn is not None:
        rex = re.compile(_ptn)

    data = []

    for item in _dirList:
        flist = os.listdir(item['path'])
        for fname in flist:
            fullpath = os.path.join(item['path'], fname)

            if not os.path.isfile(fullpath): continue          # pass not a file
            if fname.startswith(".") is True: continue         # pass hidden file

            if rex is not None:
                result = rex.search(fname)
                if result is None:
                    continue
                matchedList = result.groups()
                newItem = {'path':fullpath, "ID":matchedList[0]}
                if newItem["ID"].isnumeric() is True: newItem["ID"] = int(newItem["ID"])
                for x in range(1, len(matchedList)):
                    newItem[x] = matchedList[x]
                data.append(newItem)
            else:
                data.append({'path':fullpath, "ID":None})

    if _sort is True:
        def selectKey(_item):
            return _item['ID']
        data.sort(key=selectKey)

    return data


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


def parse_args_with_remove(_args_info):
    # set default values
    args = dict(zip([item['name'] for item in _args_info], [item['default'] for item in _args_info]))

    # parameter parsing
    idx = 0
    while idx < len(sys.argv):
        for item in _args_info:
            if sys.argv[idx] != item['key']: continue
            # set parameter value
            if item['type'] == "bool":
                args[item['name']] = not args[item['name']]
            else:
                args[item['name']] = sys.argv[idx+1]
                del sys.argv[idx+1]

            # remove the value
            del sys.argv[idx]
            idx -= 1
        idx += 1   # move to the next argument
    return args
