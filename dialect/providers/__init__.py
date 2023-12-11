# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib
import logging
import pkgutil

from gi.repository import Gio, GObject

from dialect.providers.base import ProviderCapability, ProviderFeature, ProviderError, ProviderErrorCode  # noqa
from dialect.providers import modules

MODULES = {}
TRANSLATORS = {}
TTS = {}
for _importer, modname, _ispkg in pkgutil.iter_modules(modules.__path__):
    try:
        modclass = importlib.import_module('dialect.providers.modules.' + modname).Provider
        MODULES[modclass.name] = modclass
        if modclass.capabilities:
            if ProviderCapability.TRANSLATION in modclass.capabilities:
                TRANSLATORS[modclass.name] = modclass
            if ProviderCapability.TTS in modclass.capabilities:
                TTS[modclass.name] = modclass
    except Exception as exc:
        logging.warning(f'Could not load the {modname} provider: {exc}')


def check_translator_availability(provider_name):
    if provider_name in TRANSLATORS:
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
