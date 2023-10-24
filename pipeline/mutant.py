#! /usr/bin/env python3

import os

if __package__ is None or __package__ == "":
    from utils import dotdict
else:
    from pipeline.utils import dotdict


class Mutant(dotdict):

    @staticmethod
    def parse(_filepath):
        # mutant file format
        # path/[source_code_name].mut.[line_number].[loc_info].[mutation_type].[function_name].c
        obj = Mutant()
        obj['fullpath']  = _filepath                         # input path
        obj['dir_path']  = os.path.dirname(_filepath)        # dirpath of mutant src/path/to/codefilename/
        obj['filename'] = os.path.basename(_filepath)        # mutant file name (including ext)

        pure_filename, ext = os.path.splitext(obj['filename'])   # mutant name (without ext)
        obj['name'] = pure_filename
        obj['ext'] = ext
        items = obj['name'].split(".")
        obj['src_path'] = obj['dir_path'] + ext    # src/path/to/codefile.c  in $REPOS
        obj['src_name']  = items[0] + ext          # codefile.c
        obj['line']     = items[2]                 # mutated line number
        obj['loc']      = items[3]                 # additional info for mutation
        obj['type']     = items[4]                 # type of mutant (ROR, LOD, ...)
        obj['func']     = items[5]                 # mutated function name
        return obj

    def __repr__(self):
        return "Mutant-%s (%s:%s:%s:%s:%s)" % \
               (self.src, self.func, self.type, self.line, self.loc, self.dir_path)

    def __str__(self):
        txt  = "[Mutant]\n"
        txt += "  - TEST_MUTANT           : %s\n" % self.fullpath
        txt += "  - Mutant dir path       : %s\n" % self.dir_path
        txt += "  - Mutant name           : %s\n" % self.name
        txt += "  - Source ext            : %s\n" % self.ext
        txt += "  - Source code file      : %s\n" % self.src_path
        txt += "  - Function name         : %s\n" % self.func
        txt += "  - Mutation type         : %s\n" % self.type
        txt += "  - Mutated line          : %s\n" % self.line
        txt += "  - Mutated loc (?)       : %s\n" % self.loc
        return txt

    def print(self):
        print(self.__str__())

    # def get_code_file(self):
    #     return self.dir_path+".c"
