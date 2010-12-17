from xml.dom import Node

from htmltreediff.util import (
    get_child,
    get_location,
    remove_node,
    insert_or_append,
)

class EditScriptRunner(object):
    def __init__(self, dom, edit_script):
        self.dom = dom
        self.edit_script = edit_script
        self.del_nodes = []
        self.ins_nodes = []

    # edit script actions #
    def action_delete(self, node):
        parent = node.parentNode
        next_sibling = node.nextSibling
        remove_node(node)
        node.orig_parent = parent
        node.orig_next_sibling = next_sibling
        self.del_nodes.append(node)

    def action_insert(self, parent, child_index,
                      node_type=None, node_name=None, node_value=None, attributes=None):
        if node_type == Node.ELEMENT_NODE:
            node = self.dom.createElement(node_name)
            if attributes:
                for key, value in attributes.items():
                    node.setAttribute(key, value)
        elif node_type == Node.TEXT_NODE:
            node = self.dom.createTextNode(node_value)
        self.action_insert_node(parent, child_index, node)

    def action_insert_node(self, parent, child_index, node):
        previous_sibling = get_child(parent, child_index - 1)
        next_sibling = get_child(parent, child_index)
        insert_or_append(parent, node, next_sibling)
        # add node to ins_nodes
        assert node.parentNode is not None
        node.orig_parent = parent
        node.orig_next_sibling = next_sibling
        self.ins_nodes.append(node)

    # script running #
    def run_edit_script(self):
        """
        Run an xml edit script, and return the new html produced.
        """
        for action, location, properties in self.edit_script:
            if action == 'delete':
                node = get_location(self.dom, location)
                self.action_delete(node)
            elif action == 'insert':
                parent = get_location(self.dom, location[:-1])
                child_index = location[-1]
                self.action_insert(parent, child_index, **properties)
        return self.dom
