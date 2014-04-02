from business_rules.variables import rule_variable, TYPE_STRING, TYPE_NUMERIC
from business_rules.utils import fn_name_to_pretty_description

from unittest import TestCase

class RuleVariableTests(TestCase):
    """ Tests for the base rule_variable decorator.
    """

    def test_pretty_description(self):
        self.assertEqual(
                fn_name_to_pretty_description('some_name_Of_a_thing'),
                'Some Name Of A Thing')
        self.assertEqual(fn_name_to_pretty_description('hi'), 'Hi')

    def test_rule_variable_decorator_internals(self):
        """ Make sure that the expected attributes are attached to a function
        by the variable decorators.
        """
        def some_test_function(self): pass
        wrapper = rule_variable(TYPE_STRING, 'Foo Name', options=['op1', 'op2'])
        func = wrapper(some_test_function)
        self.assertTrue(func.is_rule_variable)
        self.assertEqual(func.description, 'Foo Name')
        self.assertEqual(func.return_type, TYPE_STRING)
        self.assertEqual(func.options, ['op1', 'op2'])

    def test_rule_variable_works_as_decorator(self):
        @rule_variable(TYPE_STRING, 'Blah')
        def some_test_function(self): pass
        self.assertTrue(some_test_function.is_rule_variable)

    def test_rule_variable_decorator_auto_fills_description(self):
        @rule_variable(TYPE_STRING)
        def some_test_function(self): pass
        self.assertTrue(some_test_function.description, 'Some Test Function')

    def test_rule_variable_decorator_caches_value(self):
        foo = 1
        @rule_variable(TYPE_NUMERIC)
        def foo_func():
            return foo
        self.assertEqual(foo_func(), 1)
        foo = 2
        self.assertEqual(foo_func(), 1)