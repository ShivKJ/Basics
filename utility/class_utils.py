from functools import wraps
from inspect import FullArgSpec, getfullargspec


def __same_name_as_constructor(ins: FullArgSpec, *args, **kwargs):
    pos_args_names = ins.args

    obj_dict = {}
    for k, v in zip(pos_args_names[1:len(args) + 1], args):
        obj_dict[k] = v

    if ins.defaults:
        # when key_only args are not present.(* is not used)
        key_args_names = ins.args[-len(ins.defaults):]
        obj_dict.update(dict(zip(key_args_names, ins.defaults)))
        obj_dict.update(**kwargs)  # now overriding with given kwargs
    else:
        obj_dict.update(ins.kwonlydefaults)
        obj_dict.update(**kwargs)

    return obj_dict


def constructor_setter(__init__):
    @wraps(__init__)
    def f(self, *args, **kwargs):
        ins = getfullargspec(__init__)
        self.__dict__.update(__same_name_as_constructor(ins, *args, **kwargs))
        __init__(self, *args, **kwargs)

    return f