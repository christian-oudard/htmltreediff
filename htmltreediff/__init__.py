"""
HTML Tree Diff

Basic Usage
>>> from htmltreediff import html_changes
>>> print html_changes('<h1>one</h1>', '<h1>two</h1>')
<h1><del>one</del><ins>two</ins></h1>
>>> print html_changes('<h1>one</h1>', '<h1>two</h1>', pretty=True)
<h1>
  <del>
    one
  </del>
  <ins>
    two
  </ins>
</h1>

Text Diff Usage
>>> from htmltreediff import text_changes
>>> print text_changes(
...     'The quick brown fox jumps over the lazy dog.',
...     'The very quick brown foxes jump over the dog.',
... )
The<ins> very</ins> quick brown <del>fox jumps</del><ins>foxes jump</ins> over the<del> lazy</del> dog.
"""

from htmltreediff.text import text_changes
from htmltreediff.html import html_changes
from htmltreediff.util import html_equal
