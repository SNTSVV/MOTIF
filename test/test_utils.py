#! /usr/bin/env python3
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest import TestCase
from pipeline import utils


class TestListRunner(TestCase):

    def test_makepath(self):
        assert utils.makepath("./", ".//src/Makedir", "../abc/ccc") == "./src/abc/ccc", \
            "Error to generate proper path"
        assert utils.makepath("../", "../abc/", "../bbb/ccc") == "../../bbb/ccc", \
            "Error to generate proper path"
        assert utils.makepath("./", "../abc/", "../bbb/ccc") == "../bbb/ccc", \
            "Error to generate proper path"
        assert utils.makepath("./", "../../abc/", "../bbb/ccc") == "../../bbb/ccc", \
            "Error to generate proper path"
        assert utils.makepath("/", "../../abc/", "../bbb/ccc") == "/../../bbb/ccc", \
            "Error to generate proper path"
        pass

    def test_convert_time_for_slurm(self):
        timestr = utils.convert_time_for_SLURM(1)
        assert timestr == "00:00:01", "Error "+timestr+" for 1"

        timestr = utils.convert_time_for_SLURM(10)
        assert timestr == "00:00:10", "Error "+timestr+" for 10"

        timestr = utils.convert_time_for_SLURM(60)
        assert timestr == "00:01:00", "Error "+timestr+" for 60"

        timestr = utils.convert_time_for_SLURM(10800)
        assert timestr == "03:00:00", "Error "+timestr+" for 10800"

        timestr = utils.convert_time_for_SLURM(86400)
        assert timestr == "1-00:00:00", "Error "+timestr+" for 86400"

        timestr = utils.convert_time_for_SLURM(86400*2+1)
        assert timestr == "2-00:00:00", "Error "+timestr+" for over 2 days"

        timestr = utils.convert_time_for_SLURM(-1)
        assert timestr is None, "Error "+timestr+" for -1"

        pass

    def test_docdict(self):
        d = utils.dotdict({"test":1})
        assert d.test == 1, "Not available to access as a field"

    def test_prepare_directory(self):
        target = "./temp/test"
        if os.path.exists(target): os.removedirs(target)
        utils.prepare_directory(target)
        assert os.path.exists(target) is True, "prepare_directory function cannot make a directory"
        os.removedirs(target)


if __name__ == '__main__':
    unittest.main()