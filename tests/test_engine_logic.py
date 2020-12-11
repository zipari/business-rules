from mock import patch, MagicMock

from business_rules import engine
from business_rules.actions import BaseActions
from business_rules.operators import StringType
from business_rules.variables import BaseVariables
from . import TestCase

OVERRIDE_NONE = dict()
OVERRIDE_A1 = dict(a=1)
OVERRIDE_B2 = dict(b=2)
OVERRIDE_C3 = dict(c=3)
OVERRIDE_C4 = dict(c=4)
T_NO_OVERRIDES = (True, OVERRIDE_NONE)
F_NO_OVERRIDES = (False, OVERRIDE_NONE)
T_WITH_OVERRIDES = (True, OVERRIDE_A1)
F_WITH_OVERRIDES = (False, OVERRIDE_A1)
FAKE_OPERATOR = MagicMock()


class EngineTests(TestCase):

    # Run
    @patch.object(engine, 'run')
    def test_run_all_some_rule_triggered(self, *args):
        """
            By default, does not stop on first triggered rule.
            Returns True if any rule was triggered, otherwise False
        """
        rule1 = {
            'conditions': 'condition1',
            'actions': 'action name 1'
        }
        rule2 = {
            'conditions': 'condition2',
            'actions': 'action name 2'
        }
        variables = BaseVariables()
        actions = BaseActions()

        def return_action1(rule, *args, **kwargs):
            return rule['actions'] == 'action name 1'

        engine.run.side_effect = return_action1

        result = engine.run_all([rule1, rule2], variables, actions)
        self.assertTrue(result)
        self.assertEqual(engine.run.call_count, 2)

        # switch order and try again
        engine.run.reset_mock()

        result = engine.run_all([rule2, rule1], variables, actions)
        self.assertTrue(result)
        self.assertEqual(engine.run.call_count, 2)

    @patch.object(engine, 'run', return_value=True)
    def test_run_all_stop_on_first(self, *args):
        rule1 = {
            'conditions': 'condition1',
            'actions': 'action name 1'
        }
        rule2 = {
            'conditions': 'condition2',
            'actions': 'action name 2'
        }
        variables = BaseVariables()
        actions = BaseActions()

        result = engine.run_all([rule1, rule2], variables, actions, stop_on_first_trigger=True)
        self.assertEqual(result, True)
        self.assertEqual(engine.run.call_count, 1)
        engine.run.assert_called_once_with(rule1, variables, actions)

    @patch.object(engine, 'check_conditions_recursively', return_value=T_WITH_OVERRIDES)
    @patch.object(engine, 'do_actions')
    def test_run_that_triggers_rule_with_overrides(self, *args):
        rule = {
            'conditions': 'blah',
            'actions': 'blah2'
        }
        variables = BaseVariables()
        actions = BaseActions()

        result = engine.run(rule, variables, actions)
        self.assertEqual(result, True)
        engine.check_conditions_recursively.assert_called_once_with(
            rule['conditions'], variables
        )
        engine.do_actions.assert_called_once_with(rule['actions'],
                                                  actions,
                                                  override_params=OVERRIDE_A1)

    @patch.object(engine, 'check_conditions_recursively', return_value=F_NO_OVERRIDES)
    @patch.object(engine, 'do_actions')
    def test_run_that_doesnt_trigger_rule(self, *args):
        rule = {
            'conditions': 'blah',
            'actions': 'blah2'
        }
        variables = BaseVariables()
        actions = BaseActions()

        result = engine.run(rule, variables, actions)
        self.assertEqual(result, False)
        engine.check_conditions_recursively.assert_called_once_with(
            rule['conditions'], variables
        )
        self.assertEqual(engine.do_actions.call_count, 0)

    # Check conditions recursively
    @patch.object(engine, 'check_condition', return_value=T_NO_OVERRIDES)
    def test_check_all_conditions_with_all_true(self, *args):
        conditions = {
            'all': [
                {'thing1': ''},
                {'thing2': ''}
            ]
        }
        variables = BaseVariables()

        result = engine.check_conditions_recursively(conditions, variables)
        self.assertEqual(result, T_NO_OVERRIDES)
        # assert call count and most recent call are as expected
        self.assertEqual(engine.check_condition.call_count, 2)
        engine.check_condition.assert_called_with({'thing2': ''},
                                                  variables,
                                                  override_params=OVERRIDE_NONE)

    @patch.object(engine, 'check_condition', return_value=F_NO_OVERRIDES)
    def test_check_all_conditions_with_all_false(self, *args):
        conditions = {
            'all': [
                {'thing1': ''},
                {'thing2': ''}
            ]
        }
        variables = BaseVariables()

        result = engine.check_conditions_recursively(conditions, variables)
        self.assertEqual(result, F_NO_OVERRIDES)
        engine.check_condition.assert_called_once_with({'thing1': ''},
                                                       variables,
                                                       override_params=OVERRIDE_NONE)

    def test_check_all_condition_with_no_items_fails(self):
        with self.assertRaises(AssertionError):
            engine.check_conditions_recursively({'all': []}, BaseVariables())

    @patch.object(engine, 'check_condition', return_value=T_NO_OVERRIDES)
    def test_check_any_conditions_with_all_true(self, *args):
        conditions = {
            'any': [
                {'thing1': ''},
                {'thing2': ''}
            ]
        }
        variables = BaseVariables()

        result = engine.check_conditions_recursively(conditions, variables)
        self.assertEqual(result, T_NO_OVERRIDES)
        engine.check_condition.assert_called_once_with({'thing1': ''},
                                                       variables,
                                                       override_params=OVERRIDE_NONE)

    @patch.object(engine, 'check_condition', return_value=F_NO_OVERRIDES)
    def test_check_any_conditions_with_all_false(self, *args):
        conditions = {
            'any': [
                {'thing1': ''},
                {'thing2': ''}
            ]
        }
        variables = BaseVariables()

        result = engine.check_conditions_recursively(conditions, variables)
        self.assertEqual(result, F_NO_OVERRIDES)
        # assert call count and most recent call are as expected
        self.assertEqual(engine.check_condition.call_count, 2)
        engine.check_condition.assert_called_with({'thing2': ''},
                                                  variables,
                                                  override_params=OVERRIDE_NONE)

    def test_check_any_condition_with_no_items_fails(self):
        with self.assertRaises(AssertionError):
            engine.check_conditions_recursively({'any': []}, BaseVariables())

    def test_check_all_and_any_together(self):
        conditions = {
            'any': [],
            'all': []
        }
        variables = BaseVariables()
        with self.assertRaises(AssertionError):
            engine.check_conditions_recursively(conditions, variables)

    @patch.object(engine, 'check_condition')
    def test_nested_all_and_any(self, *args):
        conditions = {
            'all': [
                {
                    'any': [
                        {'name': 1},
                        {'name': 2}
                    ]
                },
                {'name': 3}
            ]
        }
        bv = BaseVariables()

        def side_effect(condition, _, **kwargs):
            condition_check = condition['name'] in [2, 3]
            return condition_check, {}

        engine.check_condition.side_effect = side_effect

        engine.check_conditions_recursively(conditions, bv)
        self.assertEqual(engine.check_condition.call_count, 3)
        engine.check_condition.assert_any_call({'name': 1},
                                               bv,
                                               override_params=OVERRIDE_NONE)
        engine.check_condition.assert_any_call({'name': 2},
                                               bv,
                                               override_params=OVERRIDE_NONE)
        engine.check_condition.assert_any_call({'name': 3},
                                               bv,
                                               override_params=OVERRIDE_NONE)

    @patch.object(engine, 'check_condition')
    def test_recursive_overrides_collect_unique(self, *args):
        conditions = {
            'all': [
                {'name': 1},
                {'name': 2}
            ]
        }
        bv = BaseVariables()

        def side_effect(condition, _, **kwargs):
            if condition['name'] == 1:
                return True, OVERRIDE_A1
            elif condition['name'] == 2:
                return True, OVERRIDE_B2

        engine.check_condition.side_effect = side_effect

        result, overrides = engine.check_conditions_recursively(conditions, bv)
        self.assertEqual(engine.check_condition.call_count, 2)
        engine.check_condition.assert_any_call({'name': 1},
                                               bv,
                                               override_params=OVERRIDE_NONE)
        engine.check_condition.assert_any_call({'name': 2},
                                               bv,
                                               override_params=OVERRIDE_A1)
        self.assertTrue(result)
        self.assertDictEqual(overrides, {**OVERRIDE_A1, **OVERRIDE_B2})

    @patch.object(engine, 'check_condition')
    def test_recursive_overrides_collect_repeated(self, *args):
        conditions = {
            'all': [
                {'name': 1},
                {'name': 2}
            ]
        }
        bv = BaseVariables()

        def side_effect(condition, _, **kwargs):
            if condition['name'] == 1:
                return True, OVERRIDE_C3
            elif condition['name'] == 2:
                return True, OVERRIDE_C4

        engine.check_condition.side_effect = side_effect

        result, overrides = engine.check_conditions_recursively(conditions, bv)
        self.assertEqual(engine.check_condition.call_count, 2)
        engine.check_condition.assert_any_call({'name': 1},
                                               bv,
                                               override_params=OVERRIDE_NONE)
        engine.check_condition.assert_any_call({'name': 2},
                                               bv,
                                               override_params=OVERRIDE_C3)
        self.assertTrue(result)
        self.assertDictEqual(overrides, OVERRIDE_C4)

    # Check condition
    @patch.object(engine, '_get_variable_value_and_actions_params', return_value=(FAKE_OPERATOR, OVERRIDE_A1))
    @patch.object(engine, '_do_operator_comparison', return_value=True)
    def test_check_condition_no_override(self, *args):
        condition = {
            'name': 'name_x',
            'operator': 'operator_x',
            'value': 'value_x'
        }
        variables = BaseVariables()

        result, overrides = engine.check_condition(condition, variables)
        self.assertEqual(engine._get_variable_value_and_actions_params.call_count, 1)
        self.assertEqual(engine._do_operator_comparison.call_count, 1)
        engine._get_variable_value_and_actions_params.assert_called_with(variables,
                                                                         'name_x',
                                                                         OVERRIDE_NONE)
        engine._do_operator_comparison.assert_called_with(FAKE_OPERATOR,
                                                          'operator_x',
                                                          'value_x')
        self.assertTrue(result)
        self.assertDictEqual(overrides, OVERRIDE_A1)

    @patch.object(engine, '_get_variable_value_and_actions_params', return_value=(FAKE_OPERATOR, OVERRIDE_A1))
    @patch.object(engine, '_do_operator_comparison', return_value=True)
    def test_check_condition_with_override(self, *args):
        condition = {
            'name': 'name_x',
            'operator': 'operator_x',
            'value': 'value_x',
            'params': OVERRIDE_NONE
        }
        variables = BaseVariables()

        result, overrides = engine.check_condition(condition, variables, override_params=OVERRIDE_B2)
        self.assertEqual(engine._get_variable_value_and_actions_params.call_count, 1)
        self.assertEqual(engine._do_operator_comparison.call_count, 1)
        engine._get_variable_value_and_actions_params.assert_called_with(variables,
                                                                         'name_x',
                                                                         OVERRIDE_NONE)
        engine._do_operator_comparison.assert_called_with(FAKE_OPERATOR,
                                                          'operator_x',
                                                          'value_x')
        self.assertTrue(result)
        self.assertDictEqual(overrides, {**OVERRIDE_A1, **OVERRIDE_B2})

    # Operator comparisons
    def test_check_operator_comparison(self):
        string_type = StringType('yo yo')
        with patch.object(string_type, 'contains', return_value=True):
            result = engine._do_operator_comparison(
                string_type, 'contains', 'its mocked'
            )
            self.assertTrue(result)
            string_type.contains.assert_called_once_with('its mocked')

    # Actions
    def test_do_actions(self):
        actions = [
            {
                'name': 'action1'
            },
            {
                'name': 'action2',
                'params': {
                    'param1': 'foo',
                    'param2': 10
                }
            }
        ]

        defined_actions = BaseActions()
        defined_actions.action1 = MagicMock()
        defined_actions.action2 = MagicMock()

        engine.do_actions(actions, defined_actions)
        defined_actions.action1.assert_called_once_with()
        defined_actions.action2.assert_called_once_with(param1='foo', param2=10)

    def test_do_actions_with_override(self):
        actions = [
            {
                'name': 'action',
                'params': {
                    'param': 'foo',
                }
            }
        ]
        override_params = {
            'param': 'bar'
        }
        defined_actions = BaseActions()
        defined_actions.action = MagicMock()

        engine.do_actions(actions, defined_actions, override_params=override_params)
        defined_actions.action.assert_called_once_with(param='bar')

    def test_do_with_invalid_action(self):
        actions = [
            {'name': 'fakeone'}
        ]
        err_string = "Action fakeone is not defined in class BaseActions"
        with self.assertRaisesRegexp(AssertionError, err_string):
            engine.do_actions(actions, BaseActions())

    def test_do_actions_with_returned_values(self):
        actions = [{'name': 'action1'},
                   {'name': 'action2', 'params': {'param1': 'foo', 'param2': 10}},
                   {'name': 'action3', 'params': {'param1': 'baz'}},
                   {'name': 'action4', 'params': {'param1': 'old'}}]
        defined_actions = BaseActions()
        defined_actions.action1 = MagicMock(return_value={'param3': 'bar'})
        defined_actions.action2 = MagicMock(return_value=[1, 2, 3])
        defined_actions.action3 = MagicMock(return_value={'param1': 'new'})
        defined_actions.action4 = MagicMock()

        engine.do_actions(actions, defined_actions)

        defined_actions.action1.assert_called_once_with()
        # action result of dict type gets merged into params
        defined_actions.action2.assert_called_once_with(param1='foo', param2=10, param3='bar')
        # action result of non-dict type doesn't get merged into params
        defined_actions.action3.assert_called_once_with(param1='baz')
        # action result overrides params of the following action
        defined_actions.action4.assert_called_once_with(param1='new')
