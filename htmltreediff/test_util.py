from htmltreediff.diff_core import Differ
from htmltreediff.edit_script_runner import EditScriptRunner
from htmltreediff.changes import (
    split_text_nodes,
    sort_del_before_ins,
    _strip_changes_new,
    _strip_changes_old,
)
from htmltreediff.util import (
    parse_minidom,
    minidom_tostring,
    remove_dom_attributes,
)

def reverse_edit_script(edit_script):
    if edit_script is None:
        return None
    def opposite_action(action):
        if action == 'delete':
            return 'insert'
        elif action == 'insert':
            return 'delete'
    reverse_script = []
    for action, location, node_properties in reversed(edit_script):
        reverse_script.append((opposite_action(action), location, node_properties))
    return reverse_script

def reverse_changes_html(changes):
    dom = parse_minidom(changes)
    reverse_changes(dom)
    return minidom_tostring(dom)

def reverse_changes(dom):
    for node in dom.getElementsByTagName('del') + dom.getElementsByTagName('ins'):
        if node.tagName == 'del':
            node.tagName = 'ins'
        elif node.tagName == 'ins':
            node.tagName = 'del'
    sort_del_before_ins(dom)

def get_edit_script(old_html, new_html):
    old_dom = parse_minidom(old_html)
    new_dom = parse_minidom(new_html)
    split_text_nodes(old_dom)
    split_text_nodes(new_dom)
    differ = Differ(old_dom, new_dom)
    return differ.get_edit_script()

def html_patch(old_html, edit_script):
    old_dom = parse_minidom(old_html)
    split_text_nodes(old_dom)
    runner = EditScriptRunner(old_dom, edit_script)
    return minidom_tostring(runner.run_edit_script())

def strip_changes_old(html):
    dom = parse_minidom(html)
    _strip_changes_old(dom)
    return minidom_tostring(dom)

def strip_changes_new(html):
    dom = parse_minidom(html)
    _strip_changes_new(dom)
    return minidom_tostring(dom)

def remove_attributes(html):
    dom = parse_minidom(html)
    remove_dom_attributes(dom)
    return minidom_tostring(dom)

def collapse(html):
    """Remove any indentation and newlines from the html."""
    return ''.join([line.strip() for line in html.split('\n')]).strip()

class Case(object):
    pass

def parse_cases(cases):
    for args in cases:
        case = Case()
        if len(args) == 4:
            case.name, case.old_html, case.new_html, case.target_changes = args
            case.edit_script = None
        else:
            case.name, case.old_html, case.new_html, case.target_changes, case.edit_script = args
        yield case
