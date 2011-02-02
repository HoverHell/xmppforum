#!/usr/bin/env python
"""
creates/updates (refreshes) a bootstrap.py script
"""

import os
import subprocess

here = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(here)
# In the current dir.
script_name = os.path.join(here, 'bootstrap.py')

import virtualenv


EXTRA_TEXT = """

DEFDIR = "ENV"  # default target directory for virtualenv.
INST_BASE = 'inst/'  # location of req-.txt files.

def extend_parser(parser):
    parser.add_option(
        '-c', action="store_true", dest='cinstall',
        help=('Install all known depencencies, which requires GCC and is '
          'not generally preferrable.'))
    parser.add_option(
        '-d', action="store_true", dest='dinstall',
        help=('Install only dependencies not found in Debian. See INSTALL '
          'for the list of packages you will need to install. '
          'Overrides `-c`.'))

def adjust_options(options, args):
    # Default subdirectory.
    if args == []:
        args.append(DEFDIR)


def after_install(options, home_dir):
    if sys.platform == 'win32':
        bin = 'Scripts'
    else:
        bin = 'bin'
    # shortcut to call "python pip install ..."
    # ! relative path to "requirements.txt", though.
    # explicit path to the python should not be required, but is generally
    # more safe (will rather fail than do wronf stuff).
    rpip = lambda x: subprocess.call([join(home_dir, bin, 'python'),
      join(home_dir, bin, 'pip'), 'install', '-U', '-r', INST_BASE + x])

    if options.dinstall:
        print " ------- Installing minimal requirements."
        rpip('requirements-d.txt')
    else:
        print " ------- Installing basic requirements."
        rpip('requirements.txt')
        if options.cinstall:
            print " ------- Installing C-based requirements."
            rpip('requirements-c.txt')
"""

def main():
    text = virtualenv.create_bootstrap_script(EXTRA_TEXT)
    if os.path.exists(script_name):
        f = open(script_name)
        cur_text = f.read()
        f.close()
        print 'Previous (len): %r' % len(cur_text)
    else:
        print 'No previous file found.'
        cur_text = ''
    print 'Updating %s' % script_name
    if cur_text == text:
        print 'No update'
    else:
        print 'Script changed; updating...'
        print 'New (len): %r' % len(text)
        f = open(script_name, 'w')
        f.write(text)
        f.close()

if __name__ == '__main__':
    main()
