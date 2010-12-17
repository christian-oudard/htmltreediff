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
