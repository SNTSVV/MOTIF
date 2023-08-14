import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from pipeline.IncludeFinder import IncludeFinder


class MyTestCase(unittest.TestCase):
    def test_get_header_files_by_file(self):
        # test with a file
        finder = IncludeFinder(_file="./resources/test_includecode.c")
        finder.exclude(_file="./resources/test_excludecode.c")

        answer_global = set(["time.h", "sys/stat.h"])
        answer_local = set(["fcntl.h"])

        assert len(set(finder.globals) - answer_global) == 0, "global_headers are not detected well"
        assert len(set(finder.locals) - answer_local) == 0, "local_headers are not detected well"

    def test_exclude_items(self):
        # test with a file
        finder = IncludeFinder(_file="./resources/test_includecode.c")
        finder.exclude(_file="./resources/test_excludecode.c")
        finder.exclude_items(["sys/*"])

        answer_global = set(["time.h"])
        answer_local = set(["fcntl.h"])

        assert len(set(finder.globals) - answer_global) == 0, "global_headers are not correctly detected well"
        assert len(set(finder.locals) - answer_local) == 0, "local_headers are not correctly  detected well"

    def test_get_header_files_by_text(self):
        # test with a text
        with open("./resources/test_includecode.c", "r") as f: codebase = f.read()
        with open("./resources/test_excludecode.c", "r") as f: code1 = f.read()

        finder = IncludeFinder(_code=codebase)
        finder.exclude(_code=code1)

        answer_global = set(["time.h", "sys/stat.h"])
        answer_local = set(["fcntl.h"])

        assert len(set(finder.globals) - answer_global) == 0, "global_headers are not detected well"
        assert len(set(finder.locals) - answer_local) == 0, "local_headers are not detected well"

    def test_get_header_files3(self):
        # test with a text
        finder = IncludeFinder(_file="./resources/test_includecode.c")

        answer_global = set(["stdio.h","stdlib.h", "time.h", "sys/stat.h"])
        answer_local = set(["fcntl.h"])

        assert len(set(finder.globals) - answer_global) == 0, "global_headers are not detected well"
        assert len(set(finder.locals) - answer_local) == 0, "local_headers are not detected well"


if __name__ == '__main__':
    unittest.main()
