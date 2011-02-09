==============
HTML Tree Diff
==============

Structure aware diff of XML and HTML documents.

The intended use is to concisely show the edits that have been made in a
document, so that authors of html content can review their work.


What do we mean by "HTML Tree Diff"?
------------------------------------

* HTML:
  The inputs to the diff function are HTML documents
* Tree:
  It considers the full XML tree structure of the inputs, not just text based changes.
* Diff:
  The output is human-readable HTML, using <ins> and <del> tags to show the changes.


Command line interface
----------------------

You can execute htmltreediff.cli directly as a python module, passing it html files to diff::

    $ python -m htmltreediff.cli one.html two.html 
    <h1>
      <del>
        one
      </del>
      <ins>
        two
      </ins>
    </h1>


Python API
----------

You can also use htmltreediff from within a python program as a library.

For HTML Changes::

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

And also for text-only changes::

    >>> from htmltreediff import text_changes
    >>> print text_changes(
    ...     'The quick brown fox jumps over the lazy dog.',
    ...     'The very quick brown foxes jump over the dog.',
    ... )
    The<ins> very</ins> quick brown <del>fox jumps</del><ins>foxes jump</ins> over the<del> lazy</del> dog.
