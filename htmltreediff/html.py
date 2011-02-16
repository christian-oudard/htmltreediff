from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    unwrap,
    wrap_inner,
    remove_node,
    tree_text_ratio,
)
from htmltreediff.changes import dom_diff, distribute

def diff(old_html, new_html, cutoff=0.0, html=True, pretty=False):
    """Show the differences between the old and new html document, as html.

    Return the document html with extra tags added to show changes. Add <ins>
    tags around newly added sections, and <del> tags to show sections that have
    been deleted.
    """
    old_dom = parse_minidom(old_html, html=html)
    new_dom = parse_minidom(new_html, html=html)

    # If the two documents are not similar enough, don't show the changes.
    ratio = tree_text_ratio(old_dom, new_dom)
    if ratio < cutoff:
        return '<h2>The differences from the previous version are too large to show concisely.</h2>'

    dom = dom_diff(old_dom, new_dom)

    # HTML-specific cleanup.
    if html:
        fix_lists(dom)
        fix_tables(dom)

    # Only return html for the document body contents.
    body_elements = dom.getElementsByTagName('body')
    if len(body_elements) == 1:
        dom = body_elements[0]

    return minidom_tostring(dom, pretty=pretty)

def fix_lists(dom):
    # <ins> and <del> tags are not allowed within <ul> or <ol> tags.
    # Move them to the nearest li, so that the numbering isn't interrupted.

    # Find all del > li and ins > li sets.
    del_tags = set()
    ins_tags = set()
    for node in list(dom.getElementsByTagName('li')):
        parent = node.parentNode
        if parent.tagName == 'del':
            del_tags.add(parent)
        elif parent.tagName == 'ins':
            ins_tags.add(parent)
    # Change ins > li into li > ins.
    for ins_tag in ins_tags:
        distribute(ins_tag)
    # Change del > li into li.del-li > del.
    for del_tag in del_tags:
        children = list(del_tag.childNodes)
        unwrap(del_tag)
        for c in children:
            if c.nodeName == 'li':
                c.setAttribute('class', 'del-li')
                wrap_inner(c, 'del')

def fix_tables(dom):
    # Show table row insertions
    tags = set()
    for node in list(dom.getElementsByTagName('tr')):
        parent = node.parentNode
        if parent.tagName in ('ins', 'del'):
            tags.add(parent)
    for tag in tags:
        distribute(tag)
    # Show table cell insertions
    tags = set()
    for node in list(dom.getElementsByTagName('td') +
                     dom.getElementsByTagName('th')):
        parent = node.parentNode
        if parent.tagName in ('ins', 'del'):
            tags.add(parent)
    for tag in tags:
        distribute(tag)
    # All other ins and del tags inside a table but not in a cell are invalid,
    # so remove them.
    for node in list(dom.getElementsByTagName('ins') +
                     dom.getElementsByTagName('del')):
        parent = node.parentNode
        if parent.tagName in ['table', 'tbody', 'thead', 'tfoot', 'tr']:
            remove_node(node)

