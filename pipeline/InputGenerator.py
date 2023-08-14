import os
import sys
import re
import struct
if __package__ is None or __package__ == "":
    from Prototype import Prototype
else:
    from pipeline.Prototype import Prototype


class InputGenerator():
    PARAMETER_FORMAT = [     # optional
    ]

    INPUT_VALUES_MAP = {
        "default":  {"N": -1, "Z": 0, "P": 1},
        "_Bool":    {"N": False, "Z": True, "P": True},
        "float":    {"N": 3230283776.0, "Z": 0.0, "P": 1072693248.0},
        "double":   {"N": 13826050856027422720.0, "Z": 0.0, "P": 4602891378046628864.0},
        "char":     {"N": b'\xFF', "Z": b'\x00', "P": b'\x41'},
    }

    # Binary convert table (the 'default' value should be matched to the default type of INPUT_VALUES_MAP
    # https://docs.python.org/3/library/struct.html#format-characters
    convert_table = {
        'default'           : {'format':'i', 'python':int,      'size':4},  # set default as int
        'char'              : {'format':'c', 'python':str,      'size':1},
        'signed char'       : {'format':'b', 'python':int,      'size':1},
        'unsigned char'     : {'format':'B', 'python':int,      'size':1},
        '_Bool'             : {'format':'?', 'python':bool,     'size':1},
        'short'             : {'format':'h', 'python':int,      'size':2},
        'unsigned short'    : {'format':'H', 'python':int,      'size':2},
        'int'               : {'format':'i', 'python':int,      'size':4},
        'unsigned int'      : {'format':'I', 'python':int,      'size':4},
        'long'              : {'format':'l', 'python':int,      'size':4},
        'unsigned long'     : {'format':'L', 'python':int,      'size':4},
        'long long'         : {'format':'q', 'python':int,      'size':8},
        'unsigned long long': {'format':'Q', 'python':int,      'size':8},
        'float'             : {'format':'f', 'python':float,    'size':4},
        'double'            : {'format':'d', 'python':float,    'size':8},
    }

    def __init__(self, _template_config=None):
        self.INPUT_VALUES_MAP.update(_template_config['INPUT_VALUES_MAP'])

        # user-defined formats
        for item in _template_config['PARAMETER_FORMAT']:
            if 'format' not in item or item['format'] is None: continue
            self.PARAMETER_FORMAT.append(item)
        pass

    def generate(self, _prototype:Prototype, _output_path):
        params_info = _prototype.get_param_info_list()     # get list of params
        input_types = self.__get_input_types()  # negative, zero, positive

        # generate input files as many as the input_types
        for input_type in input_types:
            # get proper values for each param_type according to the input_type
            values = []
            for param in params_info:
                value = self.get_binary_value(_prototype.name, param, input_type)
                if value is None:
                    raise Exception("Not acceptable data type of {}: {}".format(_prototype.name, param ))
                values.append(value)

            # generate file
            filename = os.path.join(_output_path, "%s.%s"%(_prototype.name, input_type))
            self.__generate_binary_file(values, filename)
        return True

    def __get_input_types(self):
        return ["negative", "zero", "positive"]

    def __generate_binary_file(self, _values:list, _filename:str):
        with open(_filename, 'wb') as f:
            for value in  _values:
                f.write(bytearray(value))  # convert to bytearray before writing
        return True

    ############################################################
    # generate values for the type statement
    ############################################################
    def get_binary_value(self, _func_name:str, _param:dict, _input_type:str):
        # convert parameter information into each variable
        # def_type, can_type, size, array_size, driver_kind, fields  = _param
        param_name  = _param['name']
        def_type    = _param['def_type']
        can_type    = _param['can_type']
        size        = _param['size']
        array_size  = _param['array_size']
        driver_kind = _param['driver_kind']
        user_struct = _param['struct']

        # get human-readable input value according to the parameter type and input type (N, Z, P)
        # it also can be provided as binary value
        # if the parameter is string and user-defined format values are provided, input_value is replaced
        special_format = self.__get_user_defined_format(_func_name, param_name, def_type)
        if special_format is not None:
            input_value = self.__select_input_sample(special_format, _input_type)
        else:
            input_value = self.__select_input_sample(can_type, _input_type)

        # should be filtered before entering this function
        # - ['void', 'vo', 'address', 'address', 0, 1, 'VOID_POINTER', 'ISO8601']

        # set binary values to be the same size to the array_size
        if driver_kind.find("ARRAY") >= 0: # multiply a unit as much as the array_size
            if can_type.find('char') >= 0:
                byte_value = self.__to_bytes(can_type, input_value)
                # byte_value = self.__adjust_bytes_size(byte_value, size) if byte_value is not None else None
                byte_value = self.__padding_bytes(byte_value, size) if byte_value is not None else None
            else:
                item_size = int(size/array_size)
                byte_value = self.__to_bytes(can_type, input_value)
                byte_value = self.__adjust_bytes_size(byte_value, item_size) if byte_value is not None else None
                byte_value = byte_value * array_size if byte_value is not None else None
        elif user_struct is not None:
            ## TODO:: It is not matching to the config file
            byte_value = b''
            byte_value = self.__to_bytes(can_type, input_value)
            byte_value = self.__adjust_bytes_size(byte_value, size) if byte_value is not None else None
            for field in user_struct['fields']:
                if 'user_defined' not in field: continue
                field_value = self.__to_bytes(field['type'], input_value)
                field_value = self.__adjust_bytes_size(field_value, field['size']) if field_value is not None else None
                byte_value += field_value
        else:
            # unit format is determined, just convert value to bytes
            # if the parameter size is larger than the input value from the value_map,
            # we fill up repetitively
            byte_value = self.__to_bytes(can_type, input_value)
            byte_value = self.__adjust_bytes_size(byte_value, size) if byte_value is not None else None

        return byte_value

    def __adjust_bytes_size(self, _data:bytes, _size:int):
        if len(_data) < _size:   # for the structure
            cur_size = len(_data)
            multiply = int(_size/cur_size)+1     # get multiply
            _data = _data * multiply  # extend byte_value
        return _data[:_size]

    def __padding_bytes(self, _data:bytes, _size:int):
        if len(_data) < _size:
            cur_size = len(_data)
            padding = _size-cur_size
            padding = b'\0' * padding
            _data = _data + padding
        return _data[:_size]

    def __select_input_sample(self, _input_format:str, _input_type:str):
        '''

        :param _param_type: canonical type and user-defined format is available (only for string)
        :param _input_type:
        :return:
        '''
        keys = list(self.INPUT_VALUES_MAP.keys())
        keys.remove('default')

        # select a value_map for the current parameter _type
        selected_key = 'default'
        for key in keys:
            if _input_format.find(key) < 0: continue
            selected_key = key
        value_map = self.INPUT_VALUES_MAP[selected_key]

        # select a proper input value
        selected_value = value_map[_input_type[:1].upper()]
        return selected_value

    def __get_user_defined_format(self, _func_name:str=None, _param_name:str=None, _type:str=None, _filename:str=None):
        user_format = None   # default
        if self.PARAMETER_FORMAT is None or len(self.PARAMETER_FORMAT) == 0:
            return user_format  # return None

        # check char_format based on function name and parameter name
        for item in self.PARAMETER_FORMAT:
            # if 'type' in item: continue
            if 'format' not in item: continue
            if not (item['function'] == _func_name and item['parameter'] == _param_name): continue
            if 'file' in item and item['file'] is not None:
                if _filename is None or item['file'] != _filename: continue
            return item['format']

        # if not found the proper format, return None
        return user_format

    ########################################
    # convert python type to bytes (apply `endian` according to the system type)
    #    -- Note that if the input is provided as bytes, this function does not do anything
    #    -- so, you need to carefully set bytes
    ########################################
    def __to_bytes(self, _type:str, _value):
        '''
        This function returns the _value by converting bytes according to its data type
        if this function cannot find the proper type in the convert_table,
        it converts the _value into the largest size bytes (double)
        :param _type: canonical type is acceptable (in case of structure, it will just assume that int value)
        :param _value:
        :return:
        '''
        if isinstance(_value, bytes): return _value
        # set byte order
        byte_order = '<' if sys.byteorder == 'little' else '>'

        # convert _type if it contains array characters
        if re.match(r'[\w\s]+(\[\w*\])+', _type) is not None:
            print("requested type: %s" % _type)
            _type = re.sub(r'(\[\w*\])+', '', _type).strip()
            print("revised type: %s" % _type)

        # set converting format character
        if not _type in self.convert_table:
            converted_value = struct.pack(byte_order+self.convert_table['default']['format'], _value)
            return converted_value

        convert_info = self.convert_table[_type]
        converted_value = None

        # unsigned value error treats
        if _type.find("unsigned") >= 0 and _value < 0:
            # convert value to unsigned
            _value  = _value+(1 << (8 * convert_info['size'])) ## 1<< 32

        # convert _value into C format
        if isinstance(_value, convert_info['python']):
            if convert_info['format'] == 'c':
                converted_value = _value.encode()
                converted_value += b'\x00'
            else:
                converted_value = struct.pack(byte_order+convert_info['format'], _value)
            # print("to_bytes: --fmt:{}, input:{}, output:{}".format(byte_order+convert_info['format'], _value, converted_value))
        return converted_value

