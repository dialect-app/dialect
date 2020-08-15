#!/usr/bin/env python3

# Initial setup
import json
import os
import sys
from io import BytesIO

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gio, GLib, Gdk, Gtk

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
XdgConfigHome = GLib.get_user_config_dir()
SettingsFile = os.path.join(XdgConfigHome, 'gnabel', 'settings.json')

MenuBuilder = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
    <menu id="app-menu">
        <section>
            <attribute name="id">help-section</attribute>
            <item>
                <attribute name="label" translatable="yes">About</attribute>
                <attribute name="action">app.about</attribute>
            </item>
            <item>
                <attribute name="label" translatable="yes">Quit</attribute>
                <attribute name="action">app.quit</attribute>
            </item>
        </section>
    </menu>
</interface>
"""


# Main part
class MainWindow(Gtk.ApplicationWindow):

    # Language values
    LangCode = list(LANGUAGES.keys())
    LangName = list(LANGUAGES.values())
    Translator = Translator()
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
    def __init__(self, app):
        self.Translator = Translator()
        Gtk.Window.__init__(self, title="Gnabel", application=app)
        self.Clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # This is only for the Clipboard button
        self.set_border_width(10)
        self.set_default_size(400, 200)
        self.set_icon_name("com.github.gi-lom.gnabel")

        self.Header()
        self.Window()

        # Languages available for speech
        try:
            self.LangSpeech = list(lang.tts_langs(tld='com').keys())
        except RuntimeError as e:
            ErrorDialog = Gtk.MessageDialog(transient_for=self,
                                            modal=True,
                                            message_type=Gtk.MessageType.ERROR,
                                            buttons=Gtk.ButtonsType.OK,
                                            text="No network connection detected. Closing.")
            print("Error: " + e)
            Response = ErrorDialog.run()
            if Response:
                sys.exit(1)

    # Header bar
    def Header(self):
        HeaderBar = Gtk.HeaderBar()
        HeaderBar.set_show_close_button(True)
        self.set_titlebar(HeaderBar)

        # Boxes creation
        HeaderBox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        OptionsBox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        OptionsBox.set_layout(Gtk.ButtonBoxStyle.EXPAND)

        HeaderBar.pack_start(HeaderBox)
        HeaderBar.pack_end(OptionsBox)

        # Header box
        ### return button
        self.Return = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.Return.set_tooltip_text("Previous translation")
        self.Return.set_sensitive(len(self.Settings["Translations"]) > 1)
        self.Return.connect("clicked", self.UIReturn)

        ### forward button
        self.Forward = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        self.Forward.set_tooltip_text("Next translation")
        self.Forward.set_sensitive(False)
        self.Forward.connect("clicked", self.UIForward)

        ### Button box for history navigation buttons
        HistoryButtonBox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        HistoryButtonBox.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        HistoryButtonBox.pack_start(self.Return, True, True, 0)
        HistoryButtonBox.pack_start(self.Forward, True, True, 0)

        ### First language
        FirstLanguageList = Gtk.ListStore(str)
        FirstLanguageList.append(["Auto"])
        for L in self.LangName:
            FirstLanguageList.append([L.capitalize()])
        self.FirstLanguageCombo = Gtk.ComboBox.new_with_model(FirstLanguageList)
        FirstLanguageCell = Gtk.CellRendererText()
        self.FirstLanguageCombo.pack_start(FirstLanguageCell, True)
        self.FirstLanguageCombo.add_attribute(FirstLanguageCell, 'text', 0)
        self.FirstLanguageCombo.set_active(0)
        self.FirstLanguageCombo.connect("changed", self.HistoryLeftLanUpdate)

        ### Switch
        Switch = Gtk.Button.new_from_icon_name("object-flip-horizontal-symbolic", Gtk.IconSize.BUTTON)
        Switch.set_tooltip_text("Switch languages")
        Switch.connect("clicked", self.UISwitch)

        ### Second language
        SecondLanguageList = Gtk.ListStore(str)
        for L in self.LangName:
            SecondLanguageList.append([L.capitalize()])
        self.SecondLanguageCombo = Gtk.ComboBox.new_with_model(SecondLanguageList)
        SecondLanguageCell = Gtk.CellRendererText()
        self.SecondLanguageCombo.pack_start(SecondLanguageCell, True)
        self.SecondLanguageCombo.add_attribute(SecondLanguageCell, 'text', 0)
        self.SecondLanguageCombo.set_active(self.LangCode.index(self.Settings['Languages'][1][0]))
        self.SecondLanguageCombo.connect("changed", self.HistoryRightLanUpdate)

        ### Button box for history navigation buttons
        LanguageButtonBox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        LanguageButtonBox.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        LanguageButtonBox.set_homogeneous(False)
        LanguageButtonBox.pack_start(self.FirstLanguageCombo, True, True, 0)
        LanguageButtonBox.pack_start(Switch, True, False, 0)
        LanguageButtonBox.pack_start(self.SecondLanguageCombo, True, True, 0)

        ### Voice
        Voice = Gtk.Button.new_from_icon_name("audio-speakers-symbolic", Gtk.IconSize.BUTTON)
        Voice.set_tooltip_text("Reproduce")
        Voice.connect("clicked", self.UIVoice)

        ### Clipboard
        ClipboardButton = Gtk.Button.new_from_icon_name("edit-paste-symbolic", Gtk.IconSize.BUTTON)
        ClipboardButton.set_tooltip_text("Copy to Clipboard")
        ClipboardButton.connect("clicked", self.UIPaperclip)

        ### Menu button
        Builder = Gtk.Builder.new_from_string(MenuBuilder, -1) 
        Menu = Builder.get_object("app-menu")
        MenuButton = Gtk.MenuButton()
        MenuButton.set_direction(Gtk.ArrowType.NONE)
        MenuPopover = Gtk.Popover.new_from_model(MenuButton, Menu)
        MenuButton.set_popover(MenuPopover)

        # Mount buttons
        ### Left side
        HeaderBar.pack_start(HistoryButtonBox)

        ### Center
        HeaderBar.set_custom_title(LanguageButtonBox)

        ### Right side
        OptionsBox.pack_start(Voice, True, True, 0)
        OptionsBox.pack_start(ClipboardButton, True, True, 0)
        OptionsBox.pack_start(MenuButton, True, True, 0)

    # Window
    def Window(self):
        # Boxes
        Box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.add(Box)

        UpperBox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        LowerBox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        Box.pack_start(UpperBox, True, True, 0)
        Box.pack_end(LowerBox, False, False, 0)

        # Left side
        ### Language box
        LanLeftBox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        LanL0 = Gtk.Button.new_with_label("Auto")
        LanL0.set_property("width-request", 65)
        LanLeftBox.pack_start(LanL0, False, False, 0)
        LanL0.connect("clicked", self.UIPressLeftLanguageButton)
        self.LanLeftButtons = []
        for i in range(ButtonNumLanguages):
            self.LanLeftButtons.append(Gtk.Button())
            self.LanLeftButtons[i].set_property("width-request", ButtonLength)
            self.LanLeftButtons[i].connect("clicked", self.UIPressLeftLanguageButton)
            LanLeftBox.pack_start(self.LanLeftButtons[i], False, False, 0)
        self.RewriteLeftLanguageButtons()
        LowerBox.pack_start(LanLeftBox, False, False, 0)

        ### Text side
        LeftScroll = Gtk.ScrolledWindow()
        LeftScroll.set_border_width(2)
        LeftScroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.LeftText = Gtk.TextView()
        self.LeftText.set_wrap_mode(2)
        self.LeftBuffer = self.LeftText.get_buffer()
        if len(self.Settings["Translations"]) > 0:
            self.FirstText = self.Settings["Translations"][0]["Text"][0]
            self.LeftBuffer.set_text(self.FirstText)
        else:
            self.LeftBuffer.set_text("")
        self.LeftText.connect("key-press-event", self.UpdateTransButton)
        self.LeftBuffer.connect("changed", self.TextChanged)
        self.connect("key-press-event", self.UpdateTransButton)
        LeftScroll.add(self.LeftText)
        UpperBox.pack_start(LeftScroll, True, True, 0)

        # Central part
        ### The button that starts the translation
        self.TransStart = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        self.TransStart.set_tooltip_text("Hint: you can press 'Ctrl+Enter' to translate.")
        self.TransStart.set_sensitive(self.LeftBuffer.get_char_count() != 0)
        self.TransStart.connect("clicked", self.Translation)
        UpperBox.pack_start(self.TransStart, False, False, 0)

        # Right side
        ### Language box
        LanRightBox = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        self.LanRightButtons = []
        for i in range(ButtonNumLanguages):
            self.LanRightButtons.append(Gtk.Button())
            self.LanRightButtons[i].set_property("width-request", ButtonLength)
            self.LanRightButtons[i].connect("clicked", self.UIPressRightLanguageButton)
            LanRightBox.pack_start(self.LanRightButtons[i], False, False, 0)
        self.RewriteRightLanguageButtons()
        LowerBox.pack_end(LanRightBox, False, True, 0)

        ### Text side
        RightScroll = Gtk.ScrolledWindow()
        RightScroll.set_border_width(2)
        RightScroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        RightText = Gtk.TextView()
        RightText.set_wrap_mode(2)
        self.RightBuffer = RightText.get_buffer()
        RightText.set_editable(False)
        if len(self.Settings["Translations"]) > 0:
            self.SecondText = self.Settings["Translations"][0]["Text"][1]
            self.RightBuffer.set_text(self.SecondText)
        else:
            self.RightBuffer.set_text("")
        RightScroll.add(RightText)
        UpperBox.pack_end(RightScroll, True, True, 0)

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

    def UIAbout(self, action, param):
        AboutText = Gtk.AboutDialog(transient_for=self, modal=True)
        AboutText.set_program_name("Gnabel")
        AboutText.set_comments("A translation app for GTK environments based on Google Translate.")
        AboutText.set_license_type(Gtk.License(3))
        AboutText.set_website("https://github.com/gi-lom/gnabel")
        AboutText.set_website_label("Github page")
        AboutText.set_logo_icon_name("com.github.gi-lom.gnabel")
        AboutText.connect('response', lambda dialog, response: dialog.destroy())
        AboutText.show()

    # This starts the translation if Ctrl+Enter button is pressed
    def UpdateTransButton(self, button, keyboard):
        Modifiers = keyboard.get_state() & Gtk.accelerator_get_default_mod_mask()

        ControlMask = Gdk.ModifierType.CONTROL_MASK
        ShiftMask = Gdk.ModifierType.SHIFT_MASK
        UnicodeKeyVal = Gdk.keyval_to_unicode(keyboard.keyval)
        if GLib.unichar_isgraph(chr(UnicodeKeyVal)) and Modifiers in (ShiftMask, 0) and not self.LeftText.is_focus():
            self.LeftText.grab_focus()

        if ControlMask == Modifiers:
            if keyboard.keyval == Gdk.KEY_Return:
                GLib.idle_add(self.Translation, button)
                return Gdk.EVENT_STOP

    def TextChanged(self, buffer):
        self.TransStart.set_sensitive(self.LeftBuffer.get_char_count() != 0)
        if os.environ.get("GNABEL_LIVE") == "1":
            GLib.idle_add(self.Translation, None)

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


class Gnabel(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self, application_id="com.github.gi_lom.gnabel")

    def do_activate(self):

        def setup_actions(window):
            """Setup menu actions."""
            QuitAction = Gio.SimpleAction.new('quit', None)
            QuitAction.connect('activate', self.OnQuit)
            self.add_action(QuitAction)

            AboutAction = Gio.SimpleAction.new('about', None)
            AboutAction.connect('activate', window.UIAbout)
            self.add_action(AboutAction)

        win = self.props.active_window
        if not win:
            win = MainWindow(self)
            setup_actions(win)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def OnQuit(self, action, param):
        """Quit the application from the menu."""
        self.quit()


# Final part, run the Application
app = Gnabel()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
