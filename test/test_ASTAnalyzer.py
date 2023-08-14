import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest import TestCase
from pipeline import utils
from pipeline import compile
from pipeline import Config
from pipeline.ASTAnalyzer import ASTAnalyzer
from pipeline.Prototype import Prototype
from clang .cindex import Index, CursorKind, TypeKind, Cursor, Type


class TestASTAnalyzer(TestCase):
    COMPILATION_FLAG = None
    TEMPLATE_CONFIG = None

    def driver(self, _config_filename='../configs/config-asn1-mass-local.py'):
        # load config file
        global config
        conf = utils.load_module(_config_filename)
        config = Config(vars(conf))
        config.augment_config()
        config.REPO_PATH = utils.makepath("..", config.REPO_PATH)

        include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
        self.COMPILATION_FLAG = config.SUT_COMPILE_FLAGS + " " + include_txt

    def test_get_function_decls(self):
        self.driver()
        ast = ASTAnalyzer("resources/test.mut.1772.1_2_7.ICR.TypeNested_realArray_Initialize.c", self.COMPILATION_FLAG)
        func_decls = ast.get_function_decls()
        for func_decl in func_decls:
            print("%s: %s" % (func_decl.spelling, str(func_decl._loc)))
        # self.fail()

    def test_extract_function(self):
        self.driver()
        # target_func_name = "TypeNested_realArray_Initialize"
        ast = ASTAnalyzer("./resources/test.mut.1772.1_2_7.ICR.TypeNested_realArray_Initialize.c", self.COMPILATION_FLAG)

        output_path = "./extract"
        if os.path.exists(output_path) is False: os.makedirs(output_path)

        func_decls = ast.get_function_decls()
        for func_decl in func_decls:
            # print("%s: %s" % (func_decl.spelling, str(func_decl._loc)))
            code = ast.extract_function(func_decl.spelling)
            if code is None: self.fail()

            # replace function name
            end = code.find("(")
            start = code.rfind(" ", 0, end) + 1
            origin_name = code[start:end]
            _prefix = "mut"
            mut_name = _prefix + "_" + origin_name

            # convert function name
            print("{} --> {}".format(origin_name, mut_name))
            code = code[:start] + _prefix + "_" + code[start:]

            # save
            filename = os.path.join("%s/%s.c" % (output_path, origin_name))
            with open(filename, "w") as f:
                f.write(code)

    def test_test_param(self):
        self.driver()
        ast = ASTAnalyzer("resources/test.mut.1772.1_2_7.ICR.TypeNested_realArray_Initialize.c", self.COMPILATION_FLAG)
        target_function = "TypeWithOptional_Initialize"
        func_decls = ast.get_function_decls()

        for func_decl in func_decls:
            # if func_decl.spelling != target_function: continue
            # print("%s: %s" % (func_decl.spelling, str(func_decl._loc)))
            prototype = Prototype(None, _template_config=config.TEMPLATE_CONFIG)
            # info = prototype._Prototype__get_base_function_info(func_decl)
            # self.__print_base_func_info(info)
            info = prototype._Prototype__get_function_info(func_decl)
            # self.__print_func_info(info)
            prototype.update(info)
            print(prototype.get_param_info_list())

    def test_test_param(self):
        self.driver()
        ast = ASTAnalyzer("resources/test.mut.1772.1_2_7.ICR.TypeNested_realArray_Initialize.c", self.COMPILATION_FLAG)
        target_function = "AType_Encode"
        func_decls = ast.get_function_decls()

        for func_decl in func_decls:
            # if func_decl.spelling != target_function: continue
            # print("%s: %s" % (func_decl.spelling, str(func_decl._loc)))
            prototype = Prototype(None, _template_config=config.TEMPLATE_CONFIG)
            # info = prototype._Prototype__get_base_function_info(func_decl)
            # self.__print_base_func_info(info)
            info = prototype._Prototype__get_function_info(func_decl)
            # self.__print_func_info(info)
            prototype.update(info)
            print(prototype.get_param_info_list())

    def test_test_param_asn1(self):
        # failed_functions = ['AType_Decode', 'AType_Encode', 'ConfigString_Decode', 'ConfigString_Encode', 'FixedLenConfigString_Decode', 'FixedLenConfigString_Encode', 'My2ndArr_Decode', 'My2ndArr_Encode', 'My2ndAType_Decode', 'My2ndAType_Encode', 'My2ndBool_Decode', 'My2ndBool_Encode', 'My2ndInt_Decode', 'My2ndInt_Encode', 'My2ndInt_IsConstraintValid', 'My2ndReal_Decode', 'My2ndString_Decode', 'My2ndString_Encode', 'My2ndTypeNested_Decode', 'My2ndTypeNested_Encode', 'MyInt_Decode', 'MyInt_Encode', 'MyInt_Initialize', 'SubTypeWithOptional_Decode', 'SubTypeWithOptional_Encode', 'SuperChoice_Decode', 'SuperChoice_Encode', 'SuperChoice_IsConstraintValid', 'SuperRestrictedChoice_Decode', 'SuperRestrictedChoice_Encode', 'T_ARR_Decode', 'T_ARR_Encode', 'T_ARR_Equal', 'T_ARR_IsConstraintValid', 'T_ARR2_Decode', 'T_ARR2_Encode', 'T_ARR2_Equal', 'T_ARR2_IsConstraintValid', 'T_ARR3_Decode', 'T_ARR3_elem_Equal', 'T_ARR3_Encode', 'T_ARR3_IsConstraintValid', 'T_ARR4_Decode', 'T_ARR4_elem_Equal', 'T_ARR4_Encode', 'T_ARR4_Equal', 'T_ARR4_IsConstraintValid', 'T_BOOL_Decode', 'T_BOOL_Encode', 'T_FIXEDSTRING_Decode', 'T_INT_Decode', 'T_INT_Encode', 'T_META_Decode', 'T_META_Encode', 'T_POS_Decode', 'T_POS_Encode', 'T_POS_Equal', 'T_POS_IsConstraintValid', 'T_POS_SET_Decode', 'T_POS_SET_Encode', 'T_POS_SET_Equal', 'T_POS_SET_IsConstraintValid', 'T_POS_SET_subTypeArray_Initialize', 'T_POS_subTypeArray_Equal', 'T_REAL_Decode', 'T_SET_Decode', 'T_SET_Encode', 'T_SET_Equal', 'T_SET_IsConstraintValid', 'T_SETOF_Decode', 'T_SETOF_Encode', 'T_SETOF_IsConstraintValid', 'T_STRING_Decode', 'T_STRING_Encode', 'T_STRING_Initialize', 'T_TypeThatMustNotBeMappedExceptInPython_Decode', 'T_TypeThatMustNotBeMappedExceptInPython_Encode', 'T_TypeThatMustNotBeMappedExceptInPython_Equal', 'TypeNested_Decode', 'TypeNested_Encode', 'TypeNested_IsConstraintValid', 'TypeNested_octStrArray_elem_Equal', 'TypeNested_octStrArray_elem_Initialize', 'TypeWithOptional_b_Initialize', 'TypeWithOptional_Decode', 'TypeWithOptional_Encode', 'TypeWithOptional_Equal']
        # no_tar_functions = ['T_ARR3_IsConstraintValid', 'T_ARR_IsConstraintValid', 'T_ARR4_elem_Equal', 'TypeNested_IsConstraintValid', 'TypeWithOptional_Equal', 'T_SET_IsConstraintValid', 'TypeWithOptional_b_Initialize', 'My2ndInt_IsConstraintValid', 'T_ARR4_Equal', 'T_POS_Equal', 'T_POS_SET_Equal', 'T_TypeThatMustNotBeMappedExceptInPython_Equal', 'T_ARR4_IsConstraintValid', 'T_SETOF_IsConstraintValid', 'T_ARR3_elem_Equal', 'T_ARR_Equal', 'T_POS_subTypeArray_Equal', 'T_STRING_Initialize', 'T_POS_SET_subTypeArray_Initialize', 'T_ARR2_Equal', 'SuperChoice_IsConstraintValid', 'T_SET_Equal', 'TypeNested_octStrArray_elem_Equal', 'TypeNested_octStrArray_elem_Initialize', 'MyInt_Initialize']
        # functions = set(failed_functions) - set(no_tar_functions)
        # functions = no_tar_functions
        functions = ['T_POS_IsConstraintValid', 'T_ARR4_elem_Equal', 'T_POS_SET_Initialize', 'TypeNested_intArray_elem_Initialize', 'TypeNested_IsConstraintValid', 'TypeWithOptional_Equal', 'T_SET_IsConstraintValid', 'TypeNested_Equal', 'TypeNested_octStrArray_Initialize', 'AType_blArray_Equal', 'T_ARR2_IsConstraintValid', 'SubTypeWithOptional_Initialize', 'T_POS_label_Initialize', 'TypeWithOptional_b_Initialize', 'SuperChoice_Initialize', 'T_POS_SET_IsConstraintValid', 'My2ndInt_IsConstraintValid', 'T_ARR4_Equal', 'E_IsConstraintValid', 'SuperRestrictedChoice_IsConstraintValid', 'T_POS_subTypeArray_Initialize', 'AType_blArray_Initialize', 'T_FIXEDSTRING_Equal', 'TypeNested_Initialize', 'T_POS_Equal', 'T_ARR3_elem_Initialize', 'T_STRING_Equal', 'T_SET_data3_Equal', 'T_ARR2_Initialize', 'T_POS_SET_Equal', 'TypeWithOptional_IsConstraintValid', 'TypeNested_Encode', 'T_TypeThatMustNotBeMappedExceptInPython_Equal', 'T_ARR4_IsConstraintValid', 'TypeWithOptional_Initialize', 'T_POS_Encode', 'My2ndTypeNested_IsConstraintValid', 'TypeNested_int2Val_Initialize', 'T_SETOF_IsConstraintValid', 'TypeNested_boolArray_Equal', 'T_TypeThatMustNotBeMappedExceptInPython_IsConstraintValid', 'T_ARR3_elem_Equal', 'T_ARR_Equal', 'TypeNested_label_Initialize', 'T_POS_subTypeArray_Equal', 'T_ARR_Initialize', 'T_INT_Encode', 'SubTypeWithOptional_IsConstraintValid', 'T_BOOL_IsConstraintValid', 'T_STRING_Initialize', 'T_ARR3_Encode', 'My2ndReal_Equal', 'TypeNested_label_Equal', 'T_SET_Encode', 'T_POS_SET_subTypeArray_Initialize', 'T_FIXEDSTRING_Encode', 'FixedLenConfigString_Initialize', 'T_ARR3_IsConstraintValid', 'T_STRING_IsConstraintValid', 'T_POS_SET_label_Equal', 'T_TypeThatMustNotBeMappedExceptInPython_Encode', 'T_SET_data4_Initialize', 'TypeNested_intArray_Initialize', 'T_POS_SET_subTypeArray_Equal', 'T_ARR2_Equal', 'TypeNested_boolArray_Initialize', 'T_SET_data4_Equal', 'SuperChoice_IsConstraintValid', 'T_ARR_IsConstraintValid', 'FixedLenConfigString_IsConstraintValid', 'My2ndTypeNested_Encode', 'My2ndReal_Initialize', 'T_SET_Equal', 'T_ARR4_Initialize', 'E_Initialize', 'T_REAL_IsConstraintValid', 'My2ndArr_Encode', 'T_SETOF_Equal', 'TypeNested_octStrArray_elem_Equal', 'SuperChoice_second_choice_Initialize', 'TypeNested_realArray_Initialize', 'FixedLenConfigString_Encode', 'T_REAL_Equal', 'My2ndInt_Equal', 'AType_IsConstraintValid', 'MyInt_Encode', 'T_META_Encode', 'T_SETOF_Initialize', 'TypeNested_intVal_Equal', 'ConfigString_Encode', 'T_SETOF_elem_Initialize', 'SuperRestrictedChoice_Equal', 'TypeNested_intArray_Equal', 'TypeNested_int2Val_Equal', 'TypeWithOptional_c_Initialize', 'TypeNested_realArray_Equal', 'T_TypeThatMustNotBeMappedExceptInPython_param_Equal', 'FixedLenConfigString_Equal', 'T_STRING_Encode', 'SuperChoice_second_choice_Equal', 'T_INT_Equal', 'T_INT_Initialize', 'SuperChoice_Encode', 'TypeWithOptional_Encode', 'T_SET_data3_Initialize', 'My2ndAType_Equal', 'T_ARR3_Equal', 'T_BOOL_Initialize', 'T_SET_data1_Equal', 'T_ARR4_elem_Initialize', 'T_ARR4_Encode', 'ConfigString_IsConstraintValid', 'T_TypeThatMustNotBeMappedExceptInPython_param_Initialize', 'T_SET_Initialize', 'T_POS_SET_Encode', 'T_POS_SET_label_Initialize', 'SuperChoice_Equal', 'T_REAL_Initialize', 'TypeNested_octStrArray_elem_Initialize', 'SuperRestrictedChoice_Encode', 'My2ndReal_Encode', 'T_META_Initialize', 'T_ARR3_Initialize', 'TypeNested_int3Val_Initialize', 'T_REAL_Encode', 'ConfigString_Equal', 'E_Equal', 'My2ndArr_IsConstraintValid', 'ConfigString_Initialize', 'My2ndString_Equal', 'T_POS_label_Equal', 'TypeWithOptional_c_Equal', 'T_TypeThatMustNotBeMappedExceptInPython_Initialize', 'TypeNested_intArray_elem_Equal', 'E_Encode', 'TypeNested_int3Val_Equal', 'T_ARR2_Encode', 'T_INT_IsConstraintValid', 'My2ndInt_Encode', 'My2ndInt_Initialize', 'SubTypeWithOptional_Encode', 'My2ndArr_Equal', 'My2ndAType_Initialize', 'My2ndString_Initialize', 'T_ARR_Encode', 'TypeNested_intVal_Initialize', 'MyInt_Equal', 'MyInt_IsConstraintValid', 'TypeNested_octStrArray_Equal', 'T_FIXEDSTRING_Initialize', 'TypeWithOptional_b_Equal', 'T_ARR_elem_Equal', 'T_META_Equal', 'T_BOOL_Equal', 'My2ndTypeNested_Equal', 'T_SET_data1_Initialize', 'T_POS_Initialize', 'SuperRestrictedChoice_Initialize', 'My2ndBool_Equal', 'T_ARR_elem_Initialize', 'My2ndArr_Initialize', 'SubTypeWithOptional_Equal', 'T_SETOF_Encode', 'T_SETOF_elem_Equal', 'MyInt_Initialize', 'AType_Initialize', 'My2ndTypeNested_Initialize', 'My2ndBool_Initialize', 'T_FIXEDSTRING_IsConstraintValid', 'My2ndReal_IsConstraintValid', 'T_META_IsConstraintValid', 'My2ndString_Encode', 'My2ndString_IsConstraintValid']

        self.driver()
        # ast = ASTAnalyzer("resources/test.mut.1772.1_2_7.ICR.TypeNested_realArray_Initialize.c", self.COMPILATION_FLAG)
        ast = ASTAnalyzer("../_ASN1_MASS/repos/test.c", self.COMPILATION_FLAG)
        func_decls = ast.get_function_decls()

        for func in functions:
            for func_decl in func_decls:
                if func_decl.spelling != func: continue
                prototype = Prototype(None, _template_config=config.TEMPLATE_CONFIG)
                info = prototype._Prototype__get_function_info(func_decl)
                prototype.update(info)
                print(prototype.get_param_info_list())


    ####################################################
    #  DEBUG: Print function information (base)
    ####################################################
    def __print_func_info(self, _info):
        print("\tNAME      : %s" % _info['name'])
        print("\tRETURN    : %s" % _info['returns'])
        print("\tPARAMS    : [")
        for param in _info['params']:
            self.__print_param_info(param)
            self.__print_param_definition(param)
            self.__print_param_call(param)
            self.__print_input_size(param)
        print("\t           ]")

    def __print_param_info(self, param:dict):
        print("\t\t     %10s: {'type': %s}" % (param['name'], param['type']))
        print("\t\t               : [ori] {'type': %s, 'size': %d,  'kind': %s, 'qualifier': %s}" % (param['pure_type'], param['size'],  param['kind'], param['qualifier']))
        print("\t\t               : [ptr] {'type': %s, 'size': %d, 'kind': %s}" % (param['ptr_type'], param['ptr_size'], param['ptr_kind']))
        print("\t\t               : [etc] {'driver_kind': %s, 'array_size': %d, 'typedef': %s}" % (param['driver_kind'], param['array_size'], param['typedef']))

    def __print_param_definition(self, param:dict):
        if param['driver_kind'] == "ARRAY":
            print("\t\t               : Definition   - %s %s[%d];" % (param['ptr_type'], param['name'], param['array_size']))
        elif param['driver_kind'] == "CONSTANT_ARRAY":
            if param['typedef'] is True:
                print("\t\t               : Definition   - %s %s;" % (param['pure_type'] , param['name']))
            else:
                print("\t\t               : Definition   - %s %s[%d];" % (param['ptr_type'] , param['name'], param['array_size']))
        elif param['driver_kind'].find("POINTER") >= 0:
            print("\t\t               : Definition   - %s %s;  // sizeof=%d" % (param['ptr_type'], param['name'], param['ptr_size']))
        else:
            print("\t\t               : Definition   - %s %s;  // sizeof=%d" % (param['pure_type'], param['name'], param['size']))

    def __print_param_call(self, param:dict):
        if param['driver_kind'].find("ARRAY") >= 0:
            if param['ptr_type'].find("char") >= 0:
                print("\t\t               : FunctionCall - memcpy(%s, BUF, %d); %s[%d] = 0;" % (param['name'], param['array_size'] * param['ptr_size'],
                                                                                                param['name'], param['array_size']-1))
            else:
                print("\t\t               : FunctionCall - memcpy(%s, BUF, %d);" % (param['name'], param['array_size'] * param['ptr_size']))
            print("\t\t               : FunctionCall - call(%s); // call by ref" % (param['name']))
        elif param['driver_kind'].find("POINTER") >= 0:
            print("\t\t               : FunctionCall - memcpy(&%s, BUF, %d);" % (param['name'], param['ptr_size']))
            print("\t\t               : FunctionCall - call(&%s); // call by ref" % (param['name']))
        else:
            print("\t\t               : FunctionCall - memcpy(&%s, BUF, %d);" % (param['name'], param['size']))
            print("\t\t               : FunctionCall - call(%s); // call by value" % (param['name']))

    def __print_input_size(self, param:dict):
        if param['driver_kind'].find("ARRAY") >= 0:
            if param['ptr_type'].find("char") >= 0:
                size = param['array_size'] * param['ptr_size']
                print("\t\t               : WritingSize - %d with null (all: %d)" % (size - param['ptr_size'], size))
            else:
                print("\t\t               : WritingSize - %d" % (param['array_size'] * param['ptr_size']))
        elif param['driver_kind'].find("POINTER") >= 0:
            print("\t\t               : WritingSize - %d" % (param['ptr_size']))
        else:
            print("\t\t               : WritingSize - %d" % (param['size']))

    ####################################################
    #  DEBUG: Print function information (base)
    ####################################################
    def __print_base_func_info(self, _info):
        print("\tNAME      : %s" % _info['name'])
        print("\tRETURN    : %s" % _info['returns'])
        print("\tPARAMS    : [")
        for param in _info['params']:
            self.__print_base_param_info(param)
            self.__print_base_param_definition(param)
            self.__print_base_param_call(param)
            self.__print_base_input_size(param)
        print("\t           ]")

    def __print_base_param_info(self, param:dict):
        print("\t\t%20s: [ori] {'type': %s, 'size': %d, 'pure_type': %s, 'kind': %s}" % (param['name'], param['type'], param['size'], param['pure_type'], param['kind']))
        print("\t\t                    : [ptr] {'type': %s, 'size': %d, 'pure_type': %s, 'kind': %s}" % (param['ptr_type'], param['ptr_size'], param['ptr_pure_type'], param['ptr_kind']))
        print("\t\t                    : [can] {'type': %s, 'size': %d, 'pure_type': %s, 'kind': %s}" % (param['can_type'], param['can_size'], param['can_pure_type'], param['can_kind']))
        print("\t\t                    : [cptr] {'type': %s, 'size': %d, 'pure_type': %s, 'kind': %s}" % (param['can_ptr_type'], param['can_ptr_size'], param['can_ptr_pure_type'], param['can_ptr_kind']))

    def __print_base_param_definition(self, param:dict):
        if param['kind'] == TypeKind.POINTER:
            print("\t\t                    : Definition   - %s %s;  // sizeof=%d" % (param['ptr_pure_type'], param['name'], param['ptr_size']))
        else:
            print("\t\t                    : Definition   - %s %s;  // sizeof=%d" % (param['pure_type'], param['name'], param['size']))

    def __print_base_param_call(self, param:dict):
        if param['kind'] == TypeKind.POINTER:
            print("\t\t                    : FunctionCall - memcpy(&%s, BUF, %d);" % (param['name'], param['ptr_size']))
            print("\t\t                    : FunctionCall - call(&%s); // call by ref" % (param['name']))
        else:
            print("\t\t                    : FunctionCall - memcpy(&%s, BUF, %d);" % (param['name'], param['size']))
            print("\t\t                    : FunctionCall - call(%s); // call by value" % (param['name']))

    def __print_base_input_size(self, param:dict):
        if param['kind'] == TypeKind.POINTER:
            print("\t\t                    : WritingSize - %s" % (param['ptr_size']))
        else:
            print("\t\t                    : WritingSize - %s" % (param['size']))


if __name__ == '__main__':
    unittest.main()