import pkgutil
import importlib

TRANSLATORS = {}
for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    if modname != 'basetrans':
        modclass = importlib.import_module('dialect.translators.' + modname).Translator
        TRANSLATORS[modclass.name] = modclass

def check_backend_availability(backend_name):
    if backend_name in TRANSLATORS.keys():
        return True

    return False

def get_fallback_backend():
    return list(TRANSLATORS.keys())[0]
