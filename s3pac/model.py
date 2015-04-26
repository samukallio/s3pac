from datetime import datetime

_NOCONV = (lambda v: v, lambda v: v)

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
    def __init__(self):
        _class = self.__class__
        for name in _class.__model_properties__:
            prop = getattr(_class, name)
            setattr(self, name, prop.default)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.__dict__)

    @classmethod
    def to_dict(cls, model, convs):
        if not isinstance(model, cls):
            raise TypeError("must be a %s instance" % cls.__name__)
        _dict = {}
        for name in cls.__model_properties__:
            prop = getattr(cls, name)
            value = getattr(model, name, prop.default)
            conv, _ = convs.get(prop.__class__, _NOCONV)
            if prop.multiple:
                _dict[name] = list(map(conv, value))
            else:
                _dict[name] = conv(value)
        return _dict

    @classmethod
    def from_dict(cls, _dict, convs):
        model = cls()
        for name in cls.__model_properties__:
            prop = getattr(cls, name)
            value = _dict.get(name, prop.default)
            _, conv = convs.get(prop.__class__, _NOCONV)
            if prop.multiple:
                if isinstance(value, list):
                    setattr(model, name, list(map(conv, value)))
                else:
                    setattr(model, name, [conv(value)])
            else:
                setattr(model, name, conv(value))
        return model
