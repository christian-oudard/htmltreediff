"""
HTML Tree Diff

Basic Usage
>>> from htmltreediff import diff
>>> print diff('<h1>...one...</h1>', '<h1>...two...</h1>', pretty=True)
<h1>
  ...
  <del>
    one
  </del>
  <ins>
    two
  </ins>
  ...
</h1>

Text Diff Usage
>>> print diff(
...     'The quick brown fox jumps over the lazy dog.',
...     'The very quick brown foxes jump over the dog.',
...     html=False,
... )
The <ins>very </ins>quick brown <del>fox jumps</del><ins>foxes jump</ins> over the<del> lazy</del> dog.
"""

from htmltreediff.html import diff
from htmltreediff.util import html_equal

__all__ = ['diff', 'html_equal']
