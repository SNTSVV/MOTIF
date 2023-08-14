#! /usr/bin/env python3
import re

class C_NODE(object):
    '''
    data class containing a node info of the c code (type, offsets, parent, and children)
    '''
    name = None
    start = {'line':0,  'offset':0}
    end = {'line':0,  'offset':0}
    children = []
    type='ITEM'
    parent = None

    def __init__(self, _name:str, _line:int, _offset:int, _end_line:int=None, _end_offset=None, _child:object=None, _isblock:bool=False):
        self.name = _name
        self.start = {'line': _line,  'offset': _offset}
        self.end = {'line':0,  'offset':0}
        self.children = []
        self.parent = None
        self.type = 'ITEM' if _isblock is False else 'BLOCK'

        if _end_line is not None:
            self.end['line'] = _end_line
        if _end_offset is not None:
            self.end['offset'] = _end_offset
        if _child is not None:
            self.add_child(_child)
        pass

    def update_end(self, _line:int, _offset:int):
        self.end['line'] = _line
        self.end['offset'] = _offset

        if self.parent.type == "BLOCK":
            self.parent.end['line'] = _line
            self.parent.end['offset'] = _offset

    def add_child(self, _child:object):
        _child.parent = self
        self.children.append(_child)

    def add_child_to_parent(self, _child:object):
        if self.parent is not None and self.parent.type == 'BLOCK':
            self.parent.add_child(_child)

    def get_child(self, _idx):
        if len(self.children) == 0: return None
        return self.children[_idx]

    def get_last_child(self):
        return self.get_child(-1)

    def get_item_parent(self):
        if self.parent.type == 'BLOCK':
            return self.parent.parent
        return self.parent

    def __repr__(self):
        return '%s (start: {line: %d, offset: %d}, end: {line: %d, offset: %d}, children: %d)' % (
            self.name,
            self.start['line'], self.start['offset'],
            self.end['line'], self.end['offset'],
            len(self.children)
        )

    def print(self, _item=None, _level=0):
        if _item is None: _item = self

        pad = '\t' * _level
        print("%s%s" % (pad, _item))
        for item in _item.children:
            self.print(item, _level+1)


class LineOffsets():
    '''
    Get code line information (length of the line
    '''
    line_offsets = []

    def __init__(self, _code:str):
        # make line info
        self.line_offsets = []
        self.__make_line_offsets(_code)

    def __make_line_offsets(self, _code:str):
        lines = _code.split('\n')
        offset = 0
        for line in lines:
            self.line_offsets.append(offset)
            offset += len(line) + 1
        return True

    def line(self, _offset:int):
        lineno = 0
        for loffset in self.line_offsets:
            if _offset < loffset: break
            lineno += 1
        return lineno

    def offset(self, _line_no:int):
        return self.line_offsets[_line_no-1]

    def lines(self):
        return len(self.line_offsets)

    def __len__(self):
        return len(self.line_offsets)

    def __iter__(self):
        return self.line_offsets

    def __getitem__(self, item):
        return self.line_offsets[item]


