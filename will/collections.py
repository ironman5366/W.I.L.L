class DictObject(dict):
    def __getattr__(self, attr):
        if attr in self:
            return self[attr]
        else:
            raise AttributeError("No such attribute: {0}".format(attr))
        
    def __setattr__(self, attr, value):
        self[attr] = value
    
    def __delattr__(self, attr):
        if attr in self:
            del self[attr]
        else:
            raise AttributeError("No such attribute: {0}".format(attr))