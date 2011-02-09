import sys
import tempfile
from copy import copy
from pprint import pformat
from textwrap import dedent
from StringIO import StringIO
from xml.dom import Node

from nose.tools import assert_equal, assert_raises
from unittest import TestCase

from htmltreediff import html_changes
from htmltreediff.text import text_changes, WordMatcher, PlaceholderMatcher
from htmltreediff.html import distribute, fix_lists, fix_tables
from htmltreediff.cli import main
from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    html_equal,
    get_location,
    remove_insignificant_text_nodes,
)
from htmltreediff.test_util import (
    reverse_edit_script,
    reverse_changes_html,
    html_diff,
    html_patch,
    strip_changes_old,
    strip_changes_new,
    remove_attributes,
    collapse,
    fix_node_locations,
)

def test_cutoff():
    changes = html_changes(
        '<h1>totally</h1>',
        '<h2>different</h2>',
    )
    assert_equal(
        changes,
        '<h2>The differences from the previous version are too large to show '
        'concisely.</h2>',
    )

def test_illegal_text_nodes():
    html = '''
        <table>
            illegal text
            <tr>
                <td>stuff</td>
            </tr>
        </table>
    '''
    dom = parse_minidom(html)
    html = minidom_tostring(dom)
    assert_equal(
        html,
        '<html><head/><body> illegal text '
        '<table><tbody><tr><td>stuff</td></tr></tbody></table></body></html>',
    )

def test_remove_insignificant_text_nodes():
    html = dedent('''
        <html>
            <head />
            <body>
                <p>
                    one <em>two</em> <strong>three</strong>
                </p>
                <table>
                    <tr>
                        <td>stuff</td>
                    </tr>
                </table>
            </body>
        </html>
    ''')
    dom = parse_minidom(html)
    remove_insignificant_text_nodes(dom)
    html = minidom_tostring(dom)
    assert_equal(
        html,
        '<html><head/><body> <p> one <em>two</em> <strong>three</strong> </p> '
        '<table><tbody><tr><td>stuff</td></tr></tbody></table> </body></html>',
    )

    # Check that it is idempotent.
    dom = parse_minidom(html)
    remove_insignificant_text_nodes(dom)
    html = minidom_tostring(dom)
    assert_equal(
        html,
        ('<html><head/><body> <p> one <em>two</em> <strong>three</strong> </p> '
         '<table><tbody><tr><td>stuff</td></tr></tbody></table> </body></html>'),
    )

def test_remove_insignificant_text_nodes_nbsp():
    html = dedent('''
        <table>
        <tbody>
        <tr>
            <td> </td>
            <td>&#160;</td>
            <td>&nbsp;</td>
        </tr>
        </tbody>
        </table>
    ''')
    dom = parse_minidom(html)
    remove_insignificant_text_nodes(dom)
    html = minidom_tostring(dom)
    assert_equal(
        html,
        ('<html><head/><body><table><tbody><tr><td> </td><td> </td><td> </td>'
         '</tr></tbody></table></body></html>'),
    )

def test_html_changes_pretty():
    cases = [
        (
            'Simple Addition',
            '<h1>one</h1>',
            '<h1>one</h1><h2>two</h2>',
            dedent('''
                <h1>
                  one
                </h1>
                <ins>
                  <h2>
                    two
                  </h2>
                </ins>
            ''').strip(),
        ),
    ]
    for test_name, old_html, new_html, pretty_changes in cases:
        def test():
            changes = html_changes(old_html, new_html, cutoff=0.0, pretty=True)
            print changes
            assert_equal(pretty_changes, changes)
        test.description = 'test_html_changes_pretty - %s' % test_name
        yield test

def test_main():
    # Run the command line interface main function.
    f1 = tempfile.NamedTemporaryFile()
    f1.write('<h1>one</h1>')
    f1.seek(0)
    f2 = tempfile.NamedTemporaryFile()
    f2.write('<h1>one</h1><h2>two</h2>')
    f2.seek(0)

    try:
        old_stdout = sys.stdout
        sys.stdout = stream = StringIO()
        main(argv=('', f1.name, f2.name))
        assert_equal(
            stream.getvalue(),
            dedent('''
                <h1>
                  one
                </h1>
                <ins>
                  <h2>
                    two
                  </h2>
                </ins>
            ''').strip() + '\n',
        )
    finally:
        sys.stdout = old_stdout

    # Run it with no arguments, it throws an error.
    assert_raises(IOError, main)


