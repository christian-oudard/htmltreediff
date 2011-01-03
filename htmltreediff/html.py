import re, cgi
from collections import defaultdict
from xml.dom import minidom

from htmltreediff.text import text_changes, wrap_html, PlaceholderMatcher
from htmltreediff.util import (
    is_text,
    is_element,
    ancestors,
    walk_dom,
    remove_node,
    insert_or_append,
    remove_text_section,
    wrap,
    wrap_inner,
    unwrap,
)

def add_changes_markup(dom, ins_nodes, del_nodes):
    """
    Add <ins> and <del> tags to the dom to show changes.
    """
    # find text-only changes
    text_only = []
    del_locations = defaultdict(list)
    ins_locations = defaultdict(list)
    for node in del_nodes:
        del_locations[(node.orig_parent, node.orig_next_sibling)].append(node)
    for node in ins_nodes:
        ins_locations[(node.orig_parent, node.orig_next_sibling)].append(node)
    for location, del_node_list in del_locations.items():
        parent, next_sibling = location
        if not location in ins_locations:
            continue # must be deleted and inserted in same location
        ins_node_list = ins_locations[location]
        if not (any(is_text(n) for n in del_node_list) and
                any(is_text(n) for n in ins_node_list)):
            continue # must be at least one text node on each side
        # remove the changed nodes from the original lists
        for node in del_node_list:
            del_nodes.remove(node)
        for node in ins_node_list:
            ins_nodes.remove(node)
            # remove inserted nodes from dom too
            assert node.parentNode is not None
            remove_node(node)
        # represent elements as placeholder strings, and replace them with
        # the real objects later
        node_placeholders = {}
        def strvalue(node):
            if is_text(node):
                s = node.nodeValue
            else:
                r = repr(node)
                node_placeholders[r] = node
                s = '{{{' + r + '}}}'
            return cgi.escape(s)
        old_text = ''.join(strvalue(n) for n in reversed(del_node_list))
        new_text = ''.join(strvalue(n) for n in ins_node_list)
        text_only.append((
            old_text,
            new_text,
            parent,
            next_sibling,
            node_placeholders,
        ))
    # add markup for text-only changes
    for old_text, new_text, parent, next_sibling, node_placeholders in text_only:
        diff = text_changes(old_text, new_text, matcher_class=PlaceholderMatcher)
        # parse the diff
        diff = wrap_html(diff, 'diff')
        diff_dom = minidom.parseString(diff.encode('utf-8'))
        diff_nodes = list(diff_dom.documentElement.childNodes)
        # apply the diff
        for diff_node in diff_nodes:
            # insert the diff into the document
            insert_or_append(parent, diff_node, next_sibling)
            # put the old objects back in their place
            for text_node in list(walk_dom(diff_node)):
                if not is_text(text_node):
                    continue
                # there might be multiple placeholders in each text node
                while True:
                    m = re.search(r'{{{(.*?)}}}', text_node.nodeValue)
                    if not m:
                        break
                    real_node = node_placeholders[m.group(1)]
                    before_, deleted_, after = remove_text_section(text_node, m.start(), m.end())
                    insert_or_append(after.parentNode, real_node, after)
                    text_node = after
    # add markup for inserted and deleted sections
    for node in reversed(del_nodes):
        # diff algorithm deletes nodes in reverse order, so un-reverse the
        # order for this iteration
        insert_or_append(node.orig_parent, node, node.orig_next_sibling)
        wrap(node, 'del')
    for node in ins_nodes:
        wrap(node, 'ins')
    # Perform post-processing and cleanup.
    remove_nesting(dom, 'del')
    remove_nesting(dom, 'ins')
    sort_del_before_ins(dom)
    merge_adjacent(dom, 'del')
    merge_adjacent(dom, 'ins')
    fix_lists(dom)
    fix_tables(dom)

def remove_nesting(dom, tag_name):
    """
    Unwrap items in the node list that have ancestors with the same tag.
    """
    for node in dom.getElementsByTagName(tag_name):
        for ancestor in ancestors(node):
            if ancestor is node:
                continue
            if ancestor is dom.documentElement:
                break
            if ancestor.tagName == tag_name:
                unwrap(node)
                break

def sort_nodes(dom, cmp_func):
    """
    Sort the nodes of the dom in-place, based on a comparison function.
    """
    dom.normalize()
    for node in list(walk_dom(dom, elements_only=True)):
        prev_sib = node.previousSibling
        while prev_sib and cmp_func(prev_sib, node) == 1:
            node.parentNode.insertBefore(node, prev_sib)
            prev_sib = node.previousSibling

def sort_del_before_ins(dom):
    def node_cmp(a, b):
        try:
            if a.tagName == 'del' and b.tagName == 'ins':
                return -1
            if a.tagName == 'ins' and b.tagName == 'del':
                return 1
        except AttributeError:
            pass
        return 0
    sort_nodes(dom, cmp_func=node_cmp)

def merge_adjacent(dom, tag_name):
    """
    Merge all adjacent tags with the specified tag name.
    Return the number of merges performed.
    """
    for node in dom.getElementsByTagName(tag_name):
        prev_sib = node.previousSibling
        if prev_sib and prev_sib.nodeName == node.tagName:
            for child in list(node.childNodes):
                prev_sib.appendChild(child)
            remove_node(node)

def distribute(node):
    """
    Wrap a copy of the given element around the contents of each of its
    children, removing the node in the process.
    """
    children = list(c for c in node.childNodes if is_element(c))
    unwrap(node)
    tag_name = node.tagName
    for c in children:
        wrap_inner(c, tag_name)

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

def _strip_changes_new(node):
    for ins_node in node.getElementsByTagName('ins'):
        unwrap(ins_node)
    for del_node in node.getElementsByTagName('del'):
        remove_node(del_node)

def _strip_changes_old(node):
    for ins_node in node.getElementsByTagName('ins'):
        remove_node(ins_node)
    for del_node in node.getElementsByTagName('del'):
        unwrap(del_node)
