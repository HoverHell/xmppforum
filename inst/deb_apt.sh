#!/bin/sh

## For the versatility!
# (alternatives from worst to best)
sucmd(){ echo "Doing su to root."; su -c "$*" }
which sudo && sucmd(){ echo "Sudoing to root."; sudo "$@" }
[ "$(id -u)" -eq 0 ] && sucmd(){ "$@" }

aptcmd="apt-get"
which aptitude > /dev/null && aptcmd="aptitude"

sucmd "$aptcmd" install python-django python-imaging python-wokkel \
    python-django-treebeard python-django-registration python-simplejson \
    python-html2text git

## for the fun (or DRY):
# $(sed -rn '/aptitude install/ { s/aptitude/apt-get/; :b s/\\//; p; n; /[^ ]/ b b; }' ../doc/INSTALL)
