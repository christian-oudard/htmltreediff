from htmltreediff.text import split_text
from htmltreediff.util import (
    is_text,
    is_element,
    ancestors,
    walk_dom,
    remove_node,
    insert_or_append,
    wrap,
    wrap_inner,
    unwrap,
)
from htmltreediff.diff_core import Differ
from htmltreediff.edit_script_runner import EditScriptRunner

def split_text_nodes(dom):
    for text_node in list(walk_dom(dom)):
        if not is_text(text_node):
            continue
        split_node(text_node)

def split_node(node):
    # Split text node in into user-friendly chunks.
    pieces = split_text(node.nodeValue)
    if len(pieces) <= 1:
        return
    parent = node.parentNode
    for piece in pieces:
        piece_node = node.ownerDocument.createTextNode(piece)
        parent.insertBefore(piece_node, node)
    remove_node(node)

def dom_diff(old_dom, new_dom):
    # Split all the text nodes in the old and new dom.
    split_text_nodes(old_dom)
    split_text_nodes(new_dom)

    # Get the edit script from the diff algorithm
    differ = Differ(old_dom, new_dom)
    edit_script = differ.get_edit_script()
    # Run the edit script, then use the inserted and deleted nodes metadata to
    #     show changes.
    runner = EditScriptRunner(old_dom, edit_script)
    dom = runner.run_edit_script()
    add_changes_markup(dom, runner.ins_nodes, runner.del_nodes)
    return dom

def add_changes_markup(dom, ins_nodes, del_nodes):
    """
    Add <ins> and <del> tags to the dom to show changes.
    """
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

