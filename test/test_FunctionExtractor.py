import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from pipeline.FunctionExtractor import FunctionExtractor


class MyTestCase(unittest.TestCase):
    def test_function_extract(self):
        obj = FunctionExtractor("")
        obj.extract("./resources/test_mutants.c", "timestamp_diff", "./outupt/extrcted0.c")
        obj.extract("./resources/test_function2.c", "test_funtion2", "./outupt/extrcted1.c")
        obj.extract("./resources/MLFS_s_deg2rad.c", "deg2rad", "./outupt/extrcted2.c")
        obj.extract("./resources/MLFS_s_deg2rad_mut.c", "deg2rad", "./outupt/extrcted3.c")
        obj.extract("./resources/MLFS___ieee754_acos.c", "__ieee754_acos", "./outupt/extrcted4.c")
        obj.extract("./resources/MLFS_test_sf_modf.c", "modff", "./outupt/extrcted5.c")
        obj.extract("./resources/MLFS_test_sf_signbitd.c", "__signbitd", "./outupt/extrcted6.c")






if __name__ == '__main__':
    unittest.main()
