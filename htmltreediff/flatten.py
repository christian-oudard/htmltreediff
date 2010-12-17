# from http://gist.github.com/443891
"""
Flatten a nested list structure.

* Works for nested structures of lists, tuples, generators, or any other iterable.
* Special-cases string types and treats them as non-iterable.
* Is not limited to the system recursion limit.
* Yields items from the structure instead of constructing a new list, and can
  work on non-terminating generators.

This is basically a non-recursive version of the following:

def flatten(iterable):
    iterable = iter(iterable)
    for item in iterable:
        if hasattr(item, '__iter__') and not isinstance(item, (str, bytes)):
            for i in flatten(item):
                yield i
        else:
            yield item


>>> list(flatten([]))
[]
>>> list(flatten([1, []]))
[1]
>>> list(flatten([[0], 1]))
[0, 1]
>>> list(flatten([1, [2, [3, 4]]]))
[1, 2, 3, 4]
>>> list(flatten((1, (2, 3))))
[1, 2, 3]
>>> list(flatten(['one', ['two', ['three', 'four']]]))
['one', 'two', 'three', 'four']
>>> list(flatten([1, 2, [3, 4], (5,6), [7, [8, [9, [10]]]]]))
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

>>> def make_nested_list(n):
...     result = []
...     for i in range(n):
...         result = [result, i]
...     return result
...
>>> import sys
>>> n = sys.getrecursionlimit() + 1
>>> assert list(range(n)) == list(flatten(make_nested_list(n)))

>>> def nested_gen(i=0):
...     yield i
...     yield nested_gen(i + 1)
...
>>> n = sys.getrecursionlimit() + 1
>>> from itertools import islice
>>> assert list(range(n)) == list(islice(flatten(nested_gen()), n))
"""

def flatten(iterable):
    iterable = iter(iterable)
    stack = []
    while True:
        for item in iterable:
            if hasattr(item, '__iter__') and \
               not isinstance(item, (basestring)):
                stack.append(iterable)
                iterable = iter(item)
                break
            else:
                yield item
        else:
            if not stack:
                return
            iterable = stack.pop()
