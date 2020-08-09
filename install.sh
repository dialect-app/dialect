#!/bin/bash

ROOT_UID=0
DEST_DIR=
ICON_DIR=

# Destination directory
if [ "$UID" -eq "$ROOT_UID" ]; then
  DEST_DIR="/usr/share/"
  ICON_DIR="/usr/share/default"
else
  DEST_DIR="$HOME/.local/share"
  ICON_DIR="$HOME/.icons"
fi

#Starting
echo "NOTE: Gnabel requires Python 3 and Pip. If they are not present, you should be able to install them using your distribution's package"
echo ""
echo "Installing..."

#Installing Python libraries
pip3 install pyperclip gobject googletrans gtts pydub

#Copying source files
mkdir ${DEST_DIR}/gnabel
cp gnabel.py ${DEST_DIR}/gnabel
cp icon.png "$ICON_DIR"

#Replacing icon and JSON line
sed -i "s;settings.json;${DEST_DIR}/gnabel/settings.json;" ${DEST_DIR}/gnabel/gnabel.py
sed -i "s;icon.png;${DEST_DIR}/gnabel/icon.png;" ${DEST_DIR}/gnabel/gnabel.py

#Creating desktop entry
cat <<EOT >> gnabel.desktop
[Desktop Entry]
Encoding=UTF-8
Version=1.0
Type=Application
Terminal=false
Exec=python3 ${DEST_DIR}/gnabel/gnabel.py
Name=Gnabel
Comment=A translation app for GTK environments based on Google Translate.
Icon=${DEST_DIR}/gnabel/icon.png
Keywords=gnabel;translate;translation
EOT
mv gnabel.desktop ${DEST_DIR}/applications

#Ending
echo ""
echo "################"
echo ""
echo "Done. If errors have not occurred, Gnabel should now appear in your menu"
echo "Report any issue to: www.github.com/gi-lom/gnabel"
