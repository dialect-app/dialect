![Dialect icon](data/com.github.gi_lom.dialect.svg?raw=true)

# Dialect

A translation app for GTK environments based on Google Translate.

## Preview

![Dialect](preview.png?raw=true)

## Features

- Translation based on the [googletrans](https://github.com/ssut/py-googletrans) Python API, an unofficial API for Google Translate
- Translation history (up to 10 translations, you can open the script and easily edit such number if you prefer more)
- Automatic language detection
- Text to speech
- Clipboard button

## Installation

### Flathub

Available soon on Flathub.

### AUR

Arch-based distro users can install it from [AUR](https://aur.archlinux.org/packages/dialect/).

## Building

### Requirements

- Python 3 `python`
- PyGObject `python-gobject`
- GTK3 `gtk3`
- Meson `meson`
- Ninja `ninja`
- Googletrans `python-googletrans`
- gTTS `python-gtts`
- Pydub `python-pydub`

You can install python dependencies from pip:

```bash
pip install googletrans gtts pydub
```

### Building from Git

```bash
git clone https://github.com/gi-lom/dialect.git
cd dialect
meson builddir --prefix=/usr/local
sudo ninja -C builddir install
```

## How to use

Open Dialect directly from your menu. For starting a translation, press "Enter" or the button between the two text spaces.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[GNU General Public License 3 or later](https://www.gnu.org/licenses/gpl-3.0.en.html)
