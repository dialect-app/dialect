#!/usr/bin/env python3

# Initial setup
import json
import os
from io import BytesIO

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio

from googletrans import LANGUAGES, Translator
from gtts import gTTS, lang
from pydub import AudioSegment
from pydub.playback import play

# Constant values
MaxLength = 1000  # maximum number of characters you can translate at once
TransNumber = 10  # number of translations to save in history
LanNumber = 8  # number of language tuples to save in history
ButtonLength = 65  # length of language buttons
ButtonNumLanguages = 3  # number of language buttons
SettingsFile = os.path.expanduser('~/.config/gnabel/settings.json')


# Main part
class MainWindow(Gtk.Window):

    # Language values
    LangCode = list(LANGUAGES.keys())
    LangName = list(LANGUAGES.values())
    Translator = Translator()
    # Languages available for speech
    LangSpeech = list(lang.tts_langs(tld='com').keys())
    # Current input Text
    CurrentInputText = ""
    CurrentHistory = 0
    TypeTime = 0
    # These are for being able to go backspace
    FirstKey = 0
    SecondKey = 0
    # Config Settings JSON file
    if not os.path.exists(SettingsFile):
        Settings = {}
        Settings["Languages"] = [['en', 'fr', 'es', 'de'], ['en', 'fr', 'es', 'de']]
        Settings["Translations"] = []
        os.makedirs(os.path.dirname(SettingsFile), exist_ok=True)
        with open(SettingsFile, 'w') as outfile:
            json.dump(Settings, outfile, indent=2)
    else:
        with open(SettingsFile) as json_file:
            Settings = json.load(json_file)
        if "Languages" not in Settings:
            Settings["Languages"] = [['en', 'fr', 'es', 'de'], ['en', 'fr', 'es', 'de']]
            with open(SettingsFile, 'w') as outfile:
                json.dump(Settings, outfile, indent=2)
        if "Translations" not in Settings:
            Settings["Translations"] = []
            with open(SettingsFile, 'w') as outfile:
                json.dump(Settings, outfile, indent=2)

    # Mount everything
    def __init__(self):
        self.Translator = Translator()
        Gtk.Window.__init__(self, title="GTranslate")
        self.Clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # This is only for the Clipboard button
        self.set_border_width(10)
        self.set_default_size(400, 200)

        MainWindow.Header(self)
        MainWindow.Window(self)

    # Header bar
    def Header(self):
        self.Header = Gtk.HeaderBar()
        self.Header.set_show_close_button(True)
        self.set_titlebar(self.Header)

        # Boxes creation
        self.HeaderBox = Gtk.HBox(spacing=6)
        self.OptionsBox = Gtk.HBox(spacing=6)

        self.Header.pack_start(self.HeaderBox)
        self.Header.pack_end(self.OptionsBox)

        # Header box
        ### return button
        self.Return = Gtk.Button()
        self.ReturnIcon = Gio.ThemedIcon(name="go-previous-symbolic")
        self.ReturnPic = Gtk.Image.new_from_gicon(self.ReturnIcon, Gtk.IconSize.BUTTON)
        self.Return.set_tooltip_text("Previous translation")
        self.Return.add(self.ReturnPic)
        self.Return.set_sensitive(len(self.Settings["Translations"]) > 1)
        self.Return.connect("clicked", self.UIReturn)

        ### forward button
        self.Forward = Gtk.Button()
        self.ForwardIcon = Gio.ThemedIcon(name="go-next-symbolic")
        self.ForwardPic = Gtk.Image.new_from_gicon(self.ForwardIcon, Gtk.IconSize.BUTTON)
        self.Forward.set_tooltip_text("Next translation")
        self.Forward.add(self.ForwardPic)
        self.Forward.set_sensitive(False)
        self.Forward.connect("clicked", self.UIForward)

        ### First language
        self.FirstLanguageList = Gtk.ListStore(str)
        self.FirstLanguageList.append(["Auto"])
        for L in self.LangName:
            self.FirstLanguageList.append([L.capitalize()])
        self.FirstLanguageCombo = Gtk.ComboBox.new_with_model(self.FirstLanguageList)
        self.FirstLanguageCell = Gtk.CellRendererText()
        self.FirstLanguageCombo.pack_start(self.FirstLanguageCell, True)
        self.FirstLanguageCombo.add_attribute(self.FirstLanguageCell, 'text', 0)
        self.FirstLanguageCombo.set_active(0)
        self.FirstLanguageCombo.connect("changed", self.HistoryLeftLanUpdate)

        ### Switch
        self.Switch = Gtk.Button()
        self.SwitchIcon = Gio.ThemedIcon(name="object-flip-horizontal-symbolic")
        self.SwitchPic = Gtk.Image.new_from_gicon(self.SwitchIcon, Gtk.IconSize.BUTTON)
        self.Switch.add(self.SwitchPic)
        self.Switch.set_tooltip_text("Switch languages")
        self.Switch.connect("clicked", self.UISwitch)

        ### Second language
        self.SecondLanguageList = Gtk.ListStore(str)
        for L in self.LangName:
            self.SecondLanguageList.append([L.capitalize()])
        self.SecondLanguageCombo = Gtk.ComboBox.new_with_model(self.SecondLanguageList)
        self.SecondLanguageCell = Gtk.CellRendererText()
        self.SecondLanguageCombo.pack_start(self.SecondLanguageCell, True)
        self.SecondLanguageCombo.add_attribute(self.SecondLanguageCell, 'text', 0)
        self.SecondLanguageCombo.set_active(self.LangCode.index(self.Settings['Languages'][1][0]))
        self.SecondLanguageCombo.connect("changed", self.HistoryRightLanUpdate)

        ### Voice
        self.Voice = Gtk.Button()
        self.VoiceIcon = Gio.ThemedIcon(name="audio-speakers-symbolic")
        self.VoicePic = Gtk.Image.new_from_gicon(self.VoiceIcon, Gtk.IconSize.BUTTON)
        self.Voice.set_tooltip_text("Reproduce")
        self.Voice.add(self.VoicePic)
        self.Voice.connect("clicked", self.UIVoice)

        ### Clipboard
        self.Clipboard = Gtk.Button()
        self.ClipboardIcon = Gio.ThemedIcon(name="edit-paste-symbolic")
        self.ClipboardPic = Gtk.Image.new_from_gicon(self.ClipboardIcon, Gtk.IconSize.BUTTON)
        self.Clipboard.set_tooltip_text("Copy to Clipboard")
        self.Clipboard.add(self.ClipboardPic)
        self.Clipboard.connect("clicked", self.UIPaperclip)

        ### About button
        self.About = Gtk.Button()
        self.AboutIcon = Gio.ThemedIcon(name="help-about-symbolic")
        self.AboutPic = Gtk.Image.new_from_gicon(self.AboutIcon, Gtk.IconSize.BUTTON)
        self.Clipboard.set_tooltip_text("About")
        self.About.add(self.AboutPic)
        self.About.connect("clicked", self.UIAbout)

        # Mount buttons
        ### Left side
        self.HeaderBox.pack_start(self.Return, True, True, 0)
        self.HeaderBox.pack_start(self.Forward, True, True, 0)
        self.Header.pack_start(self.FirstLanguageCombo)
        self.Header.pack_start(self.Switch)
        self.Header.pack_start(self.SecondLanguageCombo)

        ### Right side
        self.OptionsBox.pack_start(self.Voice, True, True, 0)
        self.OptionsBox.pack_start(self.Clipboard, True, True, 0)
        self.OptionsBox.pack_start(self.About, True, True, 0)

    # Window
    def Window(self):
        # Boxes
        self.Box = Gtk.VBox(spacing=6)
        self.add(self.Box)

        self.UpperBox = Gtk.HBox(spacing=6)
        self.LowerBox = Gtk.HBox(spacing=6)
        self.Box.pack_start(self.UpperBox, True, True, 0)
        self.Box.pack_end(self.LowerBox, False, False, 0)

        # Left side
        ### Language box
        self.LanLeftBox = Gtk.HBox(spacing=6)
        self.LanL0 = Gtk.Button.new_with_label("Auto")
        self.LanL0.set_property("width-request", 65)
        self.LanLeftBox.pack_start(self.LanL0, False, False, 0)
        self.LanL0.connect("clicked", self.UIPressLeftLanguageButton)
        self.LanLeftButtons = []
        for i in range(ButtonNumLanguages):
            self.LanLeftButtons.append(Gtk.Button())
            self.LanLeftButtons[i].set_property("width-request", ButtonLength)
            self.LanLeftButtons[i].connect("clicked", self.UIPressLeftLanguageButton)
            self.LanLeftBox.pack_start(self.LanLeftButtons[i], False, False, 0)
        self.RewriteLeftLanguageButtons()
        self.LowerBox.pack_start(self.LanLeftBox, False, False, 0)

        ### Text side
        self.LeftScroll = Gtk.ScrolledWindow()
        self.LeftScroll.set_border_width(2)
        self.LeftScroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.LeftText = Gtk.TextView()
        self.LeftText.set_wrap_mode(2)
        self.LeftBuffer = self.LeftText.get_buffer()
        if len(self.Settings["Translations"]) > 0:
            self.FirstText = self.Settings["Translations"][0]["Text"][0]
            self.LeftBuffer.set_text(self.FirstText)
        else:
            self.LeftBuffer.set_text("")
        self.LeftText.connect("key-press-event", self.UpdateTransButton)
        self.LeftText.connect("key-release-event", self.UpdateTransButtonRemoveBackspace)
        self.LeftScroll.add(self.LeftText)
        self.UpperBox.pack_start(self.LeftScroll, True, True, 0)

        # Central part
        ### The button that starts the translation
        self.TransStart = Gtk.Button()
        self.TransIcon = Gio.ThemedIcon(name="go-next-symbolic")
        self.TransPic = Gtk.Image.new_from_gicon(self.TransIcon, Gtk.IconSize.BUTTON)
        self.TransStart.set_tooltip_text("Hint: you can press 'Enter' to translate. Press 'Alt+Enter' to add a backspace in the text")
        self.TransStart.add(self.TransPic)
        self.TransStart.set_sensitive(True)
        self.TransStart.connect("clicked", self.Translation)
        self.UpperBox.pack_start(self.TransStart, False, False, 0)

        # Right side
        ### Language box
        self.LanRightBox = Gtk.HBox(spacing=6)
        self.LanRightButtons = []
        for i in range(ButtonNumLanguages):
            self.LanRightButtons.append(Gtk.Button())
            self.LanRightButtons[i].set_property("width-request", ButtonLength)
            self.LanRightButtons[i].connect("clicked", self.UIPressRightLanguageButton)
            self.LanRightBox.pack_start(self.LanRightButtons[i], False, False, 0)
        self.RewriteRightLanguageButtons()
        self.LowerBox.pack_end(self.LanRightBox, False, True, 0)

        ### Text side
        self.RightScroll = Gtk.ScrolledWindow()
        self.RightScroll.set_border_width(2)
        self.RightScroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.RightText = Gtk.TextView()
        self.RightText.set_wrap_mode(2)
        self.RightBuffer = self.RightText.get_buffer()
        self.RightText.set_editable(False)
        if len(self.Settings["Translations"]) > 0:
            self.SecondText = self.Settings["Translations"][0]["Text"][1]
            self.RightBuffer.set_text(self.SecondText)
        else:
            self.RightBuffer.set_text("")
        self.RightScroll.add(self.RightText)
        self.UpperBox.pack_end(self.RightScroll, True, True, 0)

    # User interface functions
    def UIReturn(self, button):
        if self.CurrentHistory != TransNumber:
            self.CurrentHistory += 1
            self.HistoryUpdate()

    def UIForward(self, button):
        if self.CurrentHistory != 0:
            self.CurrentHistory -= 1
            self.HistoryUpdate()

    def UIPressLeftLanguageButton(self, button):
        ll = button.get_label()
        if ll == 'Auto':
            self.FirstLanguageCombo.set_active(0)
        else:
            self.FirstLanguageCombo.set_active(self.LangName.index(ll.lower()) + 1)

    def UIPressRightLanguageButton(self, button):
        ll = button.get_label()
        self.SecondLanguageCombo.set_active(self.LangName.index(ll.lower()))

    def UISwitch(self, button):
        # Get variables
        FirstBuffer = self.LeftBuffer
        SecondBuffer = self.RightBuffer
        FirstLanguagePos = self.FirstLanguageCombo.get_active()
        SecondLanguagePos = self.SecondLanguageCombo.get_active()
        FirstText = FirstBuffer.get_text(FirstBuffer.get_start_iter(), FirstBuffer.get_end_iter(), True)
        SecondText = SecondBuffer.get_text(SecondBuffer.get_start_iter(), SecondBuffer.get_end_iter(), True)
        if FirstLanguagePos == 0:
            if FirstText == "":
                FirstLanguagePos = self.LangCode.index(self.Settings["Languages"][0][0]) + 1
            else:
                RevealedLanguage = str(self.Translator.detect(FirstText).lang)
                FirstLanguagePos = self.LangCode.index(RevealedLanguage) + 1
        FirstLanguage = self.LangCode[FirstLanguagePos - 1]
        SecondLanguage = self.LangCode[SecondLanguagePos]

        # Switch all
        self.FirstLanguageCombo.set_active(self.LangCode.index(SecondLanguage) + 1)
        self.SecondLanguageCombo.set_active(self.LangCode.index(FirstLanguage))
        FirstBuffer.set_text(SecondText)
        SecondBuffer.set_text(FirstText)

    def UIHistory(self, button):
        self.HistoryPopover.set_relative_to(button)
        self.HistoryPopover.show_all()
        self.HistoryPopover.popup()

    def UIPaperclip(self, button):
        SecondBuffer = self.RightBuffer
        SecondText = SecondBuffer.get_text(SecondBuffer.get_start_iter(), SecondBuffer.get_end_iter(), True)
        self.Clipboard.set_text(SecondText, -1)
        self.Clipboard.store()

    def UIVoice(self, button):
        SecondBuffer = self.RightBuffer
        SecondText = SecondBuffer.get_text(SecondBuffer.get_start_iter(), SecondBuffer.get_end_iter(), True)
        SecondLanguagePos = self.SecondLanguageCombo.get_active()
        SecondLanguageVoice = self.LangCode[SecondLanguagePos]
        if SecondText != "" and SecondLanguageVoice in self.LangSpeech:
            FileToPlay = BytesIO()
            tts = gTTS(SecondText, lang=SecondLanguageVoice)
            tts.write_to_fp(FileToPlay)
            FileToPlay.seek(0)
            SoundToPlay = AudioSegment.from_file(FileToPlay, format="mp3")
            play(SoundToPlay)

    def UIAbout(self, button):
        AboutText = Gtk.AboutDialog()
        AboutText.set_program_name("Gnabel")
        AboutText.set_license_type(Gtk.License(3))
        AboutText.set_website("https://github.com/gi-lom/gnabel")
        AboutText.set_website_label("Github page")
        AboutText.set_logo(None)
        AboutText.show()

    # This starts the translation if the enter button is pressed
    def UpdateTransButton(self, button, keyboard):
        self.FirstKey = self.SecondKey
        self.SecondKey = keyboard.keyval
        LeftText = self.LeftBuffer.get_text(self.LeftBuffer.get_start_iter(), self.LeftBuffer.get_end_iter(), True)
        self.TransStart.set_sensitive(len(LeftText) != 0)
        if self.FirstKey == 65505:
            pass
        if keyboard.keyval == 65293 and self.FirstKey != 65505:
            self.Translation(button)

    def UpdateTransButtonRemoveBackspace(self, button, keyboard):
        LeftText = self.LeftBuffer.get_text(self.LeftBuffer.get_start_iter(), self.LeftBuffer.get_end_iter(), True)
        if keyboard.keyval == 65293 and self.FirstKey != 65505:
            self.LeftBuffer.set_text(LeftText[:len(LeftText) - 1])

    # The history part
    def ResetReturnForwardButtons(self):
        ### Return
        self.Return.set_sensitive(self.CurrentHistory < len(self.Settings["Translations"]) - 1)
        self.Forward.set_sensitive(self.CurrentHistory > 0)

    # Retrieve translation history
    def HistoryUpdate(self):
        self.ResetReturnForwardButtons()
        LanHist = self.Settings["Translations"][self.CurrentHistory]
        self.FirstLanguageCombo.set_active(self.LangCode.index(LanHist["Languages"][0]) + 1)
        self.SecondLanguageCombo.set_active(self.LangCode.index(LanHist["Languages"][1]))
        self.LeftBuffer.set_text(LanHist["Text"][0])
        self.RightBuffer.set_text(LanHist["Text"][1])

    # Update language buttons below (left)
    def HistoryLeftLanUpdate(self, button):
        FirstLanguagePos = self.FirstLanguageCombo.get_active()
        # If you select the same language of the other part, they get switched
        if FirstLanguagePos - 1 == self.SecondLanguageCombo.get_active():
            Un = self.Settings["Languages"][0][0]
            Dos = self.Settings["Languages"][1][0]
            self.FirstLanguageCombo.set_active(self.LangCode.index(Dos) + 1)
            self.SecondLanguageCombo.set_active(self.LangCode.index(Un))
            FirstBuffer = self.LeftBuffer
            SecondBuffer = self.RightBuffer
            FirstText = FirstBuffer.get_text(FirstBuffer.get_start_iter(), FirstBuffer.get_end_iter(), True)
            SecondText = SecondBuffer.get_text(SecondBuffer.get_start_iter(), SecondBuffer.get_end_iter(), True)
            FirstBuffer.set_text(SecondText)
            SecondBuffer.set_text(FirstText)
        else:
            Code = self.LangCode[FirstLanguagePos - 1]
            if self.Settings["Languages"][0][0] not in self.Settings["Languages"][0][1:]:
                self.Settings["Languages"][0].pop()
                self.Settings["Languages"][0].insert(0, Code)
            self.Settings["Languages"][0][0] = Code
            with open(SettingsFile, 'w') as outfile:
                json.dump(self.Settings, outfile, indent=2)
            if self.CurrentHistory == 0:
                self.RewriteLeftLanguageButtons()

    # Update language buttons below (right)
    def HistoryRightLanUpdate(self, button):
        SecondLanguagePos = self.SecondLanguageCombo.get_active()
        Code = self.LangCode[SecondLanguagePos]
        if Code == self.FirstLanguageCombo.get_active() - 1:
            Un = self.Settings["Languages"][0][0]
            Dos = self.Settings["Languages"][1][0]
            self.FirstLanguageCombo.set_active(self.LangCode.index(Dos) + 1)
            self.SecondLanguageCombo.set_active(self.LangCode.index(Un))
            FirstBuffer = self.LeftBuffer
            SecondBuffer = self.RightBuffer
            FirstText = FirstBuffer.get_text(FirstBuffer.get_start_iter(), FirstBuffer.get_end_iter(), True)
            SecondText = SecondBuffer.get_text(SecondBuffer.get_start_iter(), SecondBuffer.get_end_iter(), True)
            FirstBuffer.set_text(SecondText)
            SecondBuffer.set_text(FirstText)
        else:
            if not self.Settings["Languages"][1][0] in self.Settings["Languages"][1][1:]:
                self.Settings["Languages"][1].pop()
                self.Settings["Languages"][1].insert(0, Code)
            self.Settings["Languages"][1][0] = Code
            with open(SettingsFile, 'w') as outfile:
                json.dump(self.Settings, outfile, indent=2)
            if self.CurrentHistory == 0:
                self.RewriteRightLanguageButtons()

    # Every time a new language is selected, the language buttons below are updated
    def RewriteLeftLanguageButtons(self):
        for i in range(ButtonNumLanguages):
            num = self.LangCode.index(self.Settings['Languages'][0][i + 1])
            self.LanLeftButtons[i].set_label(self.LangName[num].capitalize())

    def RewriteRightLanguageButtons(self):
        for i in range(ButtonNumLanguages):
            num = self.LangCode.index(self.Settings['Languages'][1][i + 1])
            self.LanRightButtons[i].set_label(self.LangName[num].capitalize())

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def AppearedBefore(self):
        FirstLanguagePos = self.FirstLanguageCombo.get_active()
        SecondLanguagePos = self.SecondLanguageCombo.get_active()
        FirstText = self.LeftBuffer.get_text(self.LeftBuffer.get_start_iter(), self.LeftBuffer.get_end_iter(), True)
        if self.Settings["Translations"][0]["Languages"][0] == self.LangCode[FirstLanguagePos - 1] and self.Settings["Translations"][0]["Languages"][1] == self.LangCode[SecondLanguagePos] and self.Settings["Translations"][0]["Text"][0] == FirstText:
            return True
        return False

    def Translation(self, button):
        # If it's like the last translation then it's useless to continue
        if len(self.Settings["Translations"]) == 0 or not self.AppearedBefore():
            # ItWasARepeatedAuto = -1
            FirstBuffer = self.LeftBuffer
            SecondBuffer = self.RightBuffer
            FirstText = FirstBuffer.get_text(FirstBuffer.get_start_iter(), FirstBuffer.get_end_iter(), True)
            # If the first text is empty, then everything is simply resetted and nothing is saved in history
            if FirstText == "":
                SecondBuffer.set_text("")
            else:
                FirstLanguagePos = self.FirstLanguageCombo.get_active()
                SecondLanguagePos = self.SecondLanguageCombo.get_active()
                # If the first language is revealed automatically, let's set it
                if FirstLanguagePos == 0 and FirstText != "":
                    RevealedLanguage = str(self.Translator.detect(FirstText).lang)
                    FirstLanguagePos = self.LangCode.index(RevealedLanguage) + 1
                    self.FirstLanguageCombo.set_active(FirstLanguagePos)
                    self.Settings["Languages"][0][0] = self.LangCode[SecondLanguagePos]
                # If the two languages are the same, nothing is done
                if FirstLanguagePos - 1 != SecondLanguagePos:
                    SecondText = ""
                    # If the text is over the highest number of characters allowed, it is truncated. This is done for avoiding exceeding the limit imposed by Google.
                    if len(FirstText) > 100:
                        FirstText = FirstText[:MaxLength]
                    # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                    try:
                        SecondText = self.Translator.translate(FirstText, src=self.LangCode[FirstLanguagePos - 1], dest=self.LangCode[SecondLanguagePos]).text
                        self.CurrentHistory == 0
                        # SecondText = str(time.time())
                    except Exception:
                        pass
                    SecondBuffer.set_text(SecondText)
                    # Finally, everything is saved in history
                    NewHistoryTrans = {
                        "Languages": [self.LangCode[FirstLanguagePos - 1], self.LangCode[SecondLanguagePos]],
                        "Text": [FirstText, SecondText]
                    }
                    if len(self.Settings["Translations"]) > 0:
                        self.Return.set_sensitive(True)
                    if len(self.Settings["Translations"]) == TransNumber:
                        self.Settings["Translations"].pop()
                    self.Settings["Translations"].insert(0, NewHistoryTrans)
                    # Save everything in the JSON file
                    with open(SettingsFile, 'w') as outfile:
                        json.dump(self.Settings, outfile, indent=2)


# Final part, run the Window
win = MainWindow()
win.connect("destroy", Gtk.main_quit)
win.set_default_icon_name('gnabel')
win.show_all()
Gtk.main()