class TextChangesTestCase(TestCase):
    def test_text_split(self):
        cases = [
            ('word',
             ['word']),
            ('two words',
             ['two', ' ', 'words']),
            ('entity&quot;s',
             ['entity', '&quot;', 's']),
            ("we're excited",
             ["we're", " ", "excited"]),
            ('dial 1-800-555-1234',
             ['dial', ' ', '1-800-555-1234']),
        ]
        placeholder_cases = [
            ('{{{<DOM Element: tagname at 0xhexaddress >}}}',
             ['{{{<DOM Element: tagname at 0xhexaddress >}}}']),
            ('&nbsp;{{{<DOM Element: tagname at 0xhexaddress >}}}',
             ['&nbsp;', '{{{<DOM Element: tagname at 0xhexaddress >}}}']),
            (u'\xa0{{{<DOM Element: tagname at 0xhexaddress >}}}',
             [u'\xa0', u'{{{<DOM Element: tagname at 0xhexaddress >}}}']),
            ('{{{{<DOM Element: tagname at 0xhexaddress >}}}',
             ['{', '{{{<DOM Element: tagname at 0xhexaddress >}}}']),
        ]
        for text, target in cases:
            self.assertEqual(WordMatcher()._split_text(text), target)
        for text, target in cases + placeholder_cases:
            self.assertEqual(PlaceholderMatcher()._split_text(text), target)

    def test_text_changes(self):
        cases = [
            ('The quick brown fox jumps over the lazy dog.',
             'The very quick brown foxes jump over the dog.',
             'The<ins> very</ins> quick brown <del>fox jumps</del><ins>foxes jump</ins> over the<del> lazy</del> dog.',
            ),
            ("we were excited",
             "we're excited",
             "<del>we were</del><ins>we're</ins> excited",
            ),
# This text diff sucks.
#            ('''
#Release Announcement: Protected Policies and Bulk Override
#Last night we successfully updated PolicyStat with a shiny new version. Some of the high notes in this release include:
#
#Managers can now restrict the visibility of certain policies that only certain users can view policies. I'll be writing up a bit more about this feature a little later, but the gist is that you can now do things like restricting certain sensitive HR policies from being viewable by general staff members. Another nice usage would be for partitioning off one segment of policies, say your Lab policies, so that only users from the lab saw them, which can reduce search clutter for the majority of your staff that doesn't care about that set of policies.
#Site administrators now have access to Bulk Admin Override, which makes performing sweeping changes a painless endeavor.
#We optimized the auto-save functionality to allow for better editor performance on long, complicated documents.
#
# All three of these features were prioritized based on direct customer feedback and I'm excited we were able to make it happen. Once again, I think our customers were right on the money on where we could add some very useful functionality. Thanks for the feedback and as always, if you have any other questions/concerns/comments or if you are just wondering how the weather is in Indianapolis, drop us a line.
#             ''',
#             '''
#Release Announcement: Protected Policies and Bulk Override
#Last night we successfully updated PolicyStat with a shiny new version. Some of the high notes in this release include:
#
#Managers can now restrict the visibility of policies so that only certain users can view them. I'll be writing more about this feature a little later, but the gist is that you can now do things like restrict sensitive HR policies from being viewable by general staff members. Another nice usage would be to partition off one segment of policies, say your Lab policies, so that only users from the lab see them. This reduces search clutter for the rest of your staff members, who don't care about the lab policies.
#Site administrators now have access to Bulk Admin Override, which makes performing sweeping changes a painless endeavor.
#We optimized the auto-save functionality to eliminate occasional pauses when your changes get saved. These pauses were too long when working on large documents.
#
# All three of these features were prioritized based on direct customer feedback, and we're excited to be able to make them happen. Once again, I think our customers were right on the money with their suggestions on where things could be improved. Thanks for the feedback as always. If you have any questions/concerns/comments, or if you are just wondering how the weather is in Indianapolis, drop us a line.
#             ''',
#             '''
#             ''',
#            ),
        ]
        for old, new, changes in cases:
            self.assertEqual(text_changes(old, new), changes)