class CommentsParser():
    '''
    Parsing comments and remove (but the original string is not changed)
    '''

    # List of source codes: contains all the source codes for this class
    code = None
    doc = None
    line_offsets = None

    def __init__(self, _code):
        self.code = _code
        self.line_offsets = LineOffsets(self.code)

        self.doc = C_NODE('DOC', 1, 0, _end_line=len(self.line_offsets), _end_offset=len(self.code)-1)

    def parse(self):
        # parse multi-line comments
        lastIdx = 0
        while True:
            start, end = self.__find_multi_comment(self.code, lastIdx)
            if start == -1: break
            # self.code = self.code[:start] + self.code[end+1:]
            start_line = self.line_offsets.line(start)
            end_line = self.line_offsets.line(end)
            node = C_NODE('COMMENT', start_line, start, end_line, end)
            self.__replace_code_with_pad(node, _pad=" ")
            self.doc.add_child(node)
            lastIdx = end+1

        # parse single line comments
        lines = self.code.split("\n")
        for idx in range(0,len(lines)):
            start = self.__find_line_comment(lines[idx])
            if start==-1: continue
            start = self.line_offsets[idx] + start
            if len(self.line_offsets)-1 > idx:
                end = self.line_offsets[idx+1] - 1
            else:
                end = self.line_offsets[idx]+len(lines[idx]) - 1

            node = C_NODE('LINE_COMMENT', idx+1, start, idx+1, end)
            self.__replace_code_with_pad(node, _pad=" ")
            self.doc.add_child(node)

        return self

    def __replace_code_with_pad(self, _node:C_NODE, _pad:str):
        start = _node.start['offset']
        end = _node.end['offset']

        letters = list(self.code)
        for idx in range(start, end+1):
            if letters[idx] == '\n':continue
            letters[idx] = _pad
        self.code = "".join(letters)

    def __find_multi_comment(self, _str, _start=0):
        idx = _start
        flag_str = False
        begin = -1
        end = -1
        while idx<len(_str):
            if begin < 0 and _str[idx]=="\"":  # if not in a multi comment and start a string..up flag
                flag_str = not flag_str
            elif flag_str is False and _str[idx] == "/" and _str[idx+1] == "*":
                begin = idx
                idx += 1
            elif begin >= 0 and _str[idx] == "*" and _str[idx+1] == "/":
                end = idx+1
                break
            idx += 1
        return begin, end

    def __find_line_comment(self, _str):
        idx = 0
        flag_str = False
        point = -1
        while idx<len(_str):
            if _str[idx] == "\"":  # if not in a line comment and start a string => up flag
                flag_str = not flag_str
            elif flag_str is False and _str[idx] == "/" and _str[idx+1] == "/":
                point = idx
                break
            idx += 1
        return point


class DirectiveParser():
    code = None
    line_offsets = None
    doc = None

    def __init__(self, _code):
        # self.code = _code
        self.code = CommentsParser(_code).parse().code
        self.line_offsets = LineOffsets(_code)

        # initialize
        self.doc = C_NODE('DOC', 1, 0, _end_line=len(self.line_offsets), _end_offset=len(self.code))

    def parse(self):
        # define regex for search
        rex_full = re.compile(r'#(if|ifdef|ifndef|elif|elseif|else|endif)[ \t\n]')
        rex_start = re.compile(r'#(if|ifdef|ifndef)')
        rex_else = re.compile(r'#(elif|elseif|else)')
        rex_end = re.compile(r'#endif')

        # create doc
        search_idx = 0
        cur_node = self.doc
        while True:
            match = rex_full.search(self.code, search_idx)
            if match is None: break

            # obtain info
            keyword = match.group().strip()
            offset, end_offset = match.regs[0]
            line = self.line_offsets.line(offset)
            search_idx = end_offset

            # print("search keyword: %s"% keyword)
            # make tree of directives
            if rex_start.match(keyword):
                # create IFBLOCK and add keyword
                node = C_NODE(keyword, line, offset)
                block_node = C_NODE('IFBLOCK', line, offset, _child=node, _isblock=True)
                cur_node.add_child(block_node)
                cur_node = node
            elif rex_else.match(keyword):
                # update current keyword
                cur_node.update_end(line-1 if self.code[offset-1] == '\n' else line, offset)
                # add keyword to the current IFBLOCK
                node = C_NODE(keyword, line, offset)
                cur_node.add_child_to_parent(node)
                cur_node = node
            elif rex_end.match(keyword):
                # update current keyword
                cur_node.update_end(line-1 if self.code[offset-1] == '\n' else line, offset)
                # the current IFBLOCK
                cur_node.update_end(line, offset)
                cur_node = cur_node.get_item_parent()

        if cur_node != self.doc:
            self.doc.print()
            print("ERROR: unfinished block")
            exit(1)
        return self
