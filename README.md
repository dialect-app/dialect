![](https://raw.githubusercontent.com/gi-lom/gnabel/master2/data/gnabel.svg)

# Gnabel
A translation app for GTK environments based on Google Translate.

## Preview
![](https://raw.githubusercontent.com/gi-lom/gnabel/master2/preview.png)

## Features
- Translation based on the [googletrans](https://github.com/ssut/py-googletrans) Python API, an unofficial API for Google Translate
- Translation history (up to 10 translations, you can open the script and easily edit such number if you prefer more)
- Automatic language detection
- Text to speech
- Clipboard button

## Requirements

- Python 3 `python`
- PyGObject `python-gobject`
- GTK3 `gtk3`
- Meson `meson`
- Ninja `ninja`
- Googletrans `python-googletrans`
- gTTS `python-gtts`
- Pydub `python-pydub`

## Installation

- Clone the repository
- Open the repository folder in a terminal
- Run the following commands: 

```bash
meson builddir --prefix=/usr/local
sudo ninja -C builddir install

```

Arch-based distro users can install it from AUR.

## How to use

Open Gnabel directly from your menu. For starting a translation, press "Enter" or the button between the two text spaces.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Currently has been tested on Manjaro 20.0.3 and Ubuntu 20.04

## License
[GNU General Public License 3 or later](https://www.gnu.org/licenses/gpl-3.0.en.html)
