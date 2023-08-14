#! /usr/bin/env python3
# Use libclang
import platform
if platform.python_version().startswith("3.") is False:
    raise Exception("Must be using Python 3")
import os
import argparse
import subprocess
import clang.cindex as parser
from clang.cindex import Index, CursorKind, TypeKind, Cursor, Type

if __package__ is None or __package__ == "":
    from Config import Config
    import compile
    import utils
else:
    from pipeline.Config import Config
    from pipeline import utils
    from pipeline import compile


########################################
# generate template main code
########################################
class ASTAnalyzer():
    # global input
    SOURCE_FILE = None

    # keeping Translation Units from clang
    AST = None
    TYPES = None

    def __init__(self, _source_file, _compilation_flags=None):
        # set paths
        self.SOURCE_FILE = _source_file
        if not os.path.isfile(_source_file):
            assert False, "The specified source file does not exist"

        # Create args for clang
        # For the header files that are not in global header directory,
        #   it needs to be provided manually using config.INCLUDES
        #   the INCLUDE directories are should be included in the compilation_info
        args = [v for v in _compilation_flags.split() if v.strip()]
        args += ["-I"+v for v in self.get_standard_includes()]

        # get AST of the source file using clang
        index = parser.Index.create()
        self.AST = index.parse(self.SOURCE_FILE, args=args)
        self.TYPES = self.__collect_type_defs()
        pass

    ############################################################
    # Type definitions
    ############################################################
    def __collect_type_defs(self):
        # extract function definitions from the AST
        types = {}
        for node in self.AST.cursor.get_children():
            # print("%s (%s, kind: %s, type: %s)" % (node.location.file.name, node.spelling, str(node.kind), node.type.spelling))
            # filter if elem is not the function definition
            if not (node.kind == CursorKind.TYPEDEF_DECL and node.is_definition()): continue
            # print("%s [displayname: %s, type: %s]" % (node.spelling, node.displayname, node.type.spelling))
            # print("\tCAN: %s [displayname: %s, type: %s]\n" % (node.canonical.spelling, node.canonical.displayname, node.canonical.type.spelling))

            types[node.spelling] = node
        return types

    def get_type_size(self, _typename):
        if _typename in self.TYPES:
            return self.TYPES[_typename].type.get_size()
        if _typename in self.primitive_types:
            size, format = self.primitive_types[_typename]
            return size
        return None

    def get_type(self, _typename):
        if _typename in self.TYPES:
            return self.TYPES[_typename]

        if _typename in self.primitive_types:
            example = None
            for key in self.TYPES.keys():
                example = self.TYPES[key]
                break

            # make a cursor imitation
            typenode = utils.dotdict({"spelling": _typename, "kind": example.kind})
            cannode = utils.dotdict({"type":typenode})
            typenode = utils.dotdict({"type":typenode,"canonical":cannode})
            return utils.dotdict(typenode)
        return None

    ############################################################
    # Function decls
    ############################################################
    def get_function_decls(self):
        '''
        return a Prototype object
            * function_name
            * return_type
        :param source_file:
        :param compilation_info:
        :return:
        '''
        if self.AST is None: return None

        # extract function definitions from the AST
        func_definitions = []
        for node in self.AST.cursor.get_children():
            # filter if elem is not the function definition
            if not (node.kind == CursorKind.FUNCTION_DECL and node.is_definition()): continue

            # check whether the function is in the given source code
            if node.location.file.name != self.SOURCE_FILE: continue

            # add element into definition
            func_definitions.append(node)
            if node.type.kind == TypeKind.FUNCTIONPROTO and  node.type.is_function_variadic():
                print("WARNING: The function {} is variadic. manually check for the call statement to pass more arguments".format(node.spelling))

        return func_definitions

    ############################################################
    # Util functions
    ############################################################
    def get_standard_includes(self):
        """
        libclang has problem locating some standard include. Help it
        """
        cmd = ["cc", "-E", "-x", "c", "-v", "/dev/null"]
        log = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT
        )
        log = log.decode('UTF-8', 'backslashreplace')
        started = False
        include_dirs = []
        for line in log.splitlines():
            if line.strip() == "#include <...> search starts here:":
                started = True
                continue
            if line.strip() == "End of search list.":
                started = False
                continue
            if started:
                include_dirs.append(line.strip())

        return include_dirs

    def get_includes(self):
        return self.AST.get_includes()

    def traverse(self, _cursor:Cursor, _kind:CursorKind, _name:str=None):
        '''
        generator by traversing recursive
        :param _cursor:
        :param _kind:
        :return:
        '''
        if _cursor.kind == _kind:
            if _name is not None:
                if _cursor.spelling == _name: yield _cursor
            else:
                yield _cursor
            return

        for node in _cursor.get_children():
            yield from self.traverse(node, _kind, _name)
        pass

    ############################################################
    # Primitive Types (Not used now)
    ############################################################
    primitive_types = {  ### type: [size, format]
        "int8_t"                : [1,"%hhd"],
        "int16_t"               : [2,"%hd"],
        "int32_t"               : [3,"%d"],
        "int64_t"               : [4,"%ld"],
        "__int8_t"              : [1,"%hhd"],
        "__int16_t"             : [2,"%hd"],
        "__int32_t"             : [3,"%d"],
        "__int64_t"             : [4,"%ld"],
        "uint8_t"               : [1,"%hhu"],
        "uint16_t"              : [2,"%hu"],
        "uint32_t"              : [3,"%u"],
        "uint64_t"              : [4,"%lu"],
        "__uint8_t"             : [1,"%u"],
        "__uint16_t"            : [2,"%hu"],
        "__uint32_t"            : [3,"%u"],
        "__uint64_t"            : [4,"%lu"],
        "bool"                  : [1,"%d"],
        "_Bool"                 : [1,"%d"],
        "char"                  : [1,"%d"],
        "unsigned char"         : [1,"%d"],
        "signed char"           : [1,"%d"],
        "char *"                : [8,"%s"],
        "int"                   : [4,"%d"],
        "signed"                : [4,"%d"],
        "signed int"            : [4,"%d"],
        "unsigned"              : [4,"%u"],
        "unsigned int"          : [4,"%u"],

        "short"                 : [2,"%hi"],
        "signed short"          : [2,"%hi"],
        "unsigned short"        : [2,"%hu"],
        "short int"             : [2,"%hi"],
        "signed short int"      : [2,"%hi"],
        "unsigned short int"    : [2,"%hu"],

        "long"                  : [8,"%ld"],
        "signed long"           : [8,"%ld"],
        "unsigned long"         : [8,"%lu"],
        "long int"              : [8,"%ld"],
        "signed long int"       : [8,"%ld"],
        "unsigned long int"     : [8,"%lu"],

        "long long"             : [8,"%lld"],
        "signed long long"      : [8,"%lld"],
        "unsigned long long"    : [8,"%llu"],
        "long long int"         : [8,"%lld"],
        "signed long long int"  : [8,"%lld"],
        "unsigned long long int": [8,"%llu"],
        "float"                 : [4,"%g"],
        "double"                : [8,"%G"],
        "long double"           : [16,"%LG"],
    }

    def is_primitive(self, _type_str:str, _type_kind:TypeKind=None):
        if _type_kind is not None:
            if _type_kind == TypeKind.POINTER: return True
            if _type_kind == TypeKind.VOID: return True
            if _type_kind == TypeKind.INCOMPLETEARRAY: return True   # e.g., int[], float[]

        if _type_str.find("*")>=0: return True
        return True if _type_str in self.primitive_types.keys() else False

    def get_size(self, _type_str:str, _type_kind:TypeKind=None):
        pointer_size = 8
        if _type_kind is not None:
            if _type_kind == TypeKind.POINTER: return pointer_size
            if _type_kind == TypeKind.VOID: return pointer_size
            if _type_kind == TypeKind.INCOMPLETEARRAY: return pointer_size   # e.g., int[], float[]

        if _type_str.find("*")>=0: return pointer_size
        if _type_str in self.primitive_types.keys():
            return self.primitive_types[_type_str][0]
        return None

    def get_printf_format(self, _type_str:str):
        if _type_str.find("*")>=0: return 8
        if _type_str in self.primitive_types.keys():
            return self.primitive_types[_type_str][0]
        elif _type_str == "enum" or _type_str.startswith("enum "):
            return "%d"
        return None

    ############################################################
    # Deprecated functions
    ############################################################
    def get_primitive_type_info(self, _type:Type):
        count = 0
        type_decl = _type.get_declaration()
        if type_decl.kind == CursorKind.TYPEDEF_DECL:
        # cursor
        # for elem in self.__traverse(_type.translation_unit.cursor, CursorKind.TYPEDEF_DECL, _type.spelling):
            count += 1
            print("[%d] %s - %s (%s): %s, %s" % (count, type_decl.displayname, type_decl.spelling, type_decl.kind, type_decl.canonical.spelling, type_decl.type))
            if sum([1 for item in type_decl.get_children()]) == 0: return

            info = self.__get_typedef_ref(type_decl)
            print("\t{'name':%s, 'name_origin':%s, 'size':%d, 'fields':[," % (info['name'], info['name_origin'], info['size']))
            for field in info['fields']:
                print("\t\t%s,"%str(field))
            print("\t] }")
            # for node in elem.get_children():
            #     print("\t%s (%s): %s" % (node.spelling, node.kind, node.canonical.spelling))

        mCurosr = _type.translation_unit.cursor


        # search structure
        for elem in self.traverse(_type.translation_unit.cursor, CursorKind.STRUCT_DECL):
            if not (elem.kind == CursorKind.STRUCT_DECL and elem.is_definition()): continue
            count += 1
            elem_data = self.__get_structure_info(elem)
            print("\t{'name':%s, 'name_origin':%s, 'size':%d, 'fields':[," % (elem_data['name'], elem_data['name_origin'], elem_data['size']))
            for field in elem_data['fields']:
                print("\t\t%s,"%str(field))
            print("\t] }")

        return True

    def __get_typedef_ref(self, _element:Cursor, _level=1):
        level = '\t' * _level
        print("%s%s (%s): %s" % (level, _element.spelling, _element.kind, _element.canonical.spelling))
        subiter = _element.get_children()
        for item in subiter:
            if item.kind == CursorKind.TYPE_REF:
                return self.__get_typedef_ref(item, _level+1)
            if item.kind == CursorKind.STRUCT_DECL:
                return self.__get_structure_info(item)
            return {'name':item.spelling, 'name_origin':item.canonical.spelling,
                    'fields':[], 'size': 1, 'object':item}
        return {'name':_element.spelling, 'name_origin':_element.canonical.spelling,
                'fields':[], 'size': 1, 'object':_element}

    def __get_structure_info(self, _element:Type):
        print("%s (%s): %s" % (_element.spelling, _element.kind, _element.canonical.spelling))

        subelem = _element.get_children()

        fields = []
        for item in subelem:
            if not (item.kind == CursorKind.FIELD_DECL): continue
            canonical_type = item.type.get_canonical()
            type_origin = canonical_type.spelling
            size = 1
            idx = type_origin.find('[')
            if idx >= 0:
                idx_end = type_origin.find(']', idx)
                size = int(type_origin[idx+1:idx_end])

            if type_origin == canonical_type.kind == CursorKind.STRUCTURE_DECL:
                type_origin = 'STRUCTURE'
                detail = self.__get_structure_info(canonical_type)
            else:
                detail = None
            field = {'name':item.spelling, 'type':type_origin, 'detail':detail, 'size':size}
            fields.append(field)

        # calculate total size
        sum_size = sum([field['size'] for field in fields])

        return {'name':_element.spelling, 'name_origin':_element.canonical.spelling,
                'fields':fields, 'size': sum_size, 'object':_element}


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
    config.augment_config()
    if args.repository_path is not None:
        config.REPO_PATH = args.repository_path

    include_txt = compile.get_gcc_params_include(config.INCLUDES, config.REPO_PATH)
    compilation_flags = config.SUT_COMPILE_FLAGS+" " + include_txt

    # Execute TemplateGenerator
    obj = ASTAnalyzer(args.source_file, compilation_flags)
    obj.traverse(None, CursorKind.TYPEDEF)

