# coding: utf8

from pprint import pformat
from xml.dom import Node

from nose.tools import assert_equal

from htmltreediff.html import diff
from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    html_equal,
)
from htmltreediff.test_util import (
    reverse_edit_script,
    reverse_changes_html,
    get_edit_script,
    html_patch,
    strip_changes_old,
    strip_changes_new,
    remove_attributes,
    collapse,
    parse_cases,
)

# since the test cases get automatically reversed, only include insert cases,
# not delete cases
test_cases = [ # test case = (old html, new html, inline changes, edit script)
    (
        'no changes',
        '<h1>one</h1>',
        '<h1>one</h1>',
        '<h1>one</h1>',
        [],
    ),
    (
        'simple insert',
        '<h1>one</h1>',
        '<h1>one</h1><h2>two</h2>',
        '<h1>one</h1><ins><h2>two</h2></ins>',
        [
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    (
        'insert empty element',
        '',
        '<div></div>',
        '<ins><div></div></ins>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    (
        'insert empty element, short notation',
        '',
        '<div/>',
        '<ins><div/></ins>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    (
        'insert empty element, with newline',
        '\n',
        '<div></div>\n',
        '<ins><div></div></ins>\n',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    (
        'insert empty element, with dos newline',
        '\r\n',
        '<div></div>\r\n',
        '<ins><div></div></ins>\r\n',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'div'}),
        ]
    ),
    (
        'space after empty tag',
        u'',
        u'<ol><li><span></span> </li></ol>',
        u'<ins><ol><li><span></span> </li></ol></ins>',
    ),
    (
        'simple insert with tail text',
        '<div>tail</div>',
        '<div><h1>one</h1>tail</div>',
        '<div><ins><h1>one</h1></ins>tail</div>',
        [
            ('insert', [0, 0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
        ]
    ),
    (
        'simple insert with several siblings, and tail text',
        '<h1>one</h1>tail',
        '<h1>one</h1><h2>two</h2>tail',
        '<h1>one</h1><ins><h2>two</h2></ins>tail',
        [
            ('insert', [1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    (
        'insert before',
        '<h1>one</h1>',
        '<h2>two</h2><h1>one</h1>',
        '<ins><h2>two</h2></ins><h1>one</h1>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    (
        'simple node replace',
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
    (
        'delete and insert separately',
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
    (
        'simple node replace with tail text',
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
    (
        'multiple node insert',
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
    (
        'multiple node replace',
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
    (
        'multiple node replace with extra text',
        '<div>before<h1>one</h1><h2>two</h2>after</div>',
        '<div>before<h3>three</h3><h4>four</h4>after</div>',
        '<div>before<del><h1>one</h1><h2>two</h2></del><ins><h3>three</h3><h4>four</h4></ins>after</div>',
        [
            ('delete', [0, 2, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
            ('delete', [0, 2], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('delete', [0, 1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'one'}),
            ('delete', [0, 1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h3'}),
            ('insert', [0, 1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'three'}),
            ('insert', [0, 2], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h4'}),
            ('insert', [0, 2, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'four'}),
        ]
    ),
    (
        'multiple node replace with filler in between',
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
    (
        'add before, same markup content',
        '<h1><em>xxx</em></h1>',
        '<h2><em>xxx</em></h2><h1><em>xxx</em></h1>',
        '<ins><h2><em>xxx</em></h2></ins><h1><em>xxx</em></h1>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'em'}),
            ('insert', [0, 0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'xxx'}),
        ]
    ),
    (
        'deep level change',
        '<div><h1>one</h1></div>',
        '<div><h1>one</h1><h2>two</h2></div>',
        '<div><h1>one</h1><ins><h2>two</h2></ins></div>',
        [
            ('insert', [0, 1], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'two'}),
        ]
    ),
    (
        'simple text insert',
        '<h1>one</h1><h2>two</h2>',
        '<h1>one</h1>test<h2>two</h2>',
        '<h1>one</h1><ins>test</ins><h2>two</h2>',
        [
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'test'}),
        ]
    ),
    (
        'simple text change, similar text',
        '<h1>... old ...</h1>',
        '<h1>... new ...</h1>',
        '<h1>... <del>old</del><ins>new</ins> ...</h1>',
        [
            ('delete', [0, 4], {'node_type': Node.TEXT_NODE, 'node_value': u'old'}),
            ('insert', [0, 4], {'node_type': Node.TEXT_NODE, 'node_value': u'new'}),
        ]
    ),
    (
        'simple text change, totally different text',
        '<h1>old</h1>',
        '<h1>new</h1>',
        '<del><h1>old</h1></del><ins><h1>new</h1></ins>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'old'}),
            ('delete', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'new'}),
        ]
    ),
    (
        'insert text before',
        '<h1>blue</h1>',
        '<h1>red blue</h1>',
        '<h1><ins>red </ins>blue</h1>',
        [
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'red'}),
            ('insert', [0, 1], {'node_type': Node.TEXT_NODE, 'node_value': u' '}),
        ]
    ),
    (
        'insert text inside text section',
        '<h1>red blue</h1>',
        '<h1>red green blue</h1>',
        '<h1>red <ins>green </ins>blue</h1>',
        [
            ('insert', [0, 2], {'node_type': Node.TEXT_NODE, 'node_value': u'green'}),
            ('insert', [0, 3], {'node_type': Node.TEXT_NODE, 'node_value': u' '}),
        ]
    ),
    (
        'change text section',
        '<h1>test some stuff</h1>',
        '<h1>test alot of stuff</h1>',
        '<h1>test <del>some</del><ins>alot of</ins> stuff</h1>',
        [
            ('delete', [0, 2], {'node_type': Node.TEXT_NODE, 'node_value': u'some'}),
            ('insert', [0, 2], {'node_type': Node.TEXT_NODE, 'node_value': u'alot'}),
            ('insert', [0, 3], {'node_type': Node.TEXT_NODE, 'node_value': u' '}),
            ('insert', [0, 4], {'node_type': Node.TEXT_NODE, 'node_value': u'of'}),
        ]
    ),
    (
        'add tail text',
        '<h1>test</h1>',
        '<h1>test</h1> tail',
        '<h1>test</h1><ins> tail</ins>',
        [
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u' '}),
            ('insert', [2], {'node_type': Node.TEXT_NODE, 'node_value': u'tail'}),
        ]
    ),
    (
        'change tail text',
        '<h1>test</h1>apple',
        '<h1>test</h1>banana',
        '<h1>test</h1><del>apple</del><ins>banana</ins>',
        [
            ('delete', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'apple'}),
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'banana'}),
        ]
    ),
    (
        'add text in between nodes',
        '<h1>one</h1><h2>two</h2>',
        '<h1>one</h1>filler<h2>two</h2>',
        '<h1>one</h1><ins>filler</ins><h2>two</h2>',
        [
            ('insert', [1], {'node_type': Node.TEXT_NODE, 'node_value': u'filler'}),
        ]
    ),
    (
        'simple tag rename',
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
    (
        'add before, same text content',
        '<h1>test</h1>',
        '<h2>test</h2><h1>test</h1>',
        '<ins><h2>test</h2></ins><h1>test</h1>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h2'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'test'}),
        ]
    ),
    (
        'complex text change',
        '<h1>The quick brown fox jumps over the lazy dog</h1>',
        '<h1>The very quick red fox jumps over the dog again</h1>',
        '<h1>The <ins>very </ins>quick <del>brown</del><ins>red</ins> fox jumps over the <del>lazy </del>dog<ins> again</ins></h1>',
    ),
    (
        'sub-word-boundary text change',
        '<h1>The quick brown fox jumps over the lazy dog</h1>',
        '<h1>The very quick brown foxes jump over the dog</h1>',
        '<h1>The <ins>very </ins>quick brown <del>fox jumps</del><ins>foxes jump</ins> over the <del>lazy </del>dog</h1>',
    ),
    (
        'insert markup with text before a text section',
        '<h1>blue</h1>',
        '<h1><em>green</em> blue</h1>',
        '<h1><ins><em>green</em> </ins>blue</h1>',
    ),
    (
        'insert markup with text inside a text section',
        '<h1>red blue</h1>',
        '<h1>red <em>green</em> blue</h1>',
        '<h1>red <ins><em>green</em> </ins>blue</h1>',
    ),
    (
        'insert multiple markup in a text section',
        '<h1>red blue</h1>',
        '<h1>red <em>green</em> blue <b>yellow</b></h1>',
        '<h1>red <ins><em>green</em> </ins>blue<ins> <b>yellow</b></ins></h1>',
    ),
    (
        'insert multiple markup in a changing text section',
        '<h1>... red yellow</h1>',
        '<h1>... orange red <em>green</em><b>blue</b> yellow white</h1>',
        '<h1>... <ins>orange </ins>red <ins><em>green</em><b>blue</b> </ins>yellow<ins> white</ins></h1>',
    ),
    (
        'add markup around a text section',
        '<h1>red green blue</h1>',
        '<h1>red <em>green</em> blue</h1>',
        '<h1>red <del>green</del><ins><em>green</em></ins> blue</h1>',
    ),
    (
        'delete markup and text together',
        '<h1>red <em>green</em> blue yellow</h1>',
        '<h1>red yellow</h1>',
        '<h1>red <del><em>green</em> blue </del>yellow</h1>',
    ),
    (
        'change markup and make complex text changes together',
        '<h1>The quick brown fox jumps over the lazy dog</h1>',
        '<h1>The very quick <b>brown</b> foxes jump over the dog</h1>',
        '<h1>The <ins>very </ins>quick <del>brown fox jumps</del><ins><b>brown</b> foxes jump</ins> over the <del>lazy </del>dog</h1>',
    ),
    (
        'change markup and text together',
        '<h1>red <em>green</em> blue yellow</h1>',
        '<h1>red green <b>blue</b> yellow</h1>',
        '<h1>red <del><em>green</em> blue</del><ins>green <b>blue</b></ins> yellow</h1>',
    ),
    (
        'separate text and markup changes',
        '<h1>... red blue</h1><h2>two</h2>',
        '<h1>... reds blue yellow</h1><h2><b>two</b></h2>',
        '<h1>... <del>red</del><ins>reds</ins> blue<ins> yellow</ins></h1><h2><del>two</del><ins><b>two</b></ins></h2>',
    ),
    (
        'text changes before, inside, and after a block tag',
        '<h1>red <div>green</div> blue yellow</h1>',
        '<h1>red orange <div>purple</div> yellow</h1>',
        '<h1>red <del><div>green</div> blue</del><ins>orange <div>purple</div></ins> yellow</h1>',
    ),
    (
        'change markup inside text change',
        '<div>one <div>two</div> three</div>',
        '<div>almostone, one and a half, <div>almost <em>two</em></div> three four</div>',
        '<div><ins>almostone, </ins>one <ins>and a half, </ins><div><del>two</del><ins>almost <em>two</em></ins></div> three<ins> four</ins></div>',
    ),
    (
        "ensure that &nbsp; doesn't mess up text diff",
        '<div>x</div>',
        '<div>&nbsp;<b>x</b></div>',
        '<div><del>x</del><ins>&nbsp;<b>x</b></ins></div>',
    ),
    (
        'unicode text',
        u'<h1>uber ......</h1>',
        u'<h1>über ......</h1>',
        u'<h1><del>uber</del><ins>über</ins> ......</h1>',
        [
            ('delete', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'uber'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'über'}),
        ]
    ),
    (
        'bug #1463',
        '<p><br />yyy</p>',
        '<p><b>xxx</b>yyy<br /></p>',
        '<p><del><br/></del><ins><b>xxx</b></ins>yyy<ins><br/></ins></p>',
    ),
    (
        'crossing node and tree matches',
        '<h1>xxx</h1><h1>YYY</h1><h1>YYY</h1><h2>xxx</h2>',
        '<h2>xxx</h2><h1>YYY</h1><h1>YYY</h1><h1>xxx</h1>',
        '<del><h1>xxx</h1></del><ins><h2>xxx</h2></ins><h1>YYY</h1><h1>YYY</h1><del><h2>xxx</h2></del><ins><h1>xxx</h1></ins>',
    ),
    (
        'index in lower levels being affected by changes in upper levels',
        '<p><em>zzz</em> ...</p>',
        '<h1>xxx</h1><p>yyy ...</p>',
        '<ins><h1>xxx</h1></ins><p><del><em>zzz</em></del><ins>yyy</ins> ...</p>',
        [
            ('insert', [0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'h1'}),
            ('insert', [0, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'xxx'}),
            ('delete', [1, 0, 0], {'node_value': u'zzz', 'node_type': 3}),
            ('delete', [1, 0], {'node_type': Node.ELEMENT_NODE, 'node_name': u'em'}),
            ('insert', [1, 0], {'node_type': Node.TEXT_NODE, 'node_value': u'yyy'}),
        ]
    ),
    (
        'near match should override tag-only match',
        '<p>delete this</p><p>make a small change in this paragraph</p>',
        '<p>a small change was made in this paragraph</p>',
        '<del><p>delete this</p></del><p><del>make </del>a small change <ins>was made </ins>in this paragraph</p>',
    ),
    (
        "don't match when similarity is very low",
        '<p>The quick brown fox jumps over the lazy dog</p>',
        '<p>This sentence has nothing to do with the previous one</p>',
        '<del><p>The quick brown fox jumps over the lazy dog</p></del><ins><p>This sentence has nothing to do with the previous one</p></ins>',
    ),
    (
        'another similarity test',
        '<p>Pass the end of the string under the ring, using the hemostat if necessary.</p>',
        '<p>Take the long end, which is toward the finger, and start wrapping around the finger, starting right against the distal side of the ring, wrapping one wrap after another, continuously, until all the remaining string is used (wrapped around the finger), or until the wraps go at least to, or past the midpoint of the first knuckle.</p>',
        '<del><p>Pass the end of the string under the ring, using the hemostat if necessary.</p></del><ins><p>Take the long end, which is toward the finger, and start wrapping around the finger, starting right against the distal side of the ring, wrapping one wrap after another, continuously, until all the remaining string is used (wrapped around the finger), or until the wraps go at least to, or past the midpoint of the first knuckle.</p></ins>',
    ),
    (
        'changes inside table cells work normally',
        '<table><tr><td>... A ...</td></tr></table>',
        '<table><tr><td>... B ...</td></tr></table>',
        '<table><tr><td>... <del>A</del><ins>B</ins> ...</td></tr></table>',
    ),
    (
        'add an image',
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
    (
        'change an image',
        '<img src="old.gif">',
        '<img src="new.gif">',
        '<del><img src="old.gif"></del><ins><img src="new.gif"></ins>',
    ),
    (
        'test delete action index ordering',
        '<p><em>xxx</em></p>',
        '<p>zzz<em>xxx yyy</em></p>',
        '<p><ins>zzz</ins><em>xxx<ins> yyy</ins></em></p>',
    ),
]

# test cases that should not be run in reverse
one_way_test_cases = [
    (
        'switch places',
        '<h1>one</h1><h2>two</h2>',
        '<h2>two</h2><h1>one</h1>',
        '<ins><h2>two</h2></ins><h1>one</h1><del><h2>two</h2></del>',
    ),
    (
        'switch places, near match',
        '<h1>one one</h1><h2>two two</h2>',
        '<h2>two two x</h2><h1>one one yyy</h1>',
        '<ins><h2>two two x</h2></ins><h1>one one<ins> yyy</ins></h1><del><h2>two two</h2></del>',
    ),
]

# test cases that don't pass sanity checking
insane_test_cases = [
    (
        'add a table cell',
        '<table><tr><td>... A</td></tr></table>',
        '<table><tr><td>... A</td><td>B</td></tr></table>',
        '<table><tr><td>... A</td><td><ins>B</ins></td></tr></table>',
    ),
    (
        'add a table row',
        '<table><tr><td>... A</td></tr></table>',
        '<table><tr><td>... A</td></tr><tr><td>B</td></tr></table>',
        '<table><tr><td>... A</td></tr><tr><td><ins>B</ins></td></tr></table>',
    ),
    (
        'add table rows and cells, to the bottom and right',
        '<table><tr><td>... A</td></tr></table>',
        '<table><tr><td>... A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></table>',
        '<table><tr><td>... A</td><td><ins>B</ins></td></tr><tr><td><ins>C</ins></td><td><ins>D</ins></td></tr></table>',
    ),
    (
        'add table rows and cells, to the up and left',
        '<table><tr><td>... D</td></tr></table>',
        '<table><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>... D</td></tr></table>',
        '<table><tr><td><ins>A</ins></td><td><ins>B</ins></td></tr><tr><td><ins>C</ins></td><td>... D</td></tr></table>',
    ),
    (
        'delete a table cell',
        '<table><tr><td>... A</td><td>B</td></tr></table>',
        '<table><tr><td>... A</td></tr></table>',
        '<table><tr><td>... A</td><td><del>B</del></td></tr></table>',
    ),
    (
        'delete a table row',
        '<table><tr><td>... A</td></tr><tr><td>B</td></tr></table>',
        '<table><tr><td>... A</td></tr></table>',
        '<table><tr><td>... A</td></tr><tr><td><del>B</del></td></tr></table>',
    ),
    (
        'delete top row and add a column',
        '<table><tr><td>A1</td></tr><tr><td>... B1</td></tr></table>',
        '<table><tr><td>... B1</td><td>B2</td></tr></table>',
        '<table><tr><td><del>A1</del></td></tr><tr><td>... B1</td><td><ins>B2</ins></td></tr></table>',
    ),
    (
        'delete top row and add a column, funny whitespace',
        '<table> <tr><td>A1</td></tr> <tr><td>... B1</td></tr> </table>',
        '<table> <tr><td>... B1</td><td>B2</td></tr> </table>',
        ('<table><tr><td><del>A1</del></td></tr><tr><td>... B1</td>'
         '<td><ins>B2</ins></td></tr></table>'),
    ),
    (
        'handle newline-separated words correctly',
        '<p>line one\nline two</p>',
        '<p>line one line two</p>',
        '<p>line one line two</p>',
    ),
#    (
#        'ignore adding attributes',
#        '<h1>one</h1>',
#        '<h1 id="ignore" class="ignore">one</h1>',
#        '<h1>one</h1>',
#    ),
#    (
#        'ignore deleting attributes',
#        '<h1 id="ignore" class="ignore">one</h1>',
#        '<h1>one</h1>',
#        '<h1 id="ignore" class="ignore">one</h1>',
#    ),
    (
        'whitespace changes in a table with colspan',
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
    ),
    (
        'whitespace changes in a table with nbsp entity',
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
    ),
#BROKEN, see issue #2384
#    # ul and ol tags are considered equal when diffing
#    (
#        '<ul><li>X</li></ul>',
#        '<ol><li>X</li></ol>',
#        '<ol><li>X</li></ol>',
#    ),
#    (
#        '<ol><li>X</li></ol>',
#        '<ul><li>X</li></ul>',
#        '<ul><li>X</li></ul>',
#    ),
]

# Assemble test cases
# add reverse test cases
# switch the old and new html, and reverse the changes
def reverse_cases(cases):
    for case in parse_cases(cases):
        yield (
            case.name + ' (reverse)',
            case.new_html,
            case.old_html,
            reverse_changes_html(case.target_changes),
            reverse_edit_script(case.edit_script),
        )
reverse_test_cases = list(reverse_cases(test_cases))

# Combined cases
all_test_cases = (test_cases +
                  reverse_test_cases +
                  one_way_test_cases +
                  insane_test_cases)

def assert_html_equal(a_html, b_html):
    assert html_equal(a_html, b_html), (
        u'These html documents are not equal:\n%r\n====\n%r' % (a_html, b_html))

def assert_html_not_equal(a_html, b_html):
    assert not html_equal(a_html, b_html), (
        u'These html documents should not be equal:\n%r\n====\n%r' % (a_html, b_html))

def assert_strip_changes(old_html, new_html, changes):
    assert_html_equal(old_html, strip_changes_old(changes))
    assert_html_equal(new_html, strip_changes_new(changes))

def test_parse_comments():
    assert_html_equal(
        minidom_tostring(parse_minidom('<!-- -->')),
        '',
    )
    assert_html_equal(
        minidom_tostring(parse_minidom('<!--\n-->')),
        '',
    )
    assert_html_equal(
        minidom_tostring(parse_minidom('<p>stuff<!-- \n -->stuff</p>')),
        '<p>stuffstuff</p>',
    )

def test_html_equal():
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
        assert_html_equal(a_html, b_html)

def test_html_not_equal():
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
        assert_html_not_equal(a_html, b_html)

def test_remove_attributes():
    remove_attributes_cases = [
        ('<h1>one</h1>',
         '<h1>one</h1>'),
        ('<h1 class="test">one</h1>',
         '<h1>one</h1>'),
        ('<h1 id="test-heading" class="test">one</h1>',
         '<h1>one</h1>'),
        ('<div>before <h1 id="test-heading" class="test">one</h1> after </div>',
         '<div>before <h1>one</h1> after </div>'),
        (u'<h1 class="test">über</h1>',
         u'<h1>über</h1>'),
    ]
    for html, stripped_html, in remove_attributes_cases:
        assert_html_equal(remove_attributes(html), stripped_html)

def test_edit_script():
    # edit script output does not reverse easily, don't test the reverse cases
    for case in parse_cases(test_cases + one_way_test_cases):
        if not case.edit_script:
            continue
        def test():
            actual_edit_script = get_edit_script(case.old_html, case.new_html)
            assert_equal(
                case.edit_script,
                actual_edit_script,
                ('These edit scripts do not match:\n%s\n!=\n%s'
                 % (pformat(case.edit_script), pformat(actual_edit_script))),
            )
        test.description = 'test_edit_script - %s' % case.name
        yield test

def test_html_patch():
    for case in parse_cases(all_test_cases):
        # check that applying the diff gives back the same new_html
        def test():
            edit_script = []
            edit_script = get_edit_script(case.old_html, case.new_html)
            edited_html = html_patch(case.old_html, edit_script)
            assert_html_equal(
                remove_attributes(edited_html),
                remove_attributes(case.new_html),
            )
        test.description = 'test_html_patch - %s' % case.name
        yield test

def test_cases_sanity():
    # check that removing the ins and del markup gives the original
    sane_cases = (test_cases + reverse_test_cases + one_way_test_cases)
    for case in parse_cases(sane_cases):
        def test():
            assert_strip_changes(case.old_html, case.new_html, case.target_changes)
        test.description = 'test_cases_sanity - %s' % case.name
        yield test

def test_html_diff():
    for case in parse_cases(all_test_cases):
        def test():
            changes = diff(case.old_html, case.new_html, cutoff=0.0)
            assert_html_equal(changes, case.target_changes)
        test.description = 'test_html_diff - %s' % case.name
        yield test
