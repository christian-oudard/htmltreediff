from textwrap import dedent

from nose.tools import assert_equal

from htmltreediff.html import diff
from htmltreediff.tests import assert_html_equal
from htmltreediff.changes import distribute
from htmltreediff.html import fix_lists, fix_tables
from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    remove_insignificant_text_nodes,
    get_location,
)
from htmltreediff.test_util import collapse


## Preprocessing

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


## Post-processing

def test_cutoff():
    changes = diff(
        '<h1>totally</h1>',
        '<h2>different</h2>',
        cutoff=0.2,
    )
    assert_equal(
        changes,
        '<h2>The differences from the previous version are too large to show '
        'concisely.</h2>',
    )

def test_html_diff_pretty():
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
            changes = diff(old_html, new_html, cutoff=0.0, pretty=True)
            assert_equal(pretty_changes, changes)
        test.description = 'test_html_diff_pretty - %s' % test_name
        yield test

def test_distribute():
    cases = [
        ('<ins><li>A</li><li><em>B</em></li></ins>',
         '<li><ins>A</ins></li><li><ins><em>B</em></ins></li>'),
    ]
    for original, distributed in cases:
        def test(original, distributed):
            original = parse_minidom(original)
            distributed = parse_minidom(distributed)
            node = get_location(original, [1, 0])
            distribute(node)
            assert_html_equal(
                minidom_tostring(original),
                minidom_tostring(distributed),
            )
        yield test, original, distributed

def test_fix_lists():
    cases = [
        (
            'simple list item insert',
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
        (
            'multiple list item insert',
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
        (
            'simple list item delete afterward',
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
        (
            'simple list item delete first',
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
        (
            'multiple list item delete first',
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
        (
            'insert and delete separately',
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
        (
            'multiple list item delete',
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
        (
            'delete only list item',
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
    for test_name, changes, fixed_changes in cases:
        changes = collapse(changes)
        fixed_changes = collapse(fixed_changes)
        def test():
            changes_dom = parse_minidom(changes)
            fix_lists(changes_dom)
            assert_html_equal(minidom_tostring(changes_dom), fixed_changes)
        test.description = 'test_fix_lists - %s' % test_name
        yield test

def test_fix_tables():
    cases = [
        (
            'add a table row',
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
        (
            'remove ins and del tags at the wrong level of the table',
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
    for test_name, changes, fixed_changes in cases:
        changes = collapse(changes)
        fixed_changes = collapse(fixed_changes)
        def test():
            changes_dom = parse_minidom(changes, html=False)
            fix_tables(changes_dom)
            assert_html_equal(minidom_tostring(changes_dom), fixed_changes)
        test.description = 'test_fix_tables - %s' % test_name
        yield test
