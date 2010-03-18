# -*- coding: utf-8 -*-
'''
Template tags for explicit space and newline. Intended to be used with
plaintextformat loader.
'''

from django.template import Library

import re

register = Library()


def br():
    return "\n"
br = register.simple_tag(br)


def ws():
    return " "
ws = register.simple_tag(ws)
