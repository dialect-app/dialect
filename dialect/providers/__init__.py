import importlib
from gettext import gettext as _
import pkgutil

from gi.repository import Gio, GObject

MODULES = {}
TRANSLATORS = {}
TTS = {}
for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    if modname != 'base':
        modclass = importlib.import_module('dialect.providers.' + modname).Provider
        MODULES[modclass.name] = modclass
        if modclass.translation:
            TRANSLATORS[modclass.name] = modclass
        if modclass.tts:
            TTS[modclass.name] = modclass


def check_translator_availability(backend_name):
    if backend_name in TRANSLATORS:
        return True
    return False


def get_fallback_translator_name():
    if TRANSLATORS:
        return next(iter(TRANSLATORS))
    return None


class ProviderObject(GObject.Object):
    __gtype_name__ = 'ProviderObject'

    def __init__(self, p_class=None):
        super().__init__()

        self.p_class = p_class

    @GObject.Property(type=str)
    def name(self):
        if self.p_class is not None:
            return self.p_class.name
        else:
            return ''

    @GObject.Property(type=str)
    def prettyname(self):
        if self.p_class is not None:
            return self.p_class.prettyname
        else:
            return _('Disabled')


class ProvidersListModel(GObject.GObject, Gio.ListModel):
    __gtype_name__ = 'ProvidersListModel'

    def __init__(self, p_type='', show_disabled=False):
        super().__init__()

        if (p_type):  # If we want to get an specific provider type
            types = {
                'translators': TRANSLATORS,
                'tts': TTS
            }
            providers = types.get(p_type)
        else:  # Get all providers
            providers = MODULES

        providers = list(providers.values())
        self.providers = []
        for provider in providers:
            self.providers.append(ProviderObject(provider))
        if show_disabled and self.providers:
            self.providers.insert(0, ProviderObject())

    def do_get_item(self, position):
        return self.providers[position]

    def do_get_item_type(self):
        return ProviderObject

    def do_get_n_items(self):
        return len(self.providers)

    def get_index_by_name(self, name):
        for i, prov in enumerate(self.providers):
            if prov.name == name:
                return i


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
    'zh-CN': _('Chinese (Simplified)'),
    'zh-TW': _('Chinese (Traditional)'),
    'zh_HANT': _('Chinese (Traditional)'),
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


def get_lang_name(code):
    return LANGUAGES.get(code, code)
