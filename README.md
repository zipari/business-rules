business-rules
==============

[![Build Status](https://travis-ci.org/venmo/business-rules.svg?branch=master)](https://travis-ci.org/venmo/business-rules)

As a software system grows in complexity and usage, it can become burdensome if
every change to the logic/behavior of the system also requires you to write and
deploy new code. The goal of this business rules engine is to provide a simple
interface allowing anyone to capture new rules and logic defining the behavior
of a system, and a way to then process those rules on the backend.

You might, for example, find this is a useful way for analysts to define
marketing logic around when certain customers or items are eligible for a
discount or to automate emails after users enter a certain state or go through
a particular sequence of events.

## Usage

### 1. Define Your set of variables

Variables represent values in your system, usually the value of some particular object.  You create rules by setting threshold conditions such that when a variable is computed that triggers the condition some action is taken.

You define all the available variables for a certain kind of object in your code, and then dynamically set the conditions and thresholds for those.

For example:

```python
class ProductVariables(BaseVariables):

    def __init__(self, product):
        self.product = product

    @numeric_rule_variable
    def current_inventory(self):
        return self.product.current_inventory

    @boolean_rule_variable(params={'limit': FIELD_NUMERIC})
    def current_inventory_over_limit(self, limit):
        """
        This docstring will become a tooltip! But just the first line!
        :param limit: integer; inventory limit
        :return: boolean;
        """
        return self.product.current_inventory > limit

    @numeric_rule_variable(label='Days until expiration')
    def expiration_days(self)
        last_order = self.product.orders[-1]
        return (last_order.expiration_date - datetime.date.today()).days

    @string_rule_variable()
    def current_month(self):
        return datetime.datetime.now().strftime("%B")

    @select_rule_variable(options=Products.top_holiday_items())
    def goes_well_with(self):
        return products.related_products
```

A variable can return a value of a specific type (`FIELD_TEXT`, `FIELD_NUMERIC`, `FIELD_NO_INPUT`, `FIELD_SELECT`, `FIELD_SELECT_MULTIPLE`, `FIELD_DATE`) as shown above, or a tuple, where the first element of a tuple will again be a variable, and the second element will be a dictionary of actions' parameters overrides. This dictionary will be passed to all of the triggered actions, providing an opportunity to actions to respond in a dynamic manner. Variable type is still co-related to the returned value.

For example:

```python
class ProductVariables(BaseVariables):

    def __init__(self, products):
        self.products = products

    @boolean_rule_variable(params={'product_index': FIELD_NUMERIC, 'threshold': FIELD_NUMERIC}
    def product_inventory_spot_check(self, product_index, threshold):
        selected_product = self.products[product_index]
        product_under_threshold = selected_product.current_inventory < threshold
        return product_under_threshold, {'selected_product': selected_product.name}
```

### 2. Define your set of actions

These are the actions that are available to be taken when a condition is triggered.

For example:

```python
class ProductActions(BaseActions):

    def __init__(self, product):
        self.product = product

    @rule_action(params={"sale_percentage": FIELD_NUMERIC})
    def put_on_sale(self, sale_percentage, **kwargs):
        """
        Actions too can have docstrings!
        """
        self.product.price = (1.0 - sale_percentage) * self.product.price
        self.product.save()

    @rule_action(params={"number_to_order": FIELD_NUMERIC})
    def order_more(self, number_to_order, **kwargs):
        ProductOrder.objects.create(product_id=self.product.id,
                                    quantity=number_to_order)
```

If you need a select field for an action parameter, another -more verbose- syntax is available:

```python
class ProductActions(BaseActions):

    def __init__(self, product):
        self.product = product

    @rule_action(
        params=[
            {
                'fieldType': FIELD_SELECT,
                'name': 'stock_state',
                'label': 'Stock state',
                'options': [
                    {'label': 'Available', 'name': 'available'},
                    {'label': 'Last items', 'name': 'last_items'},
                    {'label': 'Out of stock', 'name': 'out_of_stock'}
                ]
            }
        ]
    )
    def change_stock_state(self, stock_state, **kwargs):
        self.product.stock_state = stock_state
        self.product.save()
```

As you might have noticed, for every action defined it is a must to have its signature end with `**kwargs`. This is because, as we explained, variables can send an arbitrary parameters to it.

For example (following `product_inventory_spot_check` variable):

```python
class ProductActions(BaseActions):
    ...

    @rule_action()
    def low_on_product_exception(self, **kwargs):
        product = kwargs.get('selected_product', '<name not available>')
        msg = 'Low on product {}!'.format(product)
        raise Exception(msg)
```

Additionally, one action can pass parameters overrides to the subsequent ones.

For example:

```python
class ProductActions(BaseActions):
    ...

    @rule_action()
    def some_action(self, **kwargs):
        return {'foo': 'bar'}
```

In this case, any action following `some_action` will receive `{'foo': 'bar'}` as a part of its `kwargs`. The requrement is that the action response is of a `dict` type.

The order of precedence of action parameters overrides is (lowest to highest):
 * action defined parameter
 * parameter override provided by variable
 * parameter override provided by action

### 3. Build the rules

A rule is just a JSON object that gets interpreted by the business-rules engine.

Note that the JSON is expected to be auto-generated by a UI, which makes it simple for anyone to set and tweak business rules without knowing anything about the code.  The javascript library used for generating these on the web can be found [here](https://github.com/venmo/business-rules-ui).

An example of the resulting python lists/dicts is:

```python
rules = [
    # expiration_days < 5 AND current_inventory > 20
    {
        "conditions": {
            "all": [
                {
                    "name": "expiration_days",
                    "operator": "less_than",
                    "value": 5,
                },
                {
                    "name": "current_inventory",
                    "operator": "greater_than",
                    "value": 20,
                },
            ]
        },
        "actions": [
            {
                "name": "put_on_sale",
                "params": {
                    "sale_percentage": 0.25
                },
            },
        ],
    },

    # current_inventory < 5 OR (current_month = "December" AND current_inventory < 20)
    {
        "conditions": {
            "any": [
                {
                    "name": "current_inventory",
                    "operator": "less_than",
                    "value": 5,
                },
                {
                    "all": [
                        {
                            "name": "current_month",
                            "operator": "equal_to",
                            "value": "December",
                        },
                        {
                            "name": "current_inventory",
                            "operator": "less_than",
                            "value": 20,
                        }
                    ]
                }
            ]
        },
        "actions": [
            {
                "name": "order_more",
                "params": {
                    "number_to_order": 40
                }
            },
        ],
    }
]
```

### Export the available variables, operators and actions

To e.g. send to your client so it knows how to build rules

```python
from business_rules import export_rule_data
export_rule_data(ProductVariables, ProductActions)
```

that returns

```python
{
    "variables": [
        {
            "name": "expiration_days",
            "label": "Days until expiration",
            "field_type": "numeric",
            "options": [],
            "params": {},
            "tooltip": ""
        },
        {
            "name": "current_inventory_over_limit",
            "label": "",
            "field_type": "boolean",
            "options": [],
            "params": {
                "limit": "numeric"
            },
            "tooltip": "This docstring will become a tooltip! But just the first line!"
        },
        {
            "name": "current_month",
            "label": "Current Month",
            "field_type": "string",
            "options": [],
            "params": {},
            "tooltip": ""
        },
        {
            "name": "goes_well_with",
            "label": "Goes Well With",
            "field_type": "select",
            "options": ["Eggnog", "Cookies", "Beef Jerkey"],
            "params": {},
            "tooltip": ""
        }
    ],
    "actions": [
        {
            "name": "put_on_sale",
            "label": "Put On Sale",
            "params": {"sale_percentage": "numeric"},
            "tooltip": ""
        },
        {
            "name": "order_more",
            "label": "Order More",
            "params": {"number_to_order": "numeric"},
            "tooltip": ""
        }
    ],
    "variable_type_operators": {
        "numeric": [
            {
                "name": "equal_to",
                "label": "Equal To",
                "input_type": "numeric"
            },
            {
                "name": "not_equal_to",
                "label": "Not Equal To",
                "input_type": "numeric"
            },
            {
                "name": "less_than",
                "label": "Less Than",
                "input_type": "numeric"
            },
            {
                "name": "greater_than",
                "label": "Greater Than",
                "input_type": "numeric"
            }
        ],
        "string": [
            {
                "name": "equal_to",
                "label": "Equal To",
                "input_type": "text"
            },
            {
                "name": "not_equal_to",
                "label": "Not Equal To",
                "input_type": "text"
            },
            {
                "name": "non_empty",
                "label": "Non Empty",
                "input_type": "none"
            }
        ]
    }
}
```

### Run your rules

Run all of the defined rules using `run_all` or just a specific one using `run`:

```python
from business_rules import run, run_all

rules = _some_function_to_receive_from_client()
first_rule = rules[0]

for product in Products.objects.all():
    run_all(rule_list=rules,
            defined_variables=ProductVariables(product),
            defined_actions=ProductActions(product),
            stop_on_first_trigger=True)

product = Products.objects.first()
run(first_rule, ProductVariables(product), ProductActions(product))

```

## API

#### Variable Types and Decorators:

The type represents the type of the value that will be returned for the variable and is necessary since there are different available comparison operators for different types, and the front-end that's generating the rules needs to know which operators are available.

All decorators can optionally take a label:
- `label` - A human-readable label to show on the frontend. By default we just split the variable name on underscores and capitalize the words.

The available types and decorators are:

**numeric** - an integer, float, or python Decimal.

`@numeric_rule_variable` operators:

* `equal_to`
* `not_equal_to`
* `greater_than`
* `less_than`
* `greater_than_or_equal_to`
* `less_than_or_equal_to`

Note: to compare floating point equality we just check that the difference is less than some small epsilon

**string** - a python bytestring or unicode string.

`@string_rule_variable` operators:

* `equal_to`
* `not_equal_to`
* `starts_with`
* `ends_with`
* `contains`
* `matches_regex`
* `non_empty`

**boolean** - a True or False value.

`@boolean_rule_variable` operators:

* `is_true`
* `is_false`

**select** - a set of values, where the threshold will be a single item.

`@select_rule_variable` operators:

* `contains`
* `does_not_contain`

**select_multiple** - a set of values, where the threshold will be a set of items.

`@select_multiple_rule_variable` operators:

* `contains_all`
* `is_contained_by`
* `shares_at_least_one_element_with`
* `shares_exactly_one_element_with`
* `shares_no_elements_with`

**date** - a date value.

`@date_rule_variable` operators:

* `equal_to`
* `not_equal_to`
* `greater_than`
* `less_than`
* `greater_than_or_equal_to`
* `less_than_or_equal_to`


## Make virtual environment and run the tests using tox

From the base directory run:

```bash
$ tox -r
```


## Contributing

Open up a pull request, making sure to add tests for any new functionality. To set up the dev environment (assuming you're using [virtualenvwrapper](http://docs.python-guide.org/en/latest/dev/virtualenvs/#virtualenvwrapper)):

```bash
$ mkvirtualenv business-rules
$ pip install -r dev-requirements.txt
$ nosetests
```
