#!/bin/sh
set -e
cd "$(dirname "$0")"

VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' kytchen/__init__.py)

pyinstaller --noconfirm --clean --windowed \
    --name Kytchen \
    --osx-bundle-identifier ink.sgc.kytchen \
    script.py

#--icon=kytchen/kytchen.png \
#--add-data="kytchen/kytchen.png:kytchen" \
