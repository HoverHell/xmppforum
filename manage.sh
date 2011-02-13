#!/bin/sh
cd "$(dirname $0)"  # does not care about symlinks to self, though.
./ENV/bin/python ./manage.py "$@"
