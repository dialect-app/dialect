#!/bin/bash

set -o errexit -o pipefail -o nounset

ROOT_UID=0
DEST_DIR=
ICON_DIR=
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

cd "$(dirname "$0")"

# Destination directory
if [ "$UID" -eq "$ROOT_UID" ]; then
  DEST_DIR="/usr/bin"
  ICON_DIR="/usr/share/default"
else
  DEST_DIR="$HOME/.local/bin"
  ICON_DIR="$DATA_HOME/icons"
fi

mkdir -pv "$DEST_DIR"
mkdir -pv "$ICON_DIR"

#Starting
echo "NOTE: Gnabel requires Python 3 and Pip. If they are not present, you should be able to install them using your distribution's package"
echo ""
echo "Installing..."

#Installing Python libraries
pip3 install pyperclip gobject googletrans gtts pydub

#Copying source files
cp -v gnabel.py "$DEST_DIR/gnabel"
cp -v icon.png "$ICON_DIR/gnabel.png"
cp -v gnabel.desktop "$DEST_DIR/applications/gnabel.desktop"

#Ending
echo ""
echo "################"
echo ""
echo "Done. If errors have not occurred, Gnabel should now appear in your menu"
echo "Report any issue to: www.github.com/gi-lom/gnabel"
