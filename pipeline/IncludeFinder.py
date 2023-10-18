import re
import codecs
import chardet

if __package__ is None or __package__ == "":
    import utils
    from ASTAnalyzer import ASTAnalyzer
    from CParser import CommentsParser
else:
    from pipeline import utils
    from pipeline.ASTAnalyzer import ASTAnalyzer
    from pipeline.CParser import CommentsParser


class IncludeFinder():
    '''
    This class is designed for providing unique header files that are included in a source code.
    You can exclude some header files that are contained in other source codes.
    Thus, if you provide multiple code files,
    this class returns header files that are included in the first source code and
    are not included in the remaining source codes.
    '''

    # List of source codes: contains all the source codes for this class
    globals = None
    locals = None
    excludes = None

    ## keeping reference
    __AST = None
    source_file = None

    def __init__(self, _file=None, _code=None, _AST:ASTAnalyzer=None):
        if _file is not None:
            self.source_file = _file
            _code = self.__load_code(_file)

        if _code is None: raise Exception("Please provide proper input")

        if _AST is not None:
            self.__AST = _AST

        uncommented_code = CommentsParser(_code).remove_comments().code
        self.globals = self.__get_header_files(_code=uncommented_code, _is_local=False)
        self.globals = self.__select_preprocessed_header_files(self.globals)
        self.locals = self.__get_header_files(_code=uncommented_code, _is_local=True)
        self.locals = self.__select_preprocessed_header_files(self.locals)
        pass

    def exclude(self, _file=None, _code=None):
        if _file is not None:
            _code = self.__load_code(_file)

        if _code is None: raise Exception("Please provide proper input")

        # obtain headers from the _code
        uncommented_code = CommentsParser(_code).remove_comments().code
        globals = self.__get_header_files(_code=uncommented_code, _is_local=False)
        globals = self.__select_preprocessed_header_files(globals)
        locals = self.__get_header_files(_code=uncommented_code, _is_local=True)
        locals = self.__select_preprocessed_header_files(locals)

        self.globals = self.__subtract_items(self.globals, globals) # list(set(self.globals) - set(globals))
        self.locals = self.__subtract_items(self.locals, locals)  #list(set(self.locals) - set(locals))

    def __subtract_items(self, _target, _excluding_list):
        new_list = []
        for item in _target:
            if item in _excluding_list: continue
            new_list.append(item)
        return new_list

    def exclude_manual_items(self, _items):
        '''
        exclude header files that matches with _items
        :param _items:
        :return:
        '''
        self.globals = self.__exclude_manual_items(self.globals, _items)
        self.locals = self.__exclude_manual_items(self.locals, _items)

    def __exclude_manual_items(self, _target_list, _exclude_patterns):
        '''
        return the _list by excluding the elements that are not included in the _items
        :param _items:
        :return:
        '''
        _exclude_patterns = ["^"+item.replace(".", "\\.").replace("*", ".*")+"$" for item in _exclude_patterns]
        patterns = [re.compile(item) for item in _exclude_patterns]

        result = []
        for header in _target_list:
            # True if pattern matches  else False
            match = [ not pattern.match(header) is None for pattern in patterns]
            if any(match) is True: continue
            result.append(header)
        return result

    def __load_code(self, _file=None):
        '''
        load source code from a file
        :param _file:
        :return:
        '''
        # check parameter exceptions
        if _file is not None:
            encoding = self.__detect_encoding(_file)
            print("Encoding detected: %s"%encoding)
            with open(_file, "r", encoding=encoding) as f: text = f.read()

        if text is None: return None
        code = text.strip()
        if code == "": return None
        return code

    def __detect_encoding(self, _file):
        raw = open(_file, 'rb').read()
        if raw.startswith(codecs.BOM_UTF8):
            encoding = 'utf-8-sig'
        else:
            result = chardet.detect(raw)
            encoding = result['encoding']
        return encoding

    def __get_header_files(self, _code, _is_local=False):
        '''
        This function extracts header files that is in a source code
        Before extracting them, it removes comments.
        It also concerns the `#include` statement that satisfies the following regular expressions:
            global: ^[ \t]*#[ \t]*include[ \t]*[\<]([/\w\.]+)[\>]
            local: ^[ \t]*#[ \t]*include[ \t]*["]([/\w\.]+)["]
        :param _code:
        :param _is_local:
        :return:
        '''
        lines = _code.split('\n')

        # get header files
        headers = []
        for line in lines:
            # throw away an empty line
            line = line.strip()
            if line == "": continue

            # check whether the line matches with the pattern
            if _is_local is True:
                rex_pattern = re.compile(r"^[ \t]*#[ \t]*include[ \t]*[\"]([/\w\.]+)[\"]")
            else:
                rex_pattern = re.compile(r"^[ \t]*#[ \t]*include[ \t]*[\<]([/\w\.]+)[\>]")
            ret = rex_pattern.search(line)
            if ret is None: continue

            # add header file name
            headers.append(ret.group(1))

        return headers

    def __select_preprocessed_header_files(self, headers):
        # Only works when AST parser provided
        if self.__AST is None: return headers

        # get includes from clang after preprocessing
        clang_includes = self.__AST.get_includes()
        clang_includes = [str(include.include) for include in clang_includes]

        # select header files in using
        selected = []
        for header_file in headers:
            flag = False
            pure_header = utils.make_pure_relative_path(header_file)
            for include in clang_includes:
                if include.endswith(pure_header) is True:
                    flag = True
                    break
            if flag is True:
                selected.append(header_file)

        return selected
