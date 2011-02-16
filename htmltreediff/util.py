import re
from textwrap import dedent
import html5lib
from html5lib import treebuilders
from xml.dom import minidom, Node

from htmltreediff.text import WordMatcher

## DOM utilities ##
# parsing and cleaning #
from xml.dom.pulldom import SAX2DOM
import lxml.html, lxml.etree, lxml.sax
def parse_lxml_dom(xml, html=True):
    if html:
        parse_func = lxml.html.document_fromstring
    else:
        parse_func = lxml.etree.fromstring
    try:
        tree = parse_func(xml)
    except lxml.etree.XMLSyntaxError:
        tree = parse_func('<body>%s</body>' % xml)

    handler = SAX2DOM()
    lxml.sax.saxify(tree, handler)
    return handler.document

def parse_minidom(xml, clean=True, html=True):
    html_parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder('dom'))
    # Preprocessing
    xml = remove_comments(xml)
    if clean:
        xml = remove_newlines(xml)
        xml = normalize_entities(xml)
    xml = xml.strip()

    # Parse
    dom = parse_lxml_dom(xml, html=html)

    if clean:
        if html:
            remove_insignificant_text_nodes(dom)
        # clean up irrelevant content
        for node in list(walk_dom(dom)):
            if node.nodeType == Node.COMMENT_NODE:
                remove_node(node)
            elif node.nodeName == 'style':
                remove_node(node)
            elif node.nodeName == 'font':
                unwrap(node)
            elif node.nodeName == 'span':
                unwrap(node)
    dom.normalize()

    # Make sure that the body element is the top of the dom.
    for head_element in dom.getElementsByTagName('head'):
        remove_node(head_element)
    for html_element in dom.getElementsByTagName('html'):
        unwrap(html_element)
    if not dom.documentElement:
        dom = parse_lxml_dom('', html=False)

    if html:
        assert dom.documentElement.tagName == 'body'

    return dom

def remove_comments(xml):
    """
    Remove comments, as they can break the xml parser.

    See html5lib issue #122 ( http://code.google.com/p/html5lib/issues/detail?id=122 ).

    >>> remove_comments('<!-- -->')
    ''
    >>> remove_comments('<!--\\n-->')
    ''
    >>> remove_comments('<p>stuff<!-- \\n -->stuff</p>')
    '<p>stuffstuff</p>'
    """
    regex = re.compile(r'<!--.*?-->', re.DOTALL)
    return regex.sub('', xml)

def remove_newlines(xml):
    r"""Remove newlines in the xml.

    If the newline separates words in text, then replace with a space instead.

    >>> remove_newlines('<p>para one</p>\n<p>para two</p>')
    '<p>para one</p><p>para two</p>'
    >>> remove_newlines('<p>line one\nline two</p>')
    '<p>line one line two</p>'
    >>> remove_newlines('one\n1')
    'one 1'
    >>> remove_newlines('hey!\nmore text!')
    'hey! more text!'
    """
    # Normalize newlines.
    xml = xml.replace('\r\n', '\n')
    xml = xml.replace('\r', '\n')
    # Remove newlines that don't separate text. The remaining ones do separate text.
    xml = re.sub(r'(?<=[>\s])\n(?=[<\s])', '', xml)
    xml = xml.replace('\n', ' ')
    return xml.strip()

def minidom_tostring(dom, pretty=False):
    if pretty:
        xml = dom.toprettyxml()
    else:
        xml = dom.toxml()
    xml = remove_xml_declaration(xml)
    if xml == '<body/>':
        return ''
    if xml.startswith('<body>') and xml.endswith('</body>'):
        xml = xml[len('<body>'):-len('</body>')]
    xml = dedent(xml.replace('\t', '  ')).strip()
    return xml

def html_equal(a_html, b_html):
    if a_html == b_html:
        return True
    a_dom = parse_minidom(a_html)
    b_dom = parse_minidom(b_html)
    return HashableTree(a_dom.documentElement) == HashableTree(b_dom.documentElement)

class HashableNode(object):
    def __init__(self, node):
        self.node = node

    def __eq__(self, other):
        return (self.node.nodeType == other.node.nodeType and
                self.node.nodeName == other.node.nodeName and
                self.node.nodeValue == other.node.nodeValue and
                attribute_dict(self.node) == attribute_dict(other.node))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        attributes = frozenset(attribute_dict(self.node).items())
        return hash((self.node.nodeType,
                     self.node.nodeName,
                     self.node.nodeValue,
                     attributes))

class HashableTree(object):
    def __init__(self, node):
        self.node = node

    def __eq__(self, other):
        return (HashableNode(self.node) == HashableNode(other.node) and
                [HashableTree(c) for c in self.node.childNodes] ==
                [HashableTree(c) for c in other.node.childNodes])

    def __hash__(self):
        child_hashes = hash(tuple(HashableTree(c) for c in self.node.childNodes))
        return hash((HashableNode(self.node), child_hashes))

