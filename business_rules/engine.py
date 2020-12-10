from .fields import FIELD_NO_INPUT


def run_all(rule_list,
            defined_variables,
            defined_actions,
            stop_on_first_trigger=False):
    rule_was_triggered = False
    for rule in rule_list:
        result = run(rule, defined_variables, defined_actions)
        if result:
            rule_was_triggered = True
            if stop_on_first_trigger:
                return True
    return rule_was_triggered


def run(rule, defined_variables, defined_actions):
    """
    Check if rule condition is met and trigger the actions accordingly
    :param rule: business rule to be checked/executed
    :param defined_variables: variables/methods that the rule logic consists of
    :param defined_actions: actions to be executed if the rule is met
    :return: boolean - whether the rule was met or not
    """
    conditions, actions = rule['conditions'], rule['actions']
    rule_triggered, override_params = check_conditions_recursively(conditions, defined_variables)
    if rule_triggered:
        do_actions(actions, defined_actions, override_params)
        return True
    return False


def check_conditions_recursively(conditions, defined_variables, override_params=None):
    """
    Recursive check of business rule variables/methods
    :param conditions: (partial) logic of the business rule to be checked
    :param defined_variables: variables/methods to be used
    :param override_params: overrides for actions' params recursively collected from variables
    :return: tuple consisting of:
        - boolean value if the rule is triggered, and
        - actions' overrides dict
    """
    override_params = override_params or {}
    keys = list(conditions.keys())
    if keys == ['all']:
        assert len(conditions['all']) >= 1
        for condition in conditions['all']:
            conditions_met, params_update = check_conditions_recursively(
                condition, defined_variables, override_params=override_params
            )
            override_params.update(params_update)
            if not conditions_met:
                return False, override_params
        return True, override_params

    elif keys == ['any']:
        assert len(conditions['any']) >= 1
        for condition in conditions['any']:
            conditions_met, params_update = check_conditions_recursively(
                condition, defined_variables, override_params=override_params
            )
            override_params.update(params_update)
            if conditions_met:
                return True, override_params
        return False, override_params

    else:
        # help prevent errors - any and all can only be in the condition dict if they're the only item
        assert not ('any' in keys or 'all' in keys)
        return check_condition(
            conditions, defined_variables, override_params=override_params
        )


def check_condition(condition, defined_variables, override_params=None):
    """
    Checks a single rule condition - the condition will be made up of variables, values and the comparison operator.
    The defined_variables object must have a variable defined for any variables in this condition.
    :param condition: logic segment of the business rule to be checked
    :param defined_variables: variables/methods to be used
    :param override_params: overrides for actions' params recursively collected from variables
    :return: tuple consisting of:
        - boolean value if the segment is triggered, and
        - partial actions' overrides dict
    """
    override_params = override_params or {}
    name, op, value, params = condition['name'], condition['operator'], condition['value'], condition.get('params', {})
    operator_type, params_update = _get_variable_value_and_actions_params(
        defined_variables, name, params
    )
    override_params.update(params_update)
    return _do_operator_comparison(operator_type, op, value), override_params


def _get_variable_value_and_actions_params(defined_variables, name, params):
    """
    Resolves the variable/method and optionally gets actions' params overrides.
    Call the function provided on the defined_variables object with the given name (
    raise exception if that doesn't exist) and casts it to the specified type.
    :param defined_variables: variables/methods to be used
    :param name: variable name
    :param params: variable params
    :return:
            - an instance of operators.BaseType
            - optional actions' params overrides
    """
    def fallback(*args, **kwargs):
        raise AssertionError(
            "Variable {0} is not defined in class {1}".format(name, defined_variables.__class__.__name__)
        )

    method = getattr(defined_variables, name, fallback)
    try:
        method_result = method(**params)
    except TypeError as ex:
        raise TypeError("Variable params object has to be of dict type! - {}".format(str(ex)))
    except KeyError as ex:
        raise KeyError("Expected params ({}) were not provided!".format(str(ex)))
    else:
        if isinstance(method_result, tuple):
            (val, override_params) = method_result
        else:
            val, override_params = method_result, None
        override_params = override_params or {}

        return method.field_type(val), override_params


def _do_operator_comparison(operator_type, operator_name, comparison_value):
    """
        Finds the method on the given operator_type and compares it to the given comparison_value.

        - operator_type should be an instance of operators.BaseType
        - comparison_value is whatever python type to compare to
        - returns a bool
    """

    def fallback(*args, **kwargs):
        raise AssertionError("Operator {0} does not exist for type {1}".format(
            operator_name, operator_type.__class__.__name__))

    method = getattr(operator_type, operator_name, fallback)
    if getattr(method, 'input_type', '') == FIELD_NO_INPUT:
        return method()
    return method(comparison_value)


def do_actions(actions, defined_actions, override_params=None):
    """
    Executes defined actions.
    :param actions: actions to be exectuted
    :param defined_actions: scope containing all relevant actions
    :param override_params: actions' params overrides coming from variables
    :return:
    """
    override_params = override_params or {}

    returned_values = None
    for action in actions:
        method_name = action['name']

        def fallback(*args, **kwargs):
            raise AssertionError("Action {0} is not defined in class {1}" \
                                 .format(method_name, defined_actions.__class__.__name__))

        params = action.get('params') or {}
        # what's the best order of the overrides?
        params.update(override_params)
        if returned_values and isinstance(returned_values, dict):
            params = {**params, **returned_values}

        method = getattr(defined_actions, method_name, fallback)
        returned_values = method(**params)