# since the test cases get automatically reversed, only include insert cases,
# not delete cases
test_cases = [ # test case = (old html, new html, inline changes, edit script)
    ( # no changes
        '<h1>one</h1>',
        '<h1>one</h1>',
        '<h1>one</h1>',
        [],
    ),
    ( # simple insert
        '<h1>one</h1>',
        '<h1>one</h1><h2>two</h2>',
        '<h1>one</h1><ins><h2>two</h2></ins>',
        [
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # insert empty element
        '',
        '<div></div>',
        '<ins><div></div></ins>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    ( # insert empty element, short notation
        '',
        '<div/>',
        '<ins><div/></ins>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    ( # insert empty element, with newline
        '\n',
        '<div></div>\n',
        '<ins><div></div></ins>\n',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    ( # insert empty element, with dos newline
        '\r\n',
        '<div></div>\r\n',
        '<ins><div></div></ins>\r\n',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    ( # space after empty tag
        u'',
        u'<ol><li><span></span> </li></ol>',
        u'<ins><ol><li><span></span> </li></ol></ins>',
        [],
    ),
    ( # simple insert with tail text
        'tail',
        '<h1>one</h1>tail',
        '<ins><h1>one</h1></ins>tail',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
        ]
    ),
    ( # simple insert with several siblings, and tail text
        '<h1>one</h1>tail',
        '<h1>one</h1><h2>two</h2>tail',
        '<h1>one</h1><ins><h2>two</h2></ins>tail',
        [
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # insert before
        '<h1>one</h1>',
        '<h2>two</h2><h1>one</h1>',
        '<ins><h2>two</h2></ins><h1>one</h1>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # simple node replace
        '<h1>one</h1>',
        '<h2>two</h2>',
        '<del><h1>one</h1></del><ins><h2>two</h2></ins>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # delete and insert separately
        '<h1>one</h1><h2>two</h2>',
        '<h2>two</h2><h3>three</h3>',
        '<del><h1>one</h1></del><h2>two</h2><ins><h3>three</h3></ins>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h3'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'three'}),
        ]
    ),
    ( # simple node replace with tail text
        '<h1>one</h1>tail',
        '<h2>two</h2>tail',
        '<del><h1>one</h1></del><ins><h2>two</h2></ins>tail',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # multiple node insert
        '<h3>three</h3>',
        '<h1>one</h1><h2>two</h2><h3>three</h3>',
        '<ins><h1>one</h1><h2>two</h2></ins><h3>three</h3>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # multiple node replace
        '<h1>one</h1><h2>two</h2>',
        '<h3>three</h3><h4>four</h4>',
        '<del><h1>one</h1><h2>two</h2></del><ins><h3>three</h3><h4>four</h4></ins>',
        [
            ('delete', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
            ('delete', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h3'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'three'}),
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h4'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'four'}),
        ]
    ),
    ( # multiple node replace with extra text
        'before<h1>one</h1><h2>two</h2>after',
        'before<h3>three</h3><h4>four</h4>after',
        'before<del><h1>one</h1><h2>two</h2></del><ins><h3>three</h3><h4>four</h4></ins>after',
        [
            ('delete', [2, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
            ('delete', [2], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('delete', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h3'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'three'}),
            ('insert', [2], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h4'}),
            ('insert', [2, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'four'}),
        ]
    ),
    ( # multiple node replace with filler in between
        '<h1>one</h1>filler<h2>two</h2>',
        '<h3>three</h3>filler<h4>four</h4>',
        '<del><h1>one</h1></del><ins><h3>three</h3></ins>filler<del><h2>two</h2></del><ins><h4>four</h4></ins>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h3'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'three'}),
            ('delete', [2, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
            ('delete', [2], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [2], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h4'}),
            ('insert', [2, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'four'}),
        ]
    ),
    ( # add before, same markup content
        '<h1><em>xxx</em></h1>',
        '<h2><em>xxx</em></h2><h1><em>xxx</em></h1>',
        '<ins><h2><em>xxx</em></h2></ins><h1><em>xxx</em></h1>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'em'}),
            ('insert', [0, 0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'xxx'}),
        ]
    ),
    ( # deep level change
        '<div><h1>one</h1></div>',
        '<div><h1>one</h1><h2>two</h2></div>',
        '<div><h1>one</h1><ins><h2>two</h2></ins></div>',
        [
            ('insert', [0, 1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    ( # simple text insert
        '<h1>one</h1><h2>two</h2>',
        '<h1>one</h1>test<h2>two</h2>',
        '<h1>one</h1><ins>test</ins><h2>two</h2>',
        [
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'test'}),
        ]
    ),
    ( # simple text change
        '<h1>old</h1>',
        '<h1>new</h1>',
        '<h1><del>old</del><ins>new</ins></h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'old'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'new'}),
        ]
    ),
    ( # insert text before
        '<h1>blue</h1>',
        '<h1>red blue</h1>',
        '<h1><ins>red </ins>blue</h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'blue'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'red blue'}),
        ]
    ),
    ( # insert text inside text section
        '<h1>red blue</h1>',
        '<h1>red green blue</h1>',
        '<h1>red <ins>green </ins>blue</h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'red blue'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'red green blue'}),
        ]
    ),
    ( # change text section
        '<h1>test some stuff</h1>',
        '<h1>test alot of stuff</h1>',
        '<h1>test <del>some</del><ins>alot of</ins> stuff</h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'test some stuff'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'test alot of stuff'}),
        ]
    ),
    ( # add tail text
        '<h1>test</h1>',
        '<h1>test</h1> tail',
        '<h1>test</h1><ins> tail</ins>',
        [
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u' tail'}),
        ]
    ),
    ( # change tail text
        '<h1>test</h1>apple',
        '<h1>test</h1>banana',
        '<h1>test</h1><del>apple</del><ins>banana</ins>',
        [
            ('delete', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'apple'}),
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'banana'}),
        ]
    ),
    ( # add text in between nodes
        '<h1>one</h1><h2>two</h2>',
        '<h1>one</h1>filler<h2>two</h2>',
        '<h1>one</h1><ins>filler</ins><h2>two</h2>',
        [
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'filler'}),
        ]
    ),
    ( # simple tag rename
        '<h1>test</h1>',
        '<h2>test</h2>',
        '<del><h1>test</h1></del><ins><h2>test</h2></ins>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'test'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'test'}),
        ]
    ),
    ( # add before, same text content
        '<h1>test</h1>',
        '<h2>test</h2><h1>test</h1>',
        '<ins><h2>test</h2></ins><h1>test</h1>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'test'}),
        ]
    ),
    ( # complex text change
        '<h1>The quick brown fox jumps over the lazy dog</h1>',
        '<h1>The very quick red fox jumps over the dog again</h1>',
        '<h1>The<ins> very</ins> quick <del>brown</del><ins>red</ins> fox jumps over the <del>lazy </del>dog<ins> again</ins></h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'The quick brown fox jumps over the lazy dog'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'The very quick red fox jumps over the dog again'}),
        ]
    ),
    ( # sub-word-boundary text change
        '<h1>The quick brown fox jumps over the lazy dog</h1>',
        '<h1>The very quick brown foxes jump over the dog</h1>',
        '<h1>The<ins> very</ins> quick brown <del>fox jumps</del><ins>foxes jump</ins> over the <del>lazy </del>dog</h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'The quick brown fox jumps over the lazy dog'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'The very quick brown foxes jump over the dog'}),
        ]
    ),
    ( # insert markup with text before a text section
        '<h1>blue</h1>',
        '<h1><em>green</em> blue</h1>',
        '<h1><ins><em>green</em> </ins>blue</h1>',
        [],
    ),
    ( # insert markup with text inside a text section
        '<h1>red blue</h1>',
        '<h1>red <em>green</em> blue</h1>',
        '<h1>red <ins><em>green</em> </ins>blue</h1>',
        [],
    ),
    ( # insert multiple markup in a text section
        '<h1>red blue</h1>',
        '<h1>red <em>green</em> blue <b>yellow</b></h1>',
        '<h1>red <ins><em>green</em> </ins>blue<ins> <b>yellow</b></ins></h1>',
        [],
    ),
    ( # insert multiple markup in a changing text section
        '<h1>red yellow</h1>',
        '<h1>orange red <em>green</em><b>blue</b> yellow white</h1>',
        '<h1><ins>orange </ins>red <ins><em>green</em><b>blue</b> </ins>yellow<ins> white</ins></h1>',
        [],
    ),
    ( # add markup around a text section
        '<h1>red green blue</h1>',
        '<h1>red <em>green</em> blue</h1>',
        '<h1>red <del>green</del><ins><em>green</em></ins> blue</h1>',
        [],
    ),
    ( # delete markup and text together
        '<h1>red <em>green</em> blue yellow</h1>',
        '<h1>red yellow</h1>',
        '<h1>red <del><em>green</em> blue </del>yellow</h1>',
        [],
    ),
    ( # change markup and make complex text changes together
        '<h1>The quick brown fox jumps over the lazy dog</h1>',
        '<h1>The very quick <b>brown</b> foxes jump over the dog</h1>',
        '<h1>The<ins> very</ins> quick <del>brown fox jumps</del><ins><b>brown</b> foxes jump</ins> over the <del>lazy </del>dog</h1>',
        [],
    ),
    ( # change markup and text together
        '<h1>red <em>green</em> blue yellow</h1>',
        '<h1>red green <b>blue</b> yellow</h1>',
        '<h1>red <del><em>green</em> blue</del><ins>green <b>blue</b></ins> yellow</h1>',
        [],
    ),
    ( # separate text and markup changes
        '<h1>red blue</h1><h2>two</h2>',
        '<h1>reds blue yellow</h1><h2><b>two</b></h2>',
        '<h1><del>red</del><ins>reds</ins> blue<ins> yellow</ins></h1><h2><del>two</del><ins><b>two</b></ins></h2>',
        [],
    ),
    ( # text changes before, inside, and after a block tag
        '<h1>red <div>green</div> blue yellow</h1>',
        '<h1>red orange <div>purple</div> yellow</h1>',
        '<h1>red <ins>orange </ins><div><del>green</del><ins>purple</ins></div><del> blue</del> yellow</h1>',
        [],
    ),
    ( # change markup inside text change
        '<div>one <div>two</div> three</div>',
        '<div>almostone, one and a half, <div>almost <em>two</em></div> three four</div>',
        '<div><ins>almostone, </ins>one <ins>and a half, </ins><div><del>two</del><ins>almost <em>two</em></ins></div> three<ins> four</ins></div>',
        [],
    ),
    ( # ensure that &nbsp; doesn't mess up text diff
        '<div>x</div>',
        '<div>&nbsp;<b>x</b></div>',
        '<div><del>x</del><ins>&nbsp;<b>x</b></ins></div>',
        [],
    ),
    ( # text diff with <
        'x',
        '&lt;',
        '<del>x</del><ins>&lt;</ins>',
        [],
    ),
    ( # text diff with >
        'x',
        '&gt;',
        '<del>x</del><ins>&gt;</ins>',
        [],
    ),
    ( # text diff with &
        'x',
        '&amp;',
        '<del>x</del><ins>&amp;</ins>',
        [],
    ),
    ( # unicode text
        u'<h1>uber</h1>',
        u'<h1>\xc3\xbcber</h1>',
        u'<h1><del>uber</del><ins>\xc3\xbcber</ins></h1>',
        [
            ('delete', [0, 0], {'node_type': 3, 'node_value': u'uber'}),
            ('insert', [0, 0], {'node_type': 3, 'node_value': u'\xc3\xbcber'}),
        ]
    ),
    ( # bug #1463
        '<p><br />yyy</p>',
        '<p><b>xxx</b>yyy<br /></p>',
        '<p><del><br/></del><ins><b>xxx</b></ins>yyy<ins><br/></ins></p>',
        [],
    ),
    ( # crossing node and tree matches
        '<h1>xxx</h1><h1>YYY</h1><h1>YYY</h1><h2>xxx</h2>',
        '<h2>xxx</h2><h1>YYY</h1><h1>YYY</h1><h1>xxx</h1>',
        '<del><h1>xxx</h1></del><ins><h2>xxx</h2></ins><h1>YYY</h1><h1>YYY</h1><del><h2>xxx</h2></del><ins><h1>xxx</h1></ins>',
        [],
    ),
    ( # text normalization
        'first <h1>middle</h1> last',
        'first last',
        'first <del><h1>middle</h1> </del>last',
        [],
    ),
    ( # index in lower levels being affected by changes in upper levels
        '<p><em>zzz</em></p>',
        '<h1>xxx</h1><p>yyy</p>',
        '<ins><h1>xxx</h1></ins><p><del><em>zzz</em></del><ins>yyy</ins></p>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'xxx'}),
            ('delete', [1, 0, 0], {'node_value': u'zzz', 'node_type': 3}),
            ('delete', [1, 0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'em'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'yyy'}),
        ]
    ),
    ( # ignore comments
        '',
        '<div/><!--comment one--><!--comment two-->',
        '<ins><div/></ins>',
        [],
    ),
    ( # ignore style tags
        '',
        '<style type="text/css"></style>',
        '',
        [],
    ),
    ( # style tag in a block of text
        '',
        '<p>xxx<style type="text/css"></style>yyy</p>',
        '<ins><p>xxxyyy</p></ins>',
        [],
    ),
    ( # near match should override tag-only match
        '<p>delete this</p><p>make a small change in this paragraph</p>',
        '<p>a small change was made in this paragraph</p>',
        '<del><p>delete this</p></del><p><del>make </del>a small change <ins>was made </ins>in this paragraph</p>',
        [],
    ),
    ( # don't match when similarity is very low
        '<p>The quick brown fox jumps over the lazy dog</p>',
        '<p>This sentence has nothing to do with the previous one</p>',
        '<p><del>The quick brown fox jumps over the lazy dog</del><ins>This sentence has nothing to do with the previous one</ins></p>',
        [],
    ),
    ( # another similarity test
        '<p>Pass the end of the string under the ring, using the hemostat if necessary.</p>',
        '<p>Take the long end, which is toward the finger, and start wrapping around the finger, starting right against the distal side of the ring, wrapping one wrap after another, continuously, until all the remaining string is used (wrapped around the finger), or until the wraps go at least to, or past the midpoint of the first knuckle.</p>',
        '<p><del>Pass the end of the string under the ring, using the hemostat if necessary.</del><ins>Take the long end, which is toward the finger, and start wrapping around the finger, starting right against the distal side of the ring, wrapping one wrap after another, continuously, until all the remaining string is used (wrapped around the finger), or until the wraps go at least to, or past the midpoint of the first knuckle.</ins></p>',
        [],
    ),
    ( # *do* match when similarity is very low only because of relative lengths
        '<p>hey</p>',
        '<p>hey aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</p>',
        '<p>hey<ins> aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</ins></p>',
        [],
    ),
    ( # changes inside table cells work normally
        '<table><tr><td>A</td></tr></table>',
        '<table><tr><td>B</td></tr></table>',
        '<table><tr><td><del>A</del><ins>B</ins></td></tr></table>',
        [],
    ),
    ( # add an image
        '',
        '<img src="image.gif">',
        '<ins><img src="image.gif"></ins>',
        [
            ('insert', [0], {
                'node_type': Node.ELEMENT_NODE,
                'node_name': u'img',
                'attributes': {u'src': u'image.gif'},
            }),
        ]
    ),
    ( # change an image
        '<img src="old.gif">',
        '<img src="new.gif">',
        '<del><img src="old.gif"></del><ins><img src="new.gif"></ins>',
        [],
    ),
]

