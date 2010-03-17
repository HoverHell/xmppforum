# -*- coding: utf-8 -*-
'''
Template tags for careful formatting of output, in particular - specifying
whitespaces and newlines carefully while keeping clear formatting of
template code itself.
'''

from django.template import Node, Library
from django.template import TextNode

#from django.template import NodeList, Template, Context, Variable

import re

import sys  # Debug, actually.

register = Library()


class PlainfilterNode(Node):
    def __init__(self, nodelist):
        # ? Something like '}\s+{' might actually be needed.
        self.nodelist = nodelist
        self.spacere = re.compile('\s\s+')
        self.newlinere = re.compile('\n')
        pass

    def render(self, context):
        sys.stderr.write(" D: PlainfilterNode render: nodelist: \n")
        try:
            sys.stderr.write("    %r " % self.nodelist)
            sys.stderr.write("    contains_nontext: " \
              "%r " % self.nodelist.contains_nontext)
        except:
            pass
        for node in self.nodelist:
            if isinstance(node, TextNode):
                sys.stderr.write(" TextNode: %r.\n" % node)
                node.s = self.spacere.sub(u'',
                  self.newlinere.sub(u'', node.s))
            else:
                pass  # SH-
        return self.nodelist.render(context)


def plainfilter(parser, token):
    """
    Removes whitespaces.

    Actually, it removes two or more whitespaces, allowing less obvious but
    more convenient control.

    Intended to be used with # ! newline/whitespace tags.
    """
    nodelist = parser.parse(('endplainfilter', ))
    parser.delete_first_token()  # Deletes 'endplainfilter' tag.
    return PlainfilterNode(nodelist)
plainfilter = register.tag(plainfilter)


def br():
    return "\n"
br = register.simple_tag(br)


def ws():
    return " "
ws = register.simple_tag(ws)
