#! /usr/bin/env python3
# Use libclang
import platform
if platform.python_version().startswith("3.") is False:
    raise Exception("Must be using Python 3")
import os
import argparse
import re
import codecs
import jinja2
from jinja2 import Environment, select_autoescape

if __package__ is None or __package__ == "":
    from ASTAnalyzer import ASTAnalyzer
    from Prototype import Prototype
    from IncludeFinder import IncludeFinder
    from Config import Config
    import compile
    import utils
else:
    from pipeline.ASTAnalyzer import ASTAnalyzer
    from pipeline.Prototype import Prototype
    from pipeline.IncludeFinder import IncludeFinder
    from pipeline.Config import Config
    from pipeline import utils
    from pipeline import compile


########################################
# generate template main code
########################################
# Our code generator can deal with primitive types and structure and char array.
# e.g., char[10] value;   --> func_call(char *value);
#       int value;        --> func_call(int * value);  <- in this case the value can be used for out
#       int[10] value;    --> func_call(int * value);  <- we cannot distinguish int array and the above one
# When you deal with a structure, it should be careful.
#     if the structure contains pointer or char array, it may cause an BAD ACCESS error.
# When we deal with a char array, we assume that the size of the array is 100 as default.
#      if you want to apply different types, please use TEMPLATE_CONFIG in config file.
#       - 'DEFAULT_ARRAY_SIZE'
#       - 'PARAMETER_FORMAT'
class TemplateGenerator():
    # global input
    SOURCE_FILE = None
    OUTPUT_PATH = None
    INPUT_PATH = None

    #internal objects
    AST:ASTAnalyzer = None
    functions = None        # List of Cursors (FUNCTION_DECLARATION)
    prototypes = {}         # List of prototypes (Prototype class)

    def __init__(self, _source_file, _config:Config, _compilation_flags=None):
        # set configurations
        global confTemp
        confTemp = _config

        # set paths
        self.SOURCE_FILE = _source_file
        if not os.path.isfile(_source_file):
            assert False, "The specified source file does not exist"

        # define _compilation_flag if it is not provided
        if _compilation_flags is None:
            include_txt = compile.get_gcc_params_include(confTemp.INCLUDES, confTemp.REPO_PATH)
            _compilation_flags = confTemp.SUT_COMPILE_FLAGS+" " + include_txt

        # process
        self.AST = ASTAnalyzer(self.SOURCE_FILE, _compilation_flags)
        self.functions = self.AST.get_function_decls()
        self.prototypes = {}
        pass

    def generate(self, _func_name:str, _driver_src_path, _template_entry, _appendix=None):
        if _func_name not in self.prototypes:
            # process of the generating template
            target_func_decl = None
            for func_decl in self.functions:
                if _func_name is not None and func_decl.spelling != _func_name: continue
                target_func_decl = func_decl

            if target_func_decl is None:
                print("Not found the function in the code: %s" % _func_name)
                return False

            # Convert the AST object to Prototype object
            prototype = Prototype(target_func_decl, confTemp.TEMPLATE_CONFIG, self.AST)
            self.prototypes[_func_name] = prototype
        else:
            prototype = self.prototypes[_func_name]

        if self.check_non_applicable_types(prototype):
            print("@non-applicable-functions: {} {}".format(prototype.returns['type'], prototype.prototype))
            return False

        # generate test driver for AFL execution
        try:
            os.makedirs(os.path.dirname(_driver_src_path), exist_ok=True)
        except OSError as e:
            if e.errno == 20:
                print("Cannot create the directory: %s. \nPlease check there is a file with the same name"%_driver_src_path)
                raise
        self.create_concrete_code(prototype, _appendix, _driver_src_path, _template_entry)
        print("Generated test driver for {}: {}".format(_func_name, _driver_src_path))
        return True

    def check_non_applicable_types(self, _prototype):
        # if _prototype.returns['driver_kind'] == "VOID_POINTER": return True
        # for param in _prototype.params:
        #     if param['driver_kind'].startswith("VOID") is True: return True
        if _prototype.params is None or len(_prototype.params)==0: return True

        # list_non_applicable_types = [
        #     "void *",
        # ]
        # for item in list_non_applicable_types:
        #     if _prototype.returns['type'].startswith(item):
        #         return True
        #     for arg in _prototype.args:
        #         if arg['type'].startswith(item):
        #             return True
        return False

    ########################################
    # sub process steps
    ########################################
    def load_templates(self):
        '''
        load all template files from the specified directory "confTemp.TEMPLATE_ROOT_DIR"
        :return:
        '''
        templates = {}

        # get template directory
        # template_path = os.path.dirname(os.path.abspath(__file__))
        # template_path = os.path.join(template_path, confTemp.TEMPLATE_ROOT_DIR)
        template_path = confTemp.TEMPLATE_ROOT_DIR
        if template_path is None or template_path == "":
            template_path = os.path.join(os.path.dirname(__file__), "templates")

        # load all template files in the directory
        files = utils.get_all_files(template_path, "*.*", True)
        for file in files:
            filepath = os.path.join(template_path, file)
            code_text = codecs.open(filepath,'r', encoding="utf-8").read()
            templates[file] = code_text
        return templates

    def create_concrete_code(self, _prototype:Prototype, _appendix, _output_file, _template_main):

        # get template rander object
        template_set = self.load_templates()
        env = Environment(loader=jinja2.DictLoader(template_set),
                          autoescape=select_autoescape(),
                          trim_blocks=True, lstrip_blocks=True)
        template = env.get_template(_template_main)

        # find additional includes from source file
        if confTemp.TEMPLATE_CONFIG["AUTO_EXCLUDE_HEADERS"]:
            finder = IncludeFinder(_file=self.SOURCE_FILE, _AST=self.AST)
        else:
            finder = IncludeFinder(_file=self.SOURCE_FILE)
        finder.exclude(_code=template_set[_template_main]) # we assume only the main template includes header files
        # manual excluding header files that are listed in the EXCLUDE_HEADERS
        finder.exclude_manual_items(confTemp.TEMPLATE_CONFIG["EXCLUDE_HEADERS"])

        # check printing extern option
        source_rel_path = self.SOURCE_FILE.replace(confTemp.REPO_PATH, "")
        if source_rel_path.startswith("/"): source_rel_path = source_rel_path[1:]
        source_rel_path = utils.make_pure_relative_path(source_rel_path)
        flag_extern = True
        for item in confTemp.TEMPLATE_CONFIG["NO_EXTERNS"]:
            item_file = utils.make_pure_relative_path(item['file'])
            if item_file == source_rel_path \
                    and _prototype.name == item['function']:
                flag_extern = False
                break

        print("APPENDIX: "+ str(_appendix))
        # rendering the template
        code = template.render(
            function=_prototype.get_driver_dict(),
            includes={"global": finder.globals, "local": finder.locals},
            initializes=self.get_initialize_stats(),
            source_file=self.SOURCE_FILE,
            flag_extern=flag_extern,
            appendix=_appendix
        )

        # saving the code into the file
        with open(_output_file, 'w') as f:
            f.write(code)
        return True

    def get_initialize_stats(self):
        # obtain relative path of source file from the REPO_PATH (without "./")
        repo_path = confTemp.REPO_PATH[2:] if confTemp.REPO_PATH.startswith("./") else confTemp.REPO_PATH
        src_path = self.SOURCE_FILE[2:] if self.SOURCE_FILE.startswith("./") else self.SOURCE_FILE
        rel_src_path = src_path.replace(repo_path, "")
        if rel_src_path.startswith("/"): rel_src_path = rel_src_path[1:]

        # match key values with the rel_src_path and find corresponding initialization statements
        initializes = []
        keys = confTemp.TEMPLATE_CONFIG["INITIALIZE"].keys()
        for key in keys:
            key_pattern = key[2:] if key.startswith("./") else key
            key_pattern = self.convert_regex_str(key_pattern)
            if re.match(key_pattern, rel_src_path) is not None:
                initializes = confTemp.TEMPLATE_CONFIG["INITIALIZE"][key]
                break

        return initializes

    def convert_regex_str(self, match_str):
        import re
        allowed_special_chars = "-(){}!@#$%^&"
        allowed_special_chars = re.escape(allowed_special_chars)

        # split items
        items = match_str.split("/")

        # prepare splitter
        splitter = re.escape("/")
        splitter_pos = [True] * len(items)
        splitter_pos[len(splitter_pos)-1] = False

        # convert wildcard to regex
        for idx in range(len(items)):
            if items[idx] == "**":
                items[idx] = r"[\w\/\\%s]*\/"%allowed_special_chars
                splitter_pos[idx] = False
                continue

            items[idx] = re.escape(items[idx])
            wildcard = re.escape("*")
            if items[idx].find(wildcard) >= 0:
                items[idx] = items[idx].replace(wildcard, r"[\w%s]*"%allowed_special_chars)

        # merge regex
        rex = r""
        for idx in range(len(items)):
            rex += items[idx]
            if splitter_pos[idx] is True: rex += splitter

        return rex


