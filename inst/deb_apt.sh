#!/bin/sh
# Ubuntoids don't have aptitudes by default (bleh.), so at least this script
# will work.
  sudo apt-get install python-django python-imaging python-wokkel \
    python-django-treebeard python-django-registration python-simplejson
    python-html2text git
## for the fun (or DRY):
# $(sed -rn '/aptitude install/ { s/aptitude/apt-get/; :b s/\\//; p; n; /[^ ]/ b b; }' ../doc/INSTALL)
