#!/bin/bash

set -o errexit -o pipefail -o nounset

ROOT_UID=0
BIN_DIR=
DESKTOP_DIR=
ICON_DIR=
PIP3_USER_FLAG=()
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_DATA_HOME:-$HOME/.config}"/gnabel
COMMAND="$1"

# Verify command
case "$COMMAND" in
  install);;
  uninstall);;
  --help)
    echo "Usage: $0 install|uninstall|--help"
    echo '    install:     Install Gnabel'
    echo '    uninstall:   Uninstall Gnabel'
    echo '    --help:      Display this message'
    exit
  ;;
  *)
    echo "ERROR: Invalid command: $COMMAND" > /dev/stderr
    "$0" --help # Display help message before exiting
    exit 1
  ;;
esac

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
  PIP3_USER_FLAG=(--user)
fi

case "$COMMAND" in
  install)
    # Make sure destination directories exist
    mkdir -pv "$BIN_DIR"
    mkdir -pv "$DESKTOP_DIR"
    mkdir -pv "$ICON_DIR"
  ;;
esac

#Starting
echo "NOTE: Gnabel requires Python 3 and Pip. If they are not present, you should be able to install them using your distribution's package"
echo ""
echo "Installing..."

#Installing/Uninstalling Python libraries
PYTHON_LIBS=(gobject googletrans gtts pydub)
case "$COMMAND" in
  install)
    pip3 install "${PIP3_USER_FLAG[@]}" "${PYTHON_LIBS[@]}"
  ;;
  uninstall)
    echo 'Do you wish to uninstall Python dependencies too? [Y/n]'
    read -r rmv
    case "$rmv" in
      Y|y|YES|Yes|yes)
        pip3 uninstall "${PIP3_USER_FLAG[@]}" "${PYTHON_LIBS[@]}"
      ;;
      *)
        echo "The answer ($rmv) is not 'yes'. Skipping."
      ;;
    esac
  ;;
esac

# Removing config
case "$COMMAND" in
  uninstall)
    echo "Do you wish to delete history ($CONFIG_DIR/settings.json)? [Y/n]"
    read -r his
    case "$his" in
      Y|y|YES|Yes|yes)
        rm -fv "$CONFIG_DIR/settings.json"
      ;;
      *)
        echo "The answer ($his) is not 'yes'. Skipping."
      ;;
    esac
  ;;
esac

# Usage: handle_file source destination
handle_file() {
  case "$COMMAND" in
    install)
      cp -v "$1" "$2"
    ;;
    uninstall)
      rm -v "$2"
    ;;
  esac
}

#Installing/Uninstalling source files
handle_file gnabel.py "$BIN_DIR/gnabel"
handle_file gnabel.desktop "$DESKTOP_DIR/gnabel.desktop"
handle_file icon.svg "$ICON_DIR/gnabel.svg"

#Ending
echo ""
echo "################"
echo ""
case "$COMMAND" in
  install)
    echo "Done. If errors have not occurred, Gnabel should now appear in your menu"
  ;;
  uninstall)
    echo "Gnabel should have been removed from your system."
  ;;
esac
echo "Report any issue to: www.github.com/gi-lom/gnabel"
