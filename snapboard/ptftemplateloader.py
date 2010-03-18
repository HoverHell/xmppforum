"""
Wrapper for loading plaintextformat templates from the filesystem, e.g. with
stripping unnecessary newlines and spaces from it.
"""

from django.template.loaders.filesystem import load_template_source

# Plan: Load a teamplate with load_template_source and then strip it.