# test cases that should not be run in reverse
one_way_test_cases = [
    ( # switch places
        '<h1>one</h1><h2>two</h2>',
        '<h2>two</h2><h1>one</h1>',
        '<ins><h2>two</h2></ins><h1>one</h1><del><h2>two</h2></del>',
        [],
    ),
    ( # switch places, near match
        '<h1>one one</h1><h2>two two</h2>',
        '<h2>two two x</h2><h1>one one yyy</h1>',
        '<ins><h2>two two x</h2></ins><h1>one one<ins> yyy</ins></h1><del><h2>two two</h2></del>',
        [],
    ),
]

# test cases that don't pass sanity checking
insane_test_cases = [
    ( # add a table cell
        '<table><tr><td>A</td></tr></table>',
        '<table><tr><td>A</td><td>B</td></tr></table>',
        '<table><tr><td>A</td><td><ins>B</ins></td></tr></table>',
        [],
    ),
    ( # add a table row
        '<table><tr><td>A</td></tr></table>',
        '<table><tr><td>A</td></tr><tr><td>B</td></tr></table>',
        '<table><tr><td>A</td></tr><tr><td><ins>B</ins></td></tr></table>',
        [],
    ),
    ( # add table rows and cells, to the bottom and right
        '<table><tr><td>A</td></tr></table>',
        '<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>',
        '<table><tr><td>A</td><td><ins>B</ins></td></tr><tr><td><ins>C</ins></td><td><ins>D</ins></td></tr></table>',
        [],
    ),
    ( # add table rows and cells, to the up and left
        '<table><tr><td>D</td></tr></table>',
        '<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>',
        '<table><tr><td><ins>A</ins></td><td><ins>B</ins></td></tr><tr><td><ins>C</ins></td><td>D</td></tr></table>',
        [],
    ),
    ( # delete a table cell
        '<table><tr><td>A</td><td>B</td></tr></table>',
        '<table><tr><td>A</td></tr></table>',
        '<table><tr><td>A</td><td><del>B</del></td></tr></table>',
        [],
    ),
    ( # delete a table row
        '<table><tr><td>A</td></tr><tr><td>B</td></tr></table>',
        '<table><tr><td>A</td></tr></table>',
        '<table><tr><td>A</td></tr><tr><td><del>B</del></td></tr></table>',
        [],
    ),
    ( # delete top row and add a column
        '<table><tr><td>A1</td></tr><tr><td>B1</td></tr></table>',
        '<table><tr><td>B1</td><td>B2</td></tr></table>',
        '<table><tr><td><del>A1</del></td></tr><tr><td>B1</td><td><ins>B2</ins></td></tr></table>',
        [],
    ),
    ( # delete top row and add a column, funny whitespace
        '<table> <tr><td>A1</td></tr> <tr><td>B1</td></tr> </table>',
        '<table> <tr><td>B1</td><td>B2</td></tr> </table>',
        ('<table><tbody><tr><td><del>A1</del></td></tr><tr><td>B1</td>'
         '<td><ins>B2</ins></td></tr></tbody></table>'),
        [],
    ),
    ( # handle newline-separated words correctly
        '<p>line one\nline two</p>',
        '<p>line one line two</p>',
        '<p>line one line two</p>',
        [],
    ),
    ( # ignore adding attributes
        '<h1>one</h1>',
        '<h1 id="ignore" class="ignore">one</h1>',
        '<h1>one</h1>',
        [],
    ),
    ( # ignore deleting attributes
        '<h1 id="ignore" class="ignore">one</h1>',
        '<h1>one</h1>',
        '<h1 id="ignore" class="ignore">one</h1>',
        [],
    ),
    ( # whitespace changes in a table with colspan
        '''
        <table class="table_class">
            <tbody>
                <tr>
                    <td colspan="2">top across</td>
                </tr>
                <tr>
                    <td>bottom left</td>
                    <td>bottom right</td>
                </tr>
            </tbody>
        </table>
        ''',
        '''
        <table class="table_class"><tbody>
        <tr>
        <td colspan="2">top across</td>
        </tr>
        <tr>
        <td>bottom left</td>
        <td>bottom right</td>
        </tr>
        </tbody></table>
        ''',
        collapse('''
        <table class="table_class"><tbody>
        <tr>
        <td colspan="2">top across</td>
        </tr>
        <tr>
        <td>bottom left</td>
        <td>bottom right</td>
        </tr>
        </tbody></table>
        '''),
        [],
    ),
    ( # whitespace changes in a table with nbsp entity
        '''
        <table>
        <tbody>
        <tr>
            <td> </td>
            <td>&#160;</td>
            <td>&nbsp;</td>
        </tr>
        </tbody>
        </table>
        ''',
        '''
        <table>
        <tbody>
        <tr>
        <td> </td>
        <td>&#160;</td>
        <td>&nbsp;</td>
        </tr>
        </tbody>
        </table>
        ''',
        collapse('''
        <table>
        <tbody>
        <tr>
        <td> </td>
        <td>&#160;</td>
        <td>&nbsp;</td>
        </tr>
        </tbody>
        </table>
        '''),
        [],
    ),
#BROKEN, see issue #2384
#    # ul and ol tags are considered equal when diffing
#    (
#        '<ul><li>X</li></ul>',
#        '<ol><li>X</li></ol>',
#        '<ol><li>X</li></ol>',
#        [],
#    ),
#    (
#        '<ol><li>X</li></ol>',
#        '<ul><li>X</li></ul>',
#        '<ul><li>X</li></ul>',
#        [],
#    ),
]

