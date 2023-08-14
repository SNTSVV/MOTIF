import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from pipeline.CParser import CommentsParser, DirectiveParser, C_NODE


class MyTestCase(unittest.TestCase):
    def load_data(self, _file):
        f = open(_file, "r")
        data = f.read()
        f.close()
        return data

    def test_comment_parser(self):
        # test with a file
        code = self.load_data("./resources/MLFS_s_deg2rad_mut.c")
        obj = CommentsParser(code)
        obj.parse()

        print("\n====result=====")
        obj.doc.print()

    def test_directive_parser(self):
        # test with a file
        code = self.load_data("./resources/MLFS_s_deg2rad_mut.c")
        code = CommentsParser(code).parse().code
        obj = DirectiveParser(code).parse()

        print("\n====result=====")
        obj.doc.print()


if __name__ == '__main__':
    unittest.main()
