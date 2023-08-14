##################################################
# Makes a dict object appear like a class
##################################################
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(self, attr):
        if attr not in self:
            raise AttributeError("Cannot find the attribute " + attr)
        return self.get(attr)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def is_empty(self, _attribute):
        if _attribute not in self: return True
        if self[_attribute] is None: return True
        if self[_attribute] == "": return True
        return False

    def has_value(self, _attribute):
        if _attribute not in self: return False
        if self[_attribute] is None: return False
        if self[_attribute] == "": return False
        return True

    def to_dict(self):
        '''
        convert member variables into the primitive dict()
        :return:
        '''
        d = dict()
        for key, value in self.items():
            d[key] = value
        return d
