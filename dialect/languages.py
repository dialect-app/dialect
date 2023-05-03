# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from gettext import gettext as _
from typing import List

from gi.repository import Gio, GObject

LANGUAGES = {
    'af': _('Afrikaans'),
    'sq': _('Albanian'),
    'am': _('Amharic'),
    'ar': _('Arabic'),
    'hy': _('Armenian'),
    'az': _('Azerbaijani'),
    'eu': _('Basque'),
    'be': _('Belarusian'),
    'bn': _('Bengali'),
    'bs': _('Bosnian'),
    'bg': _('Bulgarian'),
    'ca': _('Catalan'),
    'ceb': _('Cebuano'),
    'ny': _('Chichewa'),
    'zh': _('Chinese'),
    'zh-Hans': _('Chinese (Simplified)'),
    'zh-Hant': _('Chinese (Traditional)'),
    'co': _('Corsican'),
    'hr': _('Croatian'),
    'cs': _('Czech'),
    'da': _('Danish'),
    'nl': _('Dutch'),
    'en': _('English'),
    'eo': _('Esperanto'),
    'et': _('Estonian'),
    'tl': _('Filipino'),
    'fi': _('Finnish'),
    'fr': _('French'),
    'fy': _('Frisian'),
    'gl': _('Galician'),
    'ka': _('Georgian'),
    'de': _('German'),
    'el': _('Greek'),
    'gu': _('Gujarati'),
    'ht': _('Haitian Creole'),
    'ha': _('Hausa'),
    'haw': _('Hawaiian'),
    'iw': _('Hebrew'),
    'he': _('Hebrew'),
    'hi': _('Hindi'),
    'hmn': _('Hmong'),
    'hu': _('Hungarian'),
    'is': _('Icelandic'),
    'ig': _('Igbo'),
    'id': _('Indonesian'),
    'ga': _('Irish'),
    'it': _('Italian'),
    'ja': _('Japanese'),
    'jw': _('Javanese'),
    'kn': _('Kannada'),
    'kk': _('Kazakh'),
    'km': _('Khmer'),
    'rw': _('Kinyarwanda'),
    'ko': _('Korean'),
    'ku': _('Kurdish (Kurmanji)'),
    'ky': _('Kyrgyz'),
    'lo': _('Lao'),
    'la': _('Latin'),
    'lv': _('Latvian'),
    'lt': _('Lithuanian'),
    'lb': _('Luxembourgish'),
    'mk': _('Macedonian'),
    'mg': _('Malagasy'),
    'ms': _('Malay'),
    'ml': _('Malayalam'),
    'mt': _('Maltese'),
    'mi': _('Maori'),
    'mr': _('Marathi'),
    'mn': _('Mongolian'),
    'my': _('Myanmar (Burmese)'),
    'ne': _('Nepali'),
    'no': _('Norwegian'),
    'or': _('Odia (Oriya)'),
    'ps': _('Pashto'),
    'fa': _('Persian'),
    'pl': _('Polish'),
    'pt': _('Portuguese'),
    'pa': _('Punjabi'),
    'ro': _('Romanian'),
    'ru': _('Russian'),
    'sm': _('Samoan'),
    'gd': _('Scots Gaelic'),
    'sr': _('Serbian'),
    'st': _('Sesotho'),
    'sn': _('Shona'),
    'sd': _('Sindhi'),
    'si': _('Sinhala'),
    'sk': _('Slovak'),
    'sl': _('Slovenian'),
    'so': _('Somali'),
    'es': _('Spanish'),
    'su': _('Sundanese'),
    'sw': _('Swahili'),
    'sv': _('Swedish'),
    'tg': _('Tajik'),
    'ta': _('Tamil'),
    'tt': _('Tatar'),
    'te': _('Telugu'),
    'th': _('Thai'),
    'tr': _('Turkish'),
    'tk': _('Turkmen'),
    'uk': _('Ukrainian'),
    'ur': _('Urdu'),
    'ug': _('Uyghur'),
    'uz': _('Uzbek'),
    'vi': _('Vietnamese'),
    'cy': _('Welsh'),
    'xh': _('Xhosa'),
    'yi': _('Yiddish'),
    'yo': _('Yoruba'),
    'zu': _('Zulu'),
}

ALIASES = {
    'zh-CN': 'zh-Hans',
    'zh-TW': 'zh-Hant',
}


def normalize_lang_code(code):
    code = code.replace('_', '-')  # Normalize separator
    codes = code.split('-')

    if len(codes) == 2:  # Code contain a script or country code

        if len(codes[1]) == 4:  # ISO 15924 (script)
            codes[1] = codes[1].capitalize()

        elif len(codes[1]) == 2:  # ISO 3166-1 (country)
            codes[1] = codes[1].upper()

        code = '-'.join(codes)

    if code in ALIASES:
        code = ALIASES[code]

    return code


def get_lang_name(code: str) -> str | None:
    return LANGUAGES.get(code, None)


class LangObject(GObject.Object):
    __gtype_name__ = 'LangObject'

    code: str = GObject.Property(type=str)
    name: str = GObject.Property(type=str)
    selected: bool = GObject.Property(type=bool, default=False)

    def __init__(self, code: str, name: str, selected: bool = False):
        super().__init__()

        self.code = code
        self.name = name
        self.selected = selected

    def __str__(self) -> str:
        return self.code


class LanguagesListModel(GObject.GObject, Gio.ListModel):
    __gtype_name__ = 'LanguagesListModel'

    def __init__(self, names_func=get_lang_name):
        super().__init__()

        self.names_func = names_func
        self.langs: List[LangObject] = []

    def __iter__(self):
        return iter(self.langs)

    def do_get_item(self, position: int) -> LangObject:
        return self.langs[position]

    def do_get_item_type(self):
        return LangObject

    def do_get_n_items(self) -> int:
        return len(self.langs)

    def set_langs(self, langs: List[str], auto: bool = False):
        removed: int = len(self.langs)
        self.langs.clear()

        if auto:
            self.langs.append(LangObject('auto', _('Auto')))

        for code in langs:
            self.langs.append(LangObject(code, self.names_func(code)))

        self.items_changed(0, removed, len(self.langs))

    def set_selected(self, code: str):
        for item in self.langs:
            item.selected = (item.code == code)