class FuzzyHashableTree(object):
    cutoff = 0.4

    def __init__(self, node):
        self.node = node

    def __eq__(self, other):
        if HashableNode(self.node) != HashableNode(other.node):
            return False

        # Check for an exact tree match.
        if HashableTree(self.node) == HashableTree(other.node):
            return True

        # Check for a fuzzy match.
        ratio = tree_text_ratio(self.node, other.node)
        if ratio >= self.cutoff:
            return True

        return False

    def __hash__(self):
        # This will never be equal if the top level tag in the tree is
        # different. Beyond that, we can't make any guarantees.
        return hash(HashableNode(self.node))


def attribute_dict(node):
    if not node.attributes:
        return {}
    d = dict(node.attributes)
    for key, node in list(d.items()):
        d[key] = node.value
    return d

def normalize_entities(html):
    # turn &nbsp; and aliases into normal spaces
    html = html.replace(u'&nbsp;', u' ')
    html = html.replace(u'&#160;', u' ')
    html = html.replace(u'&#xA0;', u' ')
    html = html.replace(u'\xa0', u' ')
    return html

def remove_xml_declaration(xml):
    # remove the xml declaration, it messes up diffxml
    return re.sub(r'<\?xml.*\?>', '', xml).strip()

def remove_dom_attributes(dom):
    for node in walk_dom(dom):
        for key in attribute_dict(node).keys():
            node.attributes.removeNamedItem(key)

_non_text_node_tags = [
    'html', 'head', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'colgroup',
    'col', 'ul', 'ol', 'dl', 'select', 'img', 'br', 'hr',
]
def remove_insignificant_text_nodes(dom):
    """
    For html elements that should not have text nodes inside them, remove all
    whitespace. For elements that may have text, collapse multiple spaces to a
    single space.
    """
    nodes_to_remove = []
    for node in walk_dom(dom):
        if is_text(node):
            text = node.nodeValue
            if node.parentNode.tagName in _non_text_node_tags:
                nodes_to_remove.append(node)
            else:
                node.nodeValue = re.sub(r'\s+', ' ', text)
    for node in nodes_to_remove:
        remove_node(node)

# information #
def is_text(node):
    return node.nodeType == Node.TEXT_NODE

def is_element(node):
    return node.nodeType == Node.ELEMENT_NODE

def get_child(parent, child_index):
    """
    Get the child at the given index, or return None if it doesn't exist.
    """
    if child_index < 0 or child_index >= len(parent.childNodes):
        return None
    return parent.childNodes[child_index]

def get_location(dom, location):
    """
    Get the node at the specified location in the dom.
    Location is a sequence of child indices, starting at the children of the
    root element. If there is no node at this location, raise a ValueError.
    """
    node = dom.documentElement
    for i in location:
        node = get_child(node, i)
        if not node:
            raise ValueError('Node at location %s does not exist.' % location)
    return node

def ancestors(node):
    ancestor = node
    while ancestor:
        yield ancestor
        ancestor = ancestor.parentNode

def walk_dom(dom, elements_only=False):
    # allow calling this on a document as well as as node
    if hasattr(dom, 'documentElement'):
        dom = dom.documentElement
    def walk(node):
        if not node:
            return
        if elements_only and not is_element(node):
            return
        yield node
        for child in node.childNodes:
            for descendant in walk(child):
                yield descendant
    return walk(dom)

def tree_text(node):
    """Return all the text below the given node as a single string.

    >>> unicode(tree_text(parse_minidom('<h1>one</h1>two<div>three<em>four</em></div>')))
    u'one two three four'
    """
    text_list = []
    for descendant in walk_dom(node):
        if is_text(descendant):
            text_list.append(descendant.nodeValue)
    return ' '.join(text_list)

def tree_text_ratio(a_dom, b_dom):
    """Compare two dom trees for text similarity, as a ratio."""
    matcher = _text_matcher(a_dom, b_dom)
    return matcher.text_ratio()

def _text_matcher(a_dom, b_dom):
    return WordMatcher(
        a=tree_text(a_dom),
        b=tree_text(b_dom),
    )

# manipulation #
def copy_dom(dom):
    new_dom = minidom.Document()
    doc = new_dom.importNode(dom.documentElement, deep=True)
    new_dom.documentElement = doc
    return new_dom

def remove_node(node):
    """
    Remove the node from the dom. If the node has no parent, raise an error.
    """
    node.parentNode.removeChild(node)

def insert_or_append(parent, node, next_sibling):
    """
    Insert the node before next_sibling, at the specified character index. If
    next_sibling is None, append the node last instead. If the insert split a
    text node, return the previous and next siblings of the newly inserted
    node.
    """
    # simple insert
    if next_sibling:
        parent.insertBefore(node, next_sibling)
    else:
        parent.appendChild(node)

def wrap(node, tag):
    """Wrap the given tag around a node."""
    wrap_node = node.ownerDocument.createElement(tag)
    parent = node.parentNode
    if parent:
        parent.replaceChild(wrap_node, node)
    wrap_node.appendChild(node)
    return wrap_node

def wrap_inner(node, tag):
    """Wrap the given tag around the contents of a node."""
    children = list(node.childNodes)
    wrap_node = node.ownerDocument.createElement(tag)
    for c in children:
        wrap_node.appendChild(c)
    node.appendChild(wrap_node)

def unwrap(node):
    """Remove a node, replacing it with its children."""
    for child in list(node.childNodes):
        node.parentNode.insertBefore(child, node)
    remove_node(node)
