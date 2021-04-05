import pkgutil
import importlib

TRANSLATORS = {}
for importer, modname, ispkg in pkgutil.iter_modules(__path__):
    if modname != 'basetrans':
        modclass = importlib.import_module('dialect.translators.' + modname).Translator
        TRANSLATORS[modclass.name] = modclass

