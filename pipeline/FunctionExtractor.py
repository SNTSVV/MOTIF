#! /usr/bin/env python3
import os
import re
import argparse

if __package__ is None or __package__ == "":
    import utils
    import compile
    from Config import Config
    from ASTAnalyzer import ASTAnalyzer
    from CParser import DirectiveParser, C_NODE
else:
    from pipeline.ASTAnalyzer import ASTAnalyzer
    from pipeline.CParser import DirectiveParser, C_NODE
    from pipeline import utils
    from pipeline import compile
    from pipeline import Config


class FunctionExtractor(object):
    PREFIX_FUNCTION_NAME = None
    POSTFIX_FUNCTION_NAME = None
    COMPILATION_FLAGS = None

    def __init__(self, _compilation_flags:str, _prefix=None, _postfix=None):
        self.COMPILATION_FLAGS = _compilation_flags
        self.PREFIX_FUNCTION_NAME = _prefix
        self.POSTFIX_FUNCTION_NAME = _postfix
        pass

    def extract(self, _input_file, _func, _output_file):
        # get start and end offsets of target function
        start, end = self.get_function_offsets(_input_file, _func)

        # get entire source code
        code = self.get_source_code(_input_file)

        # update start point (if there is #ifdef or #ifndef)
        start = self.get_start_point_by_preprocessor(code, start, end)

        # select target code
        code = code[start:end]  # bring the code by the offsets between (start, end) inclusive

        # change function name
        code = self.change_function_name(_func, code)

        # store the code
        parent = os.path.dirname(_output_file)
        os.makedirs(parent, exist_ok=True)
        with open(_output_file, 'w') as f:
            f.write(code)

        return True

    def get_function_offsets(self, _input_file, _func):
        # extract code
        ast = ASTAnalyzer(_input_file, self.COMPILATION_FLAGS)

        # finds all the AST of functions in the code
        func_decls = ast.get_function_decls()

        # Convert the AST object to Prototype object
        target_func = None
        for func_decl in func_decls:
            if func_decl.spelling != _func: continue
            target_func = func_decl
            break
        if target_func is None: return (None, None)

        # return offsets
        start = target_func.extent.start.offset
        end = target_func.extent.end.offset
        return (start, end)

    def get_source_code(self, _filename):
        f = open(_filename, "r")
        code = f.read()
        f.close()
        return code

    def get_start_point_by_preprocessor(self, _code:str, _start:int, _end:int):
        '''
        get the offset of the start point considering preprocess directives such as #ifdef
        :param _func_decl:
        :return:
        '''
        parser = DirectiveParser(_code).parse()

        # select node that covers the specified range (_start, _end)
        selected = self.traverse(parser.doc, _start, _end)
        # selected.print()

        # removes non-fragmented nodes by the function
        selected = self.removes(selected, _start, _end)
        # selected.print()

        # if there is fragmented nodes
        if len(selected.children) == 0:
            return _start
        elif len(selected.children) == 1:
            child = selected.children[0]
            return child.start["offset"]
        else:
            # I don't expect we gonna see this match
            print("ERROR: too many children")
            selected.print()
            exit(1)
        pass

    def traverse(self, _node:C_NODE, _start, _end, _level=0):
        # print("search [%d-%d] lv=%d: %s"%(_start, _end, _level,_node))
        if _node.start["offset"] <= _start and _node.end["offset"] >= _end:
            # check if there is any child that entirely include the range (_start, _end)
            target = None
            for child in _node.children:
                node = self.traverse(child, _start, _end, _level+1)
                if node is not None:
                    target = node
                    break

            return _node if target is None else target
        return None

    def removes(self, _node:C_NODE, _start, _end):
        # remove nodes before or after the function
        for idx in reversed(range(0, len(_node.children))):
            child = _node.children[idx]
            if child.end["offset"]< _start or  child.end["offset"] > _end:
                del _node.children[idx]

        # remove nodes inside of the function
        for idx in reversed(range(0, len(_node.children))):
            child = _node.children[idx]
            if _start < child.start["offset"] and child.end["offset"] < _end:
                del _node.children[idx]

        return _node

    def change_function_name(self, _func, _code):
        if (self.PREFIX_FUNCTION_NAME is not None and self.POSTFIX_FUNCTION_NAME is not None):
            return True

        # decide new function name
        new_func = self.get_mutated_func_name(_func)

        # replace function name (recursive function are also changed)
        #   including the following characters for recursive functions: "=+-*/%|&()<>[];"
        rexFrom = r"([\s\=\+\-\*\/\%%\|\&\(\)\<\>;])(%s)(\s*\()" % _func
        rexTo = r"\1%s\3"% new_func
        _code = re.sub(rexFrom, rexTo, _code)

        return _code

    def get_mutated_func_name(self, _func):
        new_func = _func
        new_func = self.PREFIX_FUNCTION_NAME + '_' + new_func if self.PREFIX_FUNCTION_NAME is not None else new_func
        new_func = new_func + '_' + self.POSTFIX_FUNCTION_NAME if self.POSTFIX_FUNCTION_NAME is not None else new_func
        return new_func


# TEST Code
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file", metavar="[source-file]", help="source file containing the functions to test (all defined functions)")
    parser.add_argument("func_name", metavar="[func-name]", help="name of the mutated function")
    parser.add_argument("output_file", metavar="[output-file]", help="output source file")
    parser.add_argument("-c", "--config-file", dest="config_file", default="../config.py", help="Configuration file that speifies, in JSON format, the types conversion and printing formatting, as well as output in function arguments")
    parser.add_argument("-r", "--repository", dest="repository_path", default=None, help="If you want to specify, a specific reposritory to be worked of this generator")
    args = parser.parse_args()

    # load config
    conf = utils.load_module(args.config_file)
    config = Config(vars(conf))
    config.augment_config()

    # set repository path
    if args.repository_path is not None:
        config.REPO_PATH = args.reposigory_path

    # convert CRLF to LF
    utils.convert_CRLF_to_LF(args.source_file)

    # generate compilation_flags
    include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
    compilation_flags = config.SUT_COMPILE_FLAGS + " " + include_txt

    obj = FunctionExtractor(compilation_flags, _prefix='mut')
    obj.extract(args.source_file, args.func_name, args.output_file)


