#! /usr/bin/env python3
from clang .cindex import Index, CursorKind, TypeKind, Cursor, Type
import copy


#################################################
# This class analyzes function prototype from the given the function declaration cursor of clang
#        and provides information for generating test drivers and input values
#   * analysis function prototype and generate the following information ( provided by get_driver_dict() ):
#       - name: name of the function (only function name)
#       - params: list of dictionaries for the parameters of the function (see the next "*" item)
#       - prototype: string prototype of the given function (without return type)
#       - returns: a dictionary that describes the return data type of the function
#   * fields of a dictionary for a parameter or a return data type
#       - "name": parameter name (only for parameters)
#       - "type": data type (from code)
#       - "pure_type": data type without qualifier
#       - "can_type": canonical data type of the type
#       - "size": size of the parameter
#       - "qualifier": qualifier (const, volatile, restrict)
#       - "kind": TypeKind from clang (canonical type)
#       - "ptr_type": data type of pointee (if the "can_type" is "int *", pointee is "int")
#       - "can_ptr_type": canonical data type of pointee
#       - "ptr_size": size of pointee
#       - "ptr_kind": TypeKind of pointee from clang (canonical type)
#       - "driver_kind": kind for test driver (ARRAY, CONSTANT_ARRAY, POINTER, PRIMITIVE, ...)
#       - "array_size": size of array if the driver_kind is "ARRAY", otherwise 1
#       - "typedef": True if the parameter data type is defined as typedef, otherwise False
#################################################
class Prototype():
    '''
    In the Creator, this class finds information of the given function using AST.
    Check the following functions carefully.
    - get_driver_dict():      returns a dict for TemplateGenerator
    - get_param_info_list():  returns a list of dicts for InputGenerator
    - __get_function_info():    generates all information of the fields of this class (called in __init__())
    - __get_driver_type_info(): generates information of the type for test driver (called in __get_function_info())
    '''
    name = None         # function name
    params = None       # a list of parameters: a list of dicts (see above explain)
    prototype = None    # function prototype string without return type
    returns = None      # return type: a dict (see above explain)

    ## processing reference
    __AST = None

    # static variable for array size
    DEFAULT_ARRAY_SIZE = 100 # No option provided for array size, This will be default value

    # This field is used for assigning array size to the specified parameters below
    # Please specify parameters as a list of dictionary (see the example dictionary below)
    # You can also specify the items from the config file.
    PARAMETER_FORMAT = [
        # {"type": "FixedLengthString", "size": 100},
        # {"file": None, "function": "gs_clock_from_string", "parameter": "str", "size": 21},
    ]

    # This field is used for dealing with a structure data type that contains pointers.
    # We define an array and assign it to the field (pointer) in the structure. (the array will be filled with random values)
    # Please specify parameters and a list of fields that you want to assign array (see the example dictionary below)
    # You can also specify the items from the config file.
    STRUCT_FIELD_BUFFER = {
        # "<name of struct>": [ {"name": "<name of field>", "type": "<data type of the field>", "size": <size of the array>}, ...],
        # 'BitStream': [{"name": "buf", "type": "byte", "size": 20000}, ],
    }

    def __init__(self, _func_decl:Cursor, _template_config:dict, _AST:object=None):
        # update DEFAULT_ARRAY_SIZE from template configuration
        self.DEFAULT_ARRAY_SIZE = _template_config["DEFAULT_ARRAY_SIZE"]

        # update PARAMETER_FORMAT from template configuration
        for item in _template_config['PARAMETER_FORMAT']:
            if 'size' not in item or item['size'] is None: continue
            self.PARAMETER_FORMAT.append(item)

        # update STRUCT_FIELD_BUFFER from template configuration
        self.STRUCT_FIELD_BUFFER.update(_template_config['STRUCT_FIELD_BUFFER'])
        if _AST is not None:
            self.__AST = _AST

        if _func_decl is not None:
            info = self.__get_function_info(_func_decl)
            self.update(info, _func_decl)
        pass

    def update(self, _info:dict, _func_decl=None):
        self.name = _info['name']
        self.returns = _info['returns']
        self.params = _info['params']
        self.prototype = self.__get_function_prototype(self.name, self.params)
        if _func_decl is not None:
            self.prototype = self.__get_function_prototype_from_decl(_func_decl)
        print(self.prototype)
        pass

    #################################################
    # Functions for communicating with other classes
    #################################################
    def get_driver_dict(self):
        '''
        This function generate a dictionary of the function information
        that is used in the jinja engine for generating code file using template
        It selects necessary data for generating test drivers from the analyzed values in this class
        :return:
        '''
        print(self.name)
        params = []
        for param in self.params:
            info = {}
            info['name']        = param['name']
            info['def_type']    = self.__driver_param_def_type(param)       # data type of param (to be defined as a variable)
            info['call_method'] = self.__driver_param_call_method(param) # referring method when the param is used for calling the function
            info['copy_method'] = self.__driver_param_copy_method(param) # referring method when a function copies data to the param
            info['size']        = self.__driver_param_input_size(param)         # the total size of the param
            info['array_size']  = self.__driver_param_array_size(param)   # the number of element of the param (if it is array)
            info['struct']      = self.__driver_param_struct_fields(info['def_type'], param) # user-defined fields information for a structure
            # if a structure is treated by user, this function return nothing.
            if info['struct'] is None:
                info['print_format']= self.__get_printf_format(param)
            else:
                info['print_format']= None
            params.append(info)
            print("\t - %s" % str(info))

        # TODO:: We cannot control POINTER type as we cannot decide the size of return value
        # TODO:: therefore excepted them.
        # Note that if the return type is  "char *" then, we consider it as string
        driver_note = self.__driver_return_driver_note(self.returns)
        if driver_note == "string":
            printf_format = "%s"
        else:
            printf_format = self.__get_printf_format(self.returns)
        returns = {"type": self.returns['pure_type'], "driver_note": driver_note, "print_format": printf_format}
        print("\t - return: %s" % str(returns))
        return {'name':self.name, "returns":returns, 'params': params, 'prototype':self.prototype}

    def get_param_info_list(self):
        # select necessary data for generating input values
        print(self.name)
        params = []
        for param in self.params:
            info = {}
            info['name']        = param['name']
            info['def_type']    = self.__driver_param_def_type(param)
            info['can_type']    = self.__driver_param_can_type(param)
            info['size']        = self.__driver_param_input_size(param)
            info['array_size']  = self.__driver_param_array_size(param)
            info['driver_kind'] = param['driver_kind']
            info['struct']      = self.__driver_param_struct_fields(info['def_type'], param) # user-defined field information for a structure
            params.append(info)
            print("\t - %s" % str(info))
        return params

    def __driver_param_def_type(self, param:dict):
        if param['driver_kind'] == "ARRAY":             return param['ptr_type']
        elif param['driver_kind'] == "CONSTANT_ARRAY":
            if param['typedef'] is True:                return param['pure_type']
            else:                                       return param['ptr_type']
        elif param['driver_kind'].find("POINTER") >= 0: return param['ptr_type']
        else:                                           return param['pure_type']

    def __driver_param_array_size(self, param:dict):
        if param['driver_kind'] == "ARRAY":             return param['array_size'] # %s %s[%d]" % (param['ptr_type'] param['name'],param['array_size'])
        elif param['driver_kind'] == "CONSTANT_ARRAY":
            if param['typedef'] is True:                return 1    # %s %s" % (param['pure_type'] param['name'])
            else:                                       return param['array_size']    # %s %s[%d]" % (param['ptr_type'] param['name'],param['array_size'])
        elif param['driver_kind'].find("POINTER") >= 0: return 1   # %s %s" % (param['ptr_type'] param['name'])
        else:                                           return 1   # %s %s" % (param['pure_type'] param['name'])

    def __driver_param_copy_method(self, param:dict):
        if param['driver_kind'].find("ARRAY") >= 0: # parameter is pointer, but the definition is also pointer
            if param['ptr_type'].find("char") >= 0:
                return "string"        # param['name']
            else:
                return "value"        # param['name']
        elif param['driver_kind'].find("POINTER") >= 0: # parameter is pointer, but the definition is primitive (include pointer type (e.g., char **))
            return "address"    # &param['name']
        else:                                           # parameter and definition is primitive
            return "address"    # &param['name']

    def __driver_param_call_method(self, param:dict):
        if param['driver_kind'].find("ARRAY") >= 0:
            return "value"      # param['name']
        elif param['driver_kind'].find("POINTER") >= 0:
            return "address"    # &param['name']
        else:
            return "value"      # param['name']

    def __driver_param_input_size(self, param:dict):
        if param['driver_kind'].find("ARRAY") >= 0:
            size = param['array_size'] * param['ptr_size']
        elif param['driver_kind'].find("POINTER") >= 0:
            size = param['ptr_size']
        else:
            size = param['size']
        return size

    def __driver_param_can_type(self, param:dict):
        if param['driver_kind'] == "ARRAY":             return param['can_ptr_type']
        elif param['driver_kind'] == "CONSTANT_ARRAY":  return param['can_ptr_type']
        elif param['driver_kind'].find("POINTER") >= 0: return param['can_ptr_type']
        else:                                           return param['can_type']

    def __driver_param_struct_fields(self, _def_type:str, _param:dict):
        # if there is a guide for a struct in the STRUCT_FIELD_BUFFER,
        # we provide more information for the struct
        # otherwise, we will ignore the struct
        if _def_type not in self.STRUCT_FIELD_BUFFER: return None
        if "exception" in self.STRUCT_FIELD_BUFFER[_def_type]:
            if self.name in self.STRUCT_FIELD_BUFFER[_def_type]["exception"]: return None

        struct_info = copy.deepcopy(self.STRUCT_FIELD_BUFFER[_def_type]) # bring information from the config
        # user_fields = self.STRUCT_FIELD_BUFFER[_def_type]['user_fields']

        # get field data from the code  (print_format should follow the info)
        struct_info['fields'] = copy.deepcopy(_param['struct'])  # bring information from the code
        for field in struct_info['fields']:                      # add print_format information for each field
            field['print_format'] = self.__get_printf_format_field(field)

        # update field data from config (mixing)
        # print("\t\t * Struct %s [%s]:"%(_param['name'], _def_type))
        for field in struct_info['fields']:
            target = [item for item in struct_info['user_fields'] if item['name'] == field['name']]
            if len(target) > 0:
                field.update(target[0])   # update 'type', 'size', 'string'
                field['user_defined'] = True
            # print("\t\t\t + %s"%field)

        # clean not used fields
        del struct_info['user_fields']
        return struct_info

    def __driver_return_driver_note(self, _type:dict):
        note = ""
        if _type['kind'] == TypeKind.POINTER:
            note = "pointer"
            if _type['can_ptr_type'].find("char") >= 0:
                note = "string"
        return note

    ############################################################
    # get format information for printf (they are called from self.get_driver_dict functions)
    ############################################################
    type_list = {
        # Special types
        "default": "%X",  # show binary
        "string": "%s",   # char *
        "struct": "%X",
        "pointer": "%p",
        "void": "%p",
        "enum": "%d",
        "byte:": "%d",

        # Primitive types
        "_Bool": "%d",

        "char": "%d",
        "unsigned char": "%d",
        "signed char": "%d",

        "int": "%d",
        "signed": "%d",
        "signed int": "%d",
        "unsigned": "%u",
        "unsigned int": "%u",

        "short": "%hi",
        "signed short": "%hi",
        "unsigned short": "%hu",
        "short int": "%hi",
        "signed short int": "%hi",
        "unsigned short int": "%hu",

        "long": "%ld",
        "signed long": "%ld",
        "unsigned long": "%lu",
        "long int": "%ld",
        "signed long int": "%ld",
        "unsigned long int": "%lu",

        "long long": "%lld",
        "signed long long": "%lld",
        "unsigned long long": "%llu",
        "long long int": "%lld",
        "signed long long int": "%lld",
        "unsigned long long int": "%llu",

        "float": "%g",
        "double": "%G",
        "long double": "%LG"
    }

    def __get_printf_format(self, _param):
        # processing for the struct type
        if _param['driver_kind'].startswith("STRUCT") is True:
            arg_type = "struct"

        elif _param['can_type'].find("**") >=0:
            arg_type = "pointer"

        # processing for arrays
        elif _param['driver_kind'].find("ARRAY") >= 0: # parameter is pointer, but the definition is also pointer
            if _param['can_ptr_type'].find("char") >= 0:
                arg_type = "string"
            else:
                arg_type = _param['can_ptr_type']

        # Selecting type of pointee or original
        elif _param['driver_kind'].endswith("POINTER") is False:
            arg_type = _param['can_type']
        else:
            arg_type = _param['can_ptr_type']

        # processing enum
        if arg_type.startswith("enum "): arg_type = "enum"

        # selecting print format
        if arg_type in self.type_list:
            return self.type_list[arg_type]
        return self.type_list['default']

    def __get_printf_format_field(self, _field):
        # pointer should be %p  (defined in the self.type_list)
        # struct should be %X  (We just print hex for the sub-struct included in a struct)
        arg_type = _field['type']
        if _field['pointer'] is True:
            arg_type = 'pointer'

        # Get info from the self.type_list
        if arg_type in self.type_list: return self.type_list[arg_type]
        return None

    ############################################################
    # Analysis Function information
    ############################################################
    def __get_function_info(self, _func_decl:Cursor):
        func = {}
        func['name'] = self.__get_function_name(_func_decl)
        func['returns'] = self.__get_driver_type_info(_func_decl.result_type, func['name'])

        # get parameter information
        func['params'] = []
        for node in _func_decl.get_arguments():
            param = {"name":node.spelling, "format":""}
            param.update(self.__get_driver_type_info(node.type, func['name'], node.spelling))
            func['params'].append( param )

        return func

    def __get_base_function_info(self, _func_decl:Cursor):
        info = {}
        info['name'] = self.__get_function_name(_func_decl)
        info['returns'] = self.__get_type_info(_func_decl.result_type)

        # get parameter information
        info['params'] = []
        for node in _func_decl.get_arguments():
            param = {"name":node.spelling, "format":""}
            param.update(self.__get_type_info(node.type))
            info['params'].append( param )
        return info

    def __get_function_name(self, _func_decl:Cursor):
        return _func_decl.spelling

    def __get_function_prototype(self, _func_name:str, _params:list):
        params_txt = []
        for param in _params:
            param_str = param['type'] + ' ' + param['name']
            # if arg['qualifier'] != "": arg_str = arg['qualifier'] + ' ' + arg_str
            params_txt.append(param_str)
        return "%s(%s)"%(_func_name, ', '.join(params_txt))

    def __get_function_prototype_from_decl(self, _func_decl:Cursor):
        func_name = self.__get_function_name(_func_decl)
        params_origin = []
        for node in _func_decl.get_arguments():
            param_str = node.type.spelling + ' ' + node.spelling
            params_origin.append(param_str)

        return "%s(%s)" % (func_name, ', '.join(params_origin))


    ############################################################
    # Analysis Data type of parameters (support the functions analyzing function information, see above)
    ############################################################
    def __get_type_info(self, _type:Type):
        '''
        Extract basic information of data type
        It includes user-defined type, canonical type, pointee, canonical type of pointee
        :param _type:
        :return:
        '''
        info = {}
        # basic information
        info["type"] = _type.spelling
        info["size"] = _type.get_size()
        info["qualifier"] = self.__get_qualifier(info["type"])
        info["pure_type"] = self.__strip_type_qualifier(info["type"])
        info["kind"] = _type.kind

        # get pointer related information
        ptr_type = _type.get_pointee()
        info["ptr_type"] = ptr_type.spelling
        info["ptr_size"] = ptr_type.get_size()
        info["ptr_qualifier"] = self.__get_qualifier(info["ptr_type"])
        info["ptr_pure_type"] = self.__strip_type_qualifier(info["ptr_type"])
        info["ptr_kind"] = ptr_type.kind

        # we use canonical name to analysis type name because it uses only standard type name (native type name)
        # get canonical_type
        #   - Canonical type helps to figure out the primitive type of the data type (escape typedef)
        canonical = _type.get_canonical()
        info["can_type"] = canonical.spelling
        info["can_size"] = canonical.get_size()
        info["can_qualifier"] = self.__get_qualifier(info["can_type"])
        info["can_pure_type"] = self.__strip_type_qualifier(info["can_type"])
        info["can_kind"] = canonical.kind

        # get pointer related information
        can_ptr_type = canonical.get_pointee()
        info["can_ptr_type"] = can_ptr_type.spelling
        info["can_ptr_size"] = can_ptr_type.get_size()
        info["can_ptr_qualifier"] = self.__get_qualifier(info["can_ptr_type"])
        info["can_ptr_pure_type"] = self.__strip_type_qualifier(info["can_ptr_type"])
        info["can_ptr_kind"] = can_ptr_type.kind

        # if canonical.kind == TypeKind.RECORD:
        #     info['struct'] = self.__get_structure_fields(canonical)
        # if canonical.kind == TypeKind.POINTER and can_ptr_type.kind == TypeKind.RECORD:
        #     info['struct'] = self.__get_structure_fields(can_ptr_type)
        return info

    # important function of this class
    def __get_driver_type_info(self, _type:Type, _func_name:str=None, _param_name:str=None):
        '''
        This function returns information extracted from basic type information (get_type_info)
        by removing unnecessary values for generating test drivers
        and augmenting additional information that would be helpful to generate test drivers.
        :param _type:
        :param _func_name:
        :param _param_name:
        :return:
        '''
        param = {}
        base = self.__get_type_info(_type)

        # select information that need to generate test driver
        param['type'] = base['type']              # original spelling of the type
        param['pure_type'] = base['pure_type']    # type name without qualifiers (will be USED to define variable)
        param['can_type'] = base['can_pure_type'] # canonical type name (e.g., typedef int _myInt; --> int)
        param['size'] = base['size']              # total size of this variable in bytes
        param['kind'] = base['can_kind']          # AST kind of the type (it shows the primitive type)
        param['qualifier'] = base['qualifier']    # the name of qualifier
        # adjustment for typedef of void: e.g., typedef void ABC, if ABC used as return type, it would be an issue
        if base['can_kind'] == TypeKind.VOID:
            param['pure_type'] = base['can_type']

            # select pointee information that need to generate test driver
        param['ptr_type'] = base['ptr_pure_type'] if base['ptr_pure_type'] != "" else None # type name of pointee
        param['can_ptr_type'] = base['can_ptr_pure_type'] # canonical type name of pointee
        param['ptr_size'] = base['ptr_size'] if base['ptr_size'] >= 0 else 0  # total size of pointee in bytes
        param['ptr_kind'] = base['can_ptr_kind']          # AST kind of the type, we use canonical one (it shows the primitive type)
        # adjustment for typedef of pointer: e.g., typedef int * ABC, the ptr_type of ABC is None, but it actually has ptr_type
        if param['can_ptr_type'] != '' and param['ptr_type'] is None:
            param['ptr_type'] = param['can_ptr_type']
            param['ptr_size'] = base['can_ptr_size'] if base['can_ptr_size'] >= 0 else 0

            # typedef information
        param['typedef'] = True if base['kind'] == TypeKind.TYPEDEF else False

        # Update data for generating test driver
        # data size of void type
        if param['kind'] == TypeKind.VOID: param['size'] = 0
        if param['ptr_kind'] == TypeKind.VOID: param['ptr_size'] = 0

        # augmenting information for test driver ()
        #    - TypeKind.RECORD is a structure data type
        #    - constant arrays and incomplete arrays are dealt in another section below
        param['driver_kind'] = "PRIMITIVE"
        if param['kind'] == TypeKind.POINTER:
            if param['ptr_kind'] == TypeKind.VOID:       param['driver_kind'] = "VOID_POINTER"
            elif param['ptr_kind'] == TypeKind.RECORD:   param['driver_kind'] = "STRUCT_POINTER"
            else:                                        param['driver_kind'] = "POINTER"
        elif param['kind'] == TypeKind.RECORD:           param['driver_kind'] = "STRUCT"
        elif param['kind'] == TypeKind:                  param['driver_kind'] = "VOID"

        if param['driver_kind'] == "VOID_POINTER":
            param = self.__get_void_ptr_type(_func_name, _param_name, param)
            if param['driver_kind'] == "VOID_POINTER":
                print("Error: Not defined data type for void pointer")
                exit(1)

        # estimating the size of array, set 1 if the type is not ARRAY
        #  -TODO:: This cannot be estimated automatically, we take user-defined array size.
        #  -TODO:: Please take a look at the config.py (TEMPLATE_CONFIG['PARAMETER_FORMAT'])
        param["array_size"] = 1
        # if param['ptr_type'].find('char')>=0:        param['driver_kind'] = "ARRAY"
        if param['driver_kind'] == "POINTER":
            param["array_size"] = self.__get_array_size(_func_name, _param_name)
            if param["array_size"] != 1: param['driver_kind'] = "ARRAY"

        # if param['driver_kind'] == "ARRAY":
        #     param["array_size"] = self.__get_array_size(_func_name, _param_name)

        # dealing with incomplete arrays (update pointee type and type infos)
        if param['kind'] == TypeKind.INCOMPLETEARRAY:
            newtype = _type.get_array_element_type()
            param['ptr_type'] = newtype.spelling
            param['ptr_size'] = newtype.get_size()
            param['ptr_kind'] = newtype.kind
            param['driver_kind'] = "ARRAY"
            param["array_size"] = self.__get_array_size(_func_name, _param_name,
                                                        _default_size=Prototype.DEFAULT_ARRAY_SIZE)
            # param['type'] = param['type'].replace("[]", " *")  # we do not change, this field will not be used
            # param['pure_type'] = param['pure_type'].replace("[]", " *") # we do not change, this field will not be used
            param['kind'] = TypeKind.POINTER
            param['size'] = 8    # Not important # TODO:: Need to get the size of the pointer if there is a way..
            param['can_type'] = param['can_type'].replace("[]", " *")
            param['can_ptr_type'] = param['can_type'].replace(" *", "")

        # dealing with constant arrays (update pointee type and canonical types)
        if param['kind'] == TypeKind.CONSTANTARRAY:
            ptrtype = _type.get_canonical().get_array_element_type()
            param['ptr_type'] = ptrtype.spelling
            param['ptr_size'] = ptrtype.get_size()
            param['ptr_kind'] = ptrtype.kind
            param['driver_kind'] = "CONSTANT_ARRAY"
            param["array_size"] = int(param['size'] / param['ptr_size'])
            param['can_type'] = ptrtype.spelling + ' *'
            param['can_ptr_type'] = ptrtype.spelling

        # get structural information
        # TODO:: We may need to get some field information so that we can provide more detail information of a structure
        if param["driver_kind"].startswith("STRUCT") is True:
            cursor = _type if param["kind"] != TypeKind.POINTER else _type.get_pointee()
            param['struct'] = self.__get_structure_fields(cursor.get_canonical())

        return param

    def __get_qualifier(self, _type_str:str):
        '''
        return qualifier
        :param in_type_str:
        :return:
        '''
        split = _type_str.split()

        if len(split) == 0: return ""
        if split[0] in ('const', 'volatile', 'restrict'):
            return split[0]
        return ""

    def __get_structure_fields(self, _type:Type):
        '''
        Get field information if the _type is struct
          - Only analysis one-level fields
          - If the field is another struct,
             we just deal with it as a binary type by putting just 'struct'
        :param _type:
        :return:
        '''
        # print("structual info")
        fields = []
        for item in _type.get_fields():
            field_info = self.__get_type_info(item.type)

            # set the field name
            field = {'name': item.spelling}

            # set whether the field is pointer or not
            field['pointer'] = True if field_info['kind'] == TypeKind.POINTER else False

            # Set field data type
            if field['pointer'] is False:
                field['type'] = field_info['can_pure_type']
                if field_info['kind'] == TypeKind.RECORD: field['type'] = 'struct'
            else:
                field['type'] = field_info['can_ptr_pure_type']
                if field_info['ptr_kind'] == TypeKind.RECORD: field['type'] = 'struct'

            # Set field size
            # - if the field is a pointer, we just use the pointer variable size
            #   (not the size of the pointee)
            field['size'] = field_info['can_size']

            fields.append(field)
            # print("\t\t  %s"%field)

        return fields

    def __strip_type_qualifier(self, _type_str:str):
        '''
        remove qualifier from the type name (e.g., 'const int'--> 'int')
        it is also remove 'const' in the middle of the type (e.g., 'int* const --> int*)
        :param in_type_str:
        :return:
        '''
        split = _type_str.split()
        while len(split) > 0:
            if split[0] in ('const', 'volatile', 'restrict'):
                split.pop(0)
            else:
                break

        # remove const in the middle
        idx = len(split)-1
        while idx >= 0:
            if split[idx] == 'const':
                split.pop(idx)
            idx -= 1
        tmp_str = " ".join(split)

        return tmp_str

    def __get_array_size(self, _func_name:str, _param_name:str, _filename:str=None, _default_size=1):
        '''
        return array size based on the user-defined configuration (self.PARAMETER_FORMAT)
        :param _func_name:
        :param _param_name:
        :param _type:
        :param _filename:
        :return:
        '''
        if self.PARAMETER_FORMAT is None: return _default_size

        # check array size based on function name and parameter name
        for item in self.PARAMETER_FORMAT:
            # check predicates
            if not (item['function'] == _func_name and item['parameter'] == _param_name): continue
            if 'file' in item and item['file'] is not None:
                if _filename is None or item['file'] != _filename: continue

            return item['size']

        return _default_size

    def __get_void_ptr_type(self, _func_name:str, _param_name:str, _param:dict, _filename:str=None):
        '''
        return array size based on the user-defined configuration (self.PARAMETER_FORMAT)
        :param _func_name:
        :param _param_name:
        :param _type:
        :param _filename:
        :return:
        '''
        if self.PARAMETER_FORMAT is None: return _param

        if self.__AST is None:
            print("AST requires for analyzing Prototype of the function: %s" % _func_name)
            exit(1)

        # check user defined types for void pointer
        for item in self.PARAMETER_FORMAT:
            # check predicates
            if 'type' not in item: continue
            if not (item['function'] == _func_name and item['parameter'] == _param_name): continue
            if 'file' in item and item['file'] is not None:
                if _filename is None or item['file'] != _filename: continue

            # replace type
            # ptr_type = item['type'].replace("*", "").strip()
            type_decl = self.__AST.get_type(item['type'])
            ptr_type = type_decl.type.spelling
            ptr_can_type = type_decl.canonical.type.spelling
            # ptr_type = self.__AST.get_typename(item['type'])
            # ptr_can_type = self.__AST.get_canonical_typename(item['type'])
            ptr_size = self.__AST.get_type_size(item['type'])
            origin_type = ptr_type + ' *'
            can_origin_type = ptr_can_type + ' *'
            _param['type']          = origin_type
            _param['pure_type']     =  origin_type
            _param['can_type']      =  can_origin_type
            _param['ptr_type']      = ptr_type
            _param['can_ptr_type']  = ptr_can_type
            _param['ptr_size'] = ptr_size
            _param['ptr_kind'] = type_decl.type.kind
            _param['driver_kind']   = "POINTER"
            break

        return _param