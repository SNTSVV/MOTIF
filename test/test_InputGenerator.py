import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest import TestCase
from pipeline import utils
from pipeline import Config
from pipeline.InputGenerator import InputGenerator


class TestInputGenerator(TestCase):
    COMPILATION_FLAG = None
    TEMPLATE_CONFIG = None
    GEN = None

    def driver(self, _config_filename='"../config.py"'):
        # load config file
        global config
        conf = utils.load_module(_config_filename)
        config = Config(vars(conf))
        config.verify_template_config()
        config.augment_config()
        config.REPO_PATH = utils.makepath("..", config.REPO_PATH)

        # Execute TemplateGenerator
        self.GEN = InputGenerator(config.TEMPLATE_CONFIG)

    def test_to_bytes(self):
        self.driver()
        print("float=====")
        print(self.GEN._InputGenerator__to_bytes('float', 3230283776.000000))
        print(self.GEN._InputGenerator__to_bytes('float', 0.000000))
        print(self.GEN._InputGenerator__to_bytes('float', 1072693248.000000))
        print("double=====")
        print(self.GEN._InputGenerator__to_bytes('double', 13826050856027422720.000000))
        print(self.GEN._InputGenerator__to_bytes('double', 0.000000))
        print(self.GEN._InputGenerator__to_bytes('double', 4602891378046628864.000000))
        print("char=====")
        print(self.GEN._InputGenerator__to_bytes('char', b'\xFF'))
        print(self.GEN._InputGenerator__to_bytes('char', b'\x00'))
        print(self.GEN._InputGenerator__to_bytes('char', b'\x41'))
        print("char 2=====")
        print(self.GEN._InputGenerator__to_bytes('char', 'A'))
        print(self.GEN._InputGenerator__to_bytes('char', 'B'))
        print(self.GEN._InputGenerator__to_bytes('char', 'C'))

        print("string=====")
        print(self.GEN._InputGenerator__to_bytes('char', "2145916800.999999999"))
        print(self.GEN._InputGenerator__to_bytes('char', "1970-01-01T00:00:00Z"))
        print(self.GEN._InputGenerator__to_bytes('char', "2038-01-01T00:00:00Z"))

        print("bool=====")
        # assert self.GEN.to_bytes('_Bool', True) == b'\x01', "Error on _Bool"
        # assert self.GEN.to_bytes('_Bool', True) == b'\x00', "Error on _Bool"
        print(self.GEN._InputGenerator__to_bytes('_Bool', True))
        print(self.GEN._InputGenerator__to_bytes('_Bool', False))

    def test_get_binary_value(self):
        self.driver()
        target_function = "TypeWithOptional_Initialize"
        # def_type, can_type, size, array_size, driver_kind = _param
        params = [
             {'name': 'ca', 'def_type': 'int', 'can_type': 'int', 'size': 4, 'array_size': 1, 'driver_kind': 'PRIMITIVE'}
            ,{'name': 'a', 'def_type': 'int', 'can_type': 'int', 'size': 4, 'array_size': 1, 'driver_kind': 'POINTER'}
            ,{'name': 'b', 'def_type': 'float', 'can_type': 'float', 'size': 12, 'array_size': 3, 'driver_kind': 'CONSTANT_ARRAY'}
            ,{'name': 'c', 'def_type': 'float', 'can_type': 'float', 'size': 400, 'array_size': 100, 'driver_kind': 'ARRAY'}
            ,{'name': 'd', 'def_type': 'char', 'can_type': 'char', 'size': 100, 'array_size': 100, 'driver_kind': 'ARRAY'}
            ,{'name': 'k', 'def_type': '__uint32_t', 'can_type': 'unsigned int', 'size': 4, 'array_size': 1, 'driver_kind': 'PRIMITIVE'}
            ,{'name': 'tim', 'def_type': 'asn1SccSint', 'can_type': 'long long', 'size': 8, 'array_size': 1, 'driver_kind': 'PRIMITIVE'}
            ,{'name': 'fo1', 'def_type': 'T_SET_data3', 'can_type': 'long long', 'size': 8, 'array_size': 1, 'driver_kind': 'POINTER'}
            ,{'name': 'name', 'def_type': 'FixedLenConfigString', 'can_type': 'char', 'size': 6, 'array_size': 1, 'driver_kind': 'CONSTANT_ARRAY'}
            ,{'name': 'test', 'def_type': 'T_TypeThatMustNotBeMappedExceptInPython', 'can_type': 'T_TypeThatMustNotBeMappedExceptInPython', 'size': 48, 'array_size': 1, 'driver_kind': 'STRUCT_POINTER'}
            ,{'name': 'pVal', 'def_type': 'TypeWithOptional', 'can_type': 'TypeWithOptional', 'size': 80, 'array_size': 1, 'driver_kind': 'STRUCT_POINTER'}
        ]

        for param in params:
            values = [ self.GEN.get_binary_value(target_function, param, it) for it in ["N", "Z", "P"] ]
            print(str(param['name']) +": " + str(values))

    def test_get_binary_value2(self):
        self.driver()
        target_function = 'AType_Encode' # 'test.mut.221.3_1_8.UOI.AType_Encode.c'
        params = [
             {'name': 'pVal', 'def_type': 'AType', 'can_type': 'AType', 'size': 10, 'array_size': 1, 'driver_kind': 'STRUCT_POINTER'}
            ,{'name': 'pBitStrm', 'def_type': 'BitStream', 'can_type': 'struct BitStream_t', 'size': 48, 'array_size': 1, 'driver_kind': 'STRUCT_POINTER'}
            ,{'name': 'pErrCode', 'def_type': 'int', 'can_type': 'int', 'size': 4, 'array_size': 1, 'driver_kind': 'POINTER'}
            ,{'name': 'bCheckConstraints', 'def_type': 'flag', 'can_type': '_Bool', 'size': 1, 'array_size': 1, 'driver_kind': 'PRIMITIVE'}
        ]

        for param in params:
            values = [ self.GEN.get_binary_value(target_function, param, it) for it in ["N", "Z", "P"] ]
            if None in values:
                raise Exception("Not acceptable data type of {} : {}".format(target_function, param ))
            print(str(param['name']) +": " + str(values))


if __name__ == '__main__':
    unittest.main()