# Assemble test cases
# add reverse test cases
# switch the old and new html, and reverse the changes
def reverse_cases(cases):
    for old_html, new_html, target_changes, edit_script in copy(cases):
        yield (
            new_html,
            old_html,
            reverse_changes_html(target_changes),
            reverse_edit_script(edit_script),
        )
reverse_test_cases = list(reverse_cases(test_cases))

# Fix node locations
test_cases = list(fix_node_locations(test_cases))
reverse_test_cases = list(fix_node_locations(reverse_test_cases))
one_way_test_cases = list(fix_node_locations(one_way_test_cases))
insane_test_cases = list(fix_node_locations(insane_test_cases))

# Combined cases
all_test_cases = (test_cases +
                  reverse_test_cases +
                  one_way_test_cases +
                  insane_test_cases)


class HtmlChangesTestCase(TestCase):
    def assert_html_equal(self, a_html, b_html):
        self.assertTrue(html_equal(a_html, b_html), u'These html documents are not equal:\n%r\n====\n%r' % (a_html, b_html))

    def assert_html_not_equal(self, a_html, b_html):
        self.assertFalse(html_equal(a_html, b_html), u'These html documents should not be equal:\n%r\n====\n%r' % (a_html, b_html))

    def assert_strip_changes(self, old_html, new_html, changes):
        self.assert_html_equal(old_html, strip_changes_old(changes))
        self.assert_html_equal(new_html, strip_changes_new(changes))

    def test_parse_comments(self):
        self.assert_html_equal(
            minidom_tostring(parse_minidom('<!-- -->')),
            '',
        )
        self.assert_html_equal(
            minidom_tostring(parse_minidom('<!--\n-->')),
            '',
        )
        self.assert_html_equal(
            minidom_tostring(parse_minidom('<p>stuff<!-- \n -->stuff</p>')),
            '<p>stuffstuff</p>',
        )

    def test_html_equal(self):
        html_equal_cases = [
            ('<h1>test</h1>',
             '<h1>test</h1>'),
            ('<h1> test</h1>',
             '<h1> test'),
            ('<span />',
             '<span/>'),
            ('<span></span>',
             '<span/>'),
            ('<h1 id="id_test" class="test">test</h1>',
             '<h1 class="test" id="id_test">test</h1>'),
            ('<html><head/><body><div/>\n</body></html>\n',
             '<div></div>\n'),
            ('<html><head/><body><div/>\n</body></html>\n',
             '<div></div>\r\n'),
        ]
        for a_html, b_html in html_equal_cases:
            self.assert_html_equal(a_html, b_html)

    def test_html_not_equal(self):
        html_not_equal_cases = [
            ('<h1>test</h1>',
             '<h2>test</h2>'),
            ('<h1>red</h1>',
             '<h1>green</h1>'),
            ('<h1> test</h1>',
             '<h1>test</h1>'),
            ('<span> </span>',
             '<span/>'),
            ('<h1>one</h1>',
             '<h1>one</h1><h2>two</h2>'),
            ('<ul><li>A</li></ul>',
             '<ol><li>A</li></ol>'),
        ]
        for a_html, b_html in html_not_equal_cases:
            self.assert_html_not_equal(a_html, b_html)

    def test_remove_attributes(self):
        remove_attributes_cases = [
            ('<h1>one</h1>',
             '<h1>one</h1>'),
            ('<h1 class="test">one</h1>',
             '<h1>one</h1>'),
            ('<h1 id="test-heading" class="test">one</h1>',
             '<h1>one</h1>'),
            ('<div>before <h1 id="test-heading" class="test">one</h1> after </div>',
             '<div>before <h1>one</h1> after </div>'),
            (u'<h1 class="test">\xc3\xbcber</h1>',
             u'<h1>\xc3\xbcber</h1>'),
        ]
        for html, stripped_html, in remove_attributes_cases:
            self.assert_html_equal(remove_attributes(html), stripped_html)

    def test_cases_sanity(self):
        # check that removing the ins and del markup gives the original
        sane_cases = (test_cases + reverse_test_cases + one_way_test_cases)
        try:
            for old_html, new_html, target_changes, edit_script in sane_cases:
                self.assert_strip_changes(old_html, new_html, target_changes)
        except:
            print
            print 'Test case sanity failed on:'
            print old_html
            print new_html
            print target_changes
            raise

    def test_html_diff(self):
        try:
            # edit script output does not reverse easily, don't test the reverse cases
            for old_html, new_html, target_changes, edit_script in (test_cases + one_way_test_cases):
                if not edit_script:
                    continue
                actual_edit_script = html_diff(old_html, new_html)
                self.assertEqual(
                    edit_script,
                    actual_edit_script,
                    'These edit scripts do not match:\n%s\n!=\n%s' % (pformat(edit_script), pformat(actual_edit_script)),
                )
        except:
            print
            print 'Html diff failed on:'
            print old_html
            print new_html
            print edit_script
            raise

    def test_html_patch(self):
        try:
            for old_html, new_html, target_changes, target_edit_script in all_test_cases:
                # check that applying the diff gives back the same new_html
                edit_script = []
                edit_script = html_diff(old_html, new_html)
                edited_html = html_patch(old_html, edit_script)
                self.assert_html_equal(
                    remove_attributes(edited_html),
                    remove_attributes(new_html),
                )
        except:
            print
            print 'Html Patch failed on:'
            print 'old:', old_html
            print 'new:', new_html
            print 'changes:', target_changes
            print 'edit script:'
            for step in edit_script:
                print step
            raise

    def test_html_changes(self):
        try:
            for old_html, new_html, target_changes, edit_script in all_test_cases:
                # check full diff function
                changes = None
                changes = html_changes(old_html, new_html, cutoff=0.0)
                # test that the generated diff gives back the original
                if (old_html, new_html, target_changes, edit_script) not in insane_test_cases:
                    self.assert_strip_changes(old_html, new_html, changes)
                # test that it matches the expected value
                self.assert_html_equal(changes, target_changes) # if we fail here, the test case is possibly wrong
        except:
            print
            print 'HtmlChanges failed on:'
            print 'old:', old_html
            print 'new:', new_html
            print 'target:', target_changes
            print 'actual:', changes
            print 'expected edit script:'
            for step in edit_script:
                print step
            print 'actual edit script:'
            for step in html_diff(old_html, new_html):
                print step
            raise

    def test_distribute(self):
        cases = [
            ('<ins><li>A</li><li><em>B</em></li></ins>',
             '<li><ins>A</ins></li><li><ins><em>B</em></ins></li>'),
        ]
        for original, distributed in cases:
            original = parse_minidom(original)
            distributed = parse_minidom(distributed)
            node = get_location(original, [1, 0])
            distribute(node)
            self.assert_html_equal(
                minidom_tostring(original),
                minidom_tostring(distributed))

    def test_fix_lists(self):
        cases = [
            ( # simple list item insert
                '''
                <ol>
                  <li>one</li>
                  <ins><li>two</li></ins>
                </ol>
                ''',
                '''
                <ol>
                  <li>one</li>
                  <li><ins>two</ins></li>
                </ol>
                '''
            ),
            ( # multiple list item insert
                '''
                <ol>
                  <li>one</li>
                  <ins>
                    <li>two</li>
                    <li>three</li>
                  </ins>
                </ol>
                ''',
                '''
                <ol>
                  <li>one</li>
                  <li><ins>two</ins></li>
                  <li><ins>three</ins></li>
                </ol>
                '''
            ),
            ( # simple list item delete afterward
                '''
                <ol>
                  <li>one</li>
                  <del><li>one and a half</li></del>
                </ol>
                ''',
                '''
                <ol>
                  <li>one</li>
                  <li class="del-li"><del>one and a half</del></li>
                </ol>
                '''
            ),
            ( # simple list item delete first
                '''
                <ol>
                  <del><li>one half</li></del>
                  <li>one</li>
                </ol>
                ''',
                '''
                <ol>
                  <li class="del-li"><del>one half</del></li>
                  <li>one</li>
                </ol>
                '''
            ),
            ( # multiple list item delete first
                '''
                <ol>
                  <del>
                    <li>one third</li>
                    <li>two thirds</li>
                  </del>
                  <li>one</li>
                </ol>
                ''',
                '''
                <ol>
                  <li class="del-li"><del>one third</del></li>
                  <li class="del-li"><del>two thirds</del></li>
                  <li>one</li>
                </ol>
                '''
            ),
            ( # insert and delete separately
                '''
                <ol>
                  <li>one</li>
                  <ins><li>two</li></ins>
                  <li>three</li>
                  <del><li>three point five</li></del>
                  <li>four</li>
                </ol>
                ''',
                '''
                <ol>
                  <li>one</li>
                  <li><ins>two</ins></li>
                  <li>three</del>
                  <li class="del-li"><del>three point five</del></li>
                  <li>four</li>
                </ol>
                '''
            ),
            ( # multiple list item delete
                '''
                <ol>
                  <li>one</li>
                  <del>
                    <li>two</li>
                    <li>three</li>
                  </del>
                </ol>
                ''',
                '''
                <ol>
                  <li>one</li>
                  <li class="del-li"><del>two</del></li>
                  <li class="del-li"><del>three</del></li>
                </ol>
                '''
            ),
            ( # delete only list item
                '''
                <ol>
                  <del>
                    <li>one</li>
                  </del>
                </ol>
                ''',
                '''
                <ol>
                  <li class="del-li"><del>one</del></li>
                </ol>
                '''
            ),
        ]
        for changes, fixed_changes in cases:
            changes = collapse(changes)
            fixed_changes = collapse(fixed_changes)
            changes_dom = parse_minidom(changes)
            fix_lists(changes_dom)
            self.assert_html_equal(minidom_tostring(changes_dom), fixed_changes)

    def test_fix_tables(self):
        cases = [
            ( # add a table row
                '''
                <table>
                  <tr><td>A</td></tr>
                  <ins><tr><td>B</td></tr></ins>
                </table>
                ''',
                '''
                <table>
                  <tr><td>A</td></tr>
                  <tr><td><ins>B</ins></td></tr>
                </table>
                '''
            ),
            ( # remove ins and del tags at the wrong level of the table
                '''
                <table>
                    <ins> </ins><del> </del>
                    <thead>
                        <ins> </ins><del> </del>
                    </thead>
                    <tfoot>
                        <ins> </ins><del> </del>
                    </tfoot>
                    <tbody>
                        <ins> </ins><del> </del>
                        <tr>
                            <ins> </ins><del> </del>
                            <td><ins>A</ins></td>
                        </tr>
                    </tbody>
                </table>
                ''',
                '''
                <table>
                    <thead></thead>
                    <tfoot></tfoot>
                    <tbody>
                        <tr>
                            <td><ins>A</ins></td>
                        </tr>
                    </tbody>
                </table>
                ''',
            ),
        ]
        for changes, fixed_changes in cases:
            changes = collapse(changes)
            fixed_changes = collapse(fixed_changes)
            changes_dom = parse_minidom(changes, html=False)
            fix_tables(changes_dom)
            self.assert_html_equal(minidom_tostring(changes_dom), fixed_changes)
