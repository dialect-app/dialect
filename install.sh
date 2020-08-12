#!/bin/bash

set -o errexit -o pipefail -o nounset

ROOT_UID=0
BIN_DIR=
DESKTOP_DIR=
ICON_DIR=
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

# Use containing folder of this script as working directory
cd "$(dirname "$0")"

# Destination directory
if [ "$UID" -eq "$ROOT_UID" ]; then
  BIN_DIR="/usr/bin"
  DESKTOP_DIR="/usr/share/applications"
  ICON_DIR="/usr/share/icons/hicolor/scalable/apps"
else
  BIN_DIR="$HOME/.local/bin"
  DESKTOP_DIR="$DATA_HOME/applications"
  ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
fi

# Make sure destination directories exist
mkdir -pv "$BIN_DIR"
mkdir -pv "$DESKTOP_DIR"
mkdir -pv "$ICON_DIR"

#Starting
echo "NOTE: Gnabel requires Python 3 and Pip. If they are not present, you should be able to install them using your distribution's package"
echo ""
echo "Installing..."

#Installing Python libraries
sudo pip3 install gobject googletrans gtts pydub

#Copying source files
cp -v gnabel.py "$BIN_DIR/gnabel"
cp -v gnabel.desktop "$DESKTOP_DIR/gnabel.desktop"
cp -v icon.svg "$ICON_DIR/gnabel.svg"

#Ending
echo ""
echo "################"
echo ""
echo "Done. If errors have not occurred, Gnabel should now appear in your menu"
echo "Report any issue to: www.github.com/gi-lom/gnabel"