def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file", metavar="source-file", help="source file containing the functions to test (all defined functions)")
    parser.add_argument("output_dir", metavar="output-dir", help="Directory to put the generated files")
    parser.add_argument("-c", "--config-file", dest="config_file", default=None, help="Configuration file that speifies, in JSON format, the types conversion and printing formatting, as well as output in function arguments")
    parser.add_argument("-f", "--function", dest="function_name", default=None, help="function name that you want to generate test driver")
    parser.add_argument("-r", "--repository", dest="repository_path", default=None, help="If you want to specify, a specific reposritory to be worked of this generator")
    args = parser.parse_args()

    if args.config_file is None:
        print("Please provide config file using -c parameter.")
        exit(1)

    return args


if __name__ == "__main__":
    args = parse_arg()

    # load config file
    conf = utils.load_module(args.config_file)
    config = Config(vars(conf))
    config.verify_template_config()
    config.augment_config()
    if args.repository_path is not None:
        config.REPO_PATH = args.repository_path

    # Execute TemplateGenerator
    gen = TemplateGenerator(args.source_file, args.output_dir, config, None)
    test_driver_name = os.path.join(args.function_name + '.wrapping_main.c')
    ret = gen.generate(args.function_name, test_driver_name, config.TEMPLATE_FUZZING_DRIVER)
    print("result: %s"%ret)

    # Additional code for generating inputs together
    from InputGenerator import InputGenerator
    input_dir = utils.makepath(args.output_dir, 'inputs')
    InputGenerator(config.TEMPLATE_CONFIG).generate(gen.prototypes[args.function_name], input_dir)
    print("Generated input files for {} in {}".format(args.function_name, input_dir))


# Test code
# python3 pipeline/TemplateGenerator.py -c config.py case_studies/ASN1/repos/test.c ./case_studies/ASN1/testoutput