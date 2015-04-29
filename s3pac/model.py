from datetime import datetime

class Property:
    def __init__(self, default, multiple=False):
        self.default = default if not multiple else []
        self.multiple = multiple

class LongProperty(Property):
    def __init__(self, default=0, multiple=False):
        super().__init__(default, multiple)

class StringProperty(Property):
    def __init__(self, default="", multiple=False):
        super().__init__(default, multiple)

class DateTimeProperty(Property):
    def __init__(self, default=datetime.utcfromtimestamp(0), multiple=False):
        super().__init__(default, multiple)

class ModelType(type):
    def __init__(_class, name, bases, dct):
        propnames = [propname for propname, prop \
                              in _class.__dict__.items() \
                              if isinstance(prop, Property)]
        _class.__model_properties__ = propnames

class Model(metaclass=ModelType):
    def __init__(self, **kwargs):
        _class = self.__class__
        for name in _class.__model_properties__:
            prop = getattr(_class, name)
            value = kwargs.get(name, prop.default)
            setattr(self, name, value)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.__dict__)

    @classmethod
    def convertdict(_class, convs, _dict):
        result = {}
        for name in _class.__model_properties__:
            if name not in _dict:
                continue
            prop = getattr(_class, name)
            value = _dict.get(name)
            conv = convs.get(prop.__class__, lambda v: v)
            if prop.multiple:
                if isinstance(value, list):
                    result[name] = list(map(conv, value))
                else:
                    result[name] = [conv(value)]
            else:
                if isinstance(value, list):
                    result[name] = conv(value[0])
                else:
                    result[name] = conv(value)
        return result

    @classmethod
    def load(_class, convs, _dict):
        return _class(**_class.convertdict(convs, _dict))

    @classmethod
    def store(_class, convs, model):
        return _class.convertdict(convs, model.__dict__)
