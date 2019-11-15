import inspect

from .utils import fn_name_to_pretty_label, validate_parameters


class BaseActions(object):
    """ Classes that hold a collection of actions to use with the rules engine should inherit from this. """

    @classmethod
    def get_all_actions(cls):
        methods = inspect.getmembers(cls)
        return [{'name': m[0],
                 'label': m[1].label,
                 'params': m[1].params
                 } for m in methods if getattr(m[1], 'is_rule_action', False)]


def rule_action(label=None, params=None):
    """ Decorator to make a function into a rule action. """

    def wrapper(func):
        params_ = params
        if isinstance(params, dict):
            params_ = [dict(label=fn_name_to_pretty_label(name),
                            name=name,
                            fieldType=field_type) for name, field_type in params.items()]
        validate_parameters(func, params_, 'action')
        func.is_rule_action = True
        func.label = label or fn_name_to_pretty_label(func.__name__)
        func.params = params_
        return func

    return wrapper
