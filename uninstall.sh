
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
CONFIG_DIR="${XDG_DATA_HOME:-$HOME/.config/gnabel}"

#Starting
echo "NOTE: This script supposes you have used the install script provided to install Gnabel."
echo "If you have run the install script using sudo, do it again for this script"
echo ""

#Uninstall python dependencies
echo "Do you wish to uninstall Python dependencies too? [y/N]"
read rmv
if [ "$rmv" = "y" ]; then
    echo "NOTE: gobject will not be removed"
    echo "Removing Python dependencies..."
    pip3 uninstall googletrans gtts pydub
fi
echo ""
echo "################"
echo ""

#Remove history
echo "Do you wish to remove translation history? [y/N]"
read his
if [ "$his" = "y" -a -f "$CONFIG_DIR/settings.json" ]; then
    rm -v "$CONFIG_HOMEsettings.json"
fi
echo ""
echo "################"
echo ""

#Removing source files
rm -v "$BIN_DIR/gnabel"
rm -v "$DESKTOP_DIR/gnabel.desktop"
rm -v "$ICON_DIR/gnabel.svg"

#Ending
echo ""
echo "################"
echo ""
echo "Gnabel should have been removed from your system."
echo "Report any issue to: www.github.com/gi-lom/gnabel"
