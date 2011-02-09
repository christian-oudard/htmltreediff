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
from htmltreediff.html_diff import HtmlDiffer, tree_text_ratio
from htmltreediff.edit_script_runner import EditScriptRunner
from htmltreediff.html import add_changes_markup
from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    get_location,
    html_equal,
)

__all__ = ['text_changes', 'html_changes', 'html_equal']

def html_changes(old_html, new_html, cutoff=0.0, pretty=False):
    """Show the differences between the old and new html document, as html.

    Return the document html with extra tags added to show changes. Add <ins>
    tags around newly added sections, and <del> tags to show sections that have
    been deleted.
    """
    old_dom = parse_minidom(old_html)
    new_dom = parse_minidom(new_html)
    # If the two documents are not similar enough, don't show the changes.
    ratio = tree_text_ratio(old_dom, new_dom)
    if ratio < cutoff:
        return '<h2>The differences from the previous version are too large to show concisely.</h2>'
    # Get the edit script from the diff algorithm
    differ = HtmlDiffer(old_dom, new_dom)
    edit_script = differ.get_edit_script()
    # Run the edit script, then use the inserted and deleted nodes metadata to
    #     show changes.
    runner = EditScriptRunner(old_dom, edit_script)
    dom = runner.run_edit_script()
    add_changes_markup(dom, runner.ins_nodes, runner.del_nodes)
    # Only return html for the document body contents.
    body = dom.getElementsByTagName('body')[0]
    return minidom_tostring(body, pretty=pretty)
