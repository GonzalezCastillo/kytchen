#!/bin/sh
set -e
cd "$(dirname "$0")"

pyinstaller --noconfirm --clean --windowed \
    --name Kytchen \
    --osx-bundle-identifier ink.sgc.kytchen \
    launch.py

#--icon=kytchen/kytchen.png \
#--add-data="kytchen/kytchen.png:kytchen" \
