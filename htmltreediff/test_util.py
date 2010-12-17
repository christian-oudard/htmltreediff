from copy import copy

from htmltreediff.html_diff import HtmlDiffer
from htmltreediff.edit_script_runner import EditScriptRunner
from htmltreediff.html import (
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

def html_diff(old_html, new_html):
    differ = HtmlDiffer(parse_minidom(old_html), parse_minidom(new_html))
    return differ.get_edit_script()

def html_patch(old_html, edit_script):
    runner = EditScriptRunner(parse_minidom(old_html), edit_script)
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

def fix_node_locations(test_cases):
    """Fix node locations in test cases."""
    for old_html, new_html, target_changes, edit_script in copy(test_cases):
        new_edit_script = []
        for action, location, node_properties in edit_script:
            location = [1] + location # account for auto-added head and body elements
            new_edit_script.append((
                action,
                location,
                node_properties,
            ))
        yield (
            old_html,
            new_html,
            target_changes,
            new_edit_script,
        )
