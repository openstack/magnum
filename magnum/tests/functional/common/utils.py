# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from collections import abc
import functools
import inspect
import time
import types


def def_method(f, *args, **kwargs):
    @functools.wraps(f)
    def new_method(self):
        return f(self, *args, **kwargs)
    return new_method


def parameterized_class(cls):
    """A class decorator for running parameterized test cases.

    Mark your class with @parameterized_class.
    Mark your test cases with @parameterized.
    """
    test_functions = inspect.getmembers(cls, predicate=inspect.ismethod)
    for (name, f) in test_functions:
        if name.startswith('test_') and not hasattr(f, '_test_data'):
            continue

        # remove the original test function from the class
        delattr(cls, name)

        # add a new test function to the class for each entry in f._test_data
        for tag, args in f._test_data.items():
            new_name = "{0}_{1}".format(f.__name__, tag)
            if hasattr(cls, new_name):
                raise Exception(
                    "Parameterized test case '{0}.{1}' created from '{0}.{2}' "
                    "already exists".format(cls.__name__, new_name, name))

            # Using `def new_method(self): f(self, **args)` is not sufficient
            # (all new_methods use the same args value due to late binding).
            # Instead, use this factory function.
            new_method = def_method(f, **args)

            # To add a method to a class, available for all instances:
            #   MyClass.method = types.MethodType(f, None, MyClass)
            setattr(cls, new_name, types.MethodType(new_method, None, cls))
    return cls


def parameterized(data):
    """A function decorator for parameterized test cases.

    Example:

        @parameterized({
            'zero': dict(val=0),
            'one': dict(val=1),
        })
        def test_val(self, val):
            self.assertEqual(val, self.get_val())

    The above will generate two test cases:
        `test_val_zero` which runs with val=0
        `test_val_one` which runs with val=1

    :param data: A dictionary that looks like {tag: {arg1: val1, ...}}
    """
    def wrapped(f):
        f._test_data = data
        return f
    return wrapped


def wait_for_condition(condition, interval=1, timeout=40):
    start_time = time.time()
    end_time = time.time() + timeout
    while time.time() < end_time:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise Exception(("Timed out after %s seconds.  Started " +
                    "on %s and ended on %s") % (timeout, start_time, end_time))


def memoized(func):
    """A decorator to cache function's return value"""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args):
        if not isinstance(args, abc.Hashable):
            # args is not cacheable. just call the function.
            return func(*args)
        if args in cache:
            return cache[args]
        else:
            value = func(*args)
            cache[args] = value
            return value
    return wrapper
