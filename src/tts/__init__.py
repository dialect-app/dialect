import importlib
import pkgutil

TTS = {}
for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    if modname != 'basetts':
        modclass = importlib.import_module('dialect.tts.' + modname).TextToSpeech
        TTS[modclass.name] = modclass

