# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# SPDX-License-Identifier: GPL-3.0-or-later

# Initial setup
import json
import os
import sys
import threading
from io import BytesIO

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from googletrans import LANGUAGES, Translator
from gtts import gTTS, lang
from pydub import AudioSegment
from pydub.playback import play

# Constant values
APP_ID = 'com.github.gi_lom.dialect'
MAX_LENGTH = 1000  # maximum number of characters you can translate at once
TRANS_NUMBER = 10  # number of translations to save in history
LANG_NUMBER = 8  # number of language tuples to save in history
BUTTON_LENGTH = 65  # length of language buttons
BUTTON_NUM_LANGUAGES = 3  # number of language buttons
XDG_CONFIG_HOME = GLib.get_user_config_dir()
SETTINGS_FILE = os.path.join(XDG_CONFIG_HOME, 'dialect', 'settings.json')


# Main part
class DialectWindow(Gtk.ApplicationWindow):

    # Language values
    lang_code = list(LANGUAGES.keys())
    lang_name = list(LANGUAGES.values())
    # Current input Text
    current_input_text = ""
    current_history = 0
    type_time = 0
    trans_queue = []
    active_thread = None
    # These are for being able to go backspace
    first_key = 0
    second_key = 0
    # Config Settings JSON file
    if not os.path.exists(SETTINGS_FILE):
        settings = {}
        settings["Languages"] = [
            ['en', 'fr', 'es', 'de'],
            ['en', 'fr', 'es', 'de']
        ]
        settings["Translations"] = []
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as out_file:
            json.dump(settings, out_file, indent=2)
    else:
        with open(SETTINGS_FILE) as json_file:
            settings = json.load(json_file)
        if "Languages" not in settings:
            settings["Languages"] = [
                ['en', 'fr', 'es', 'de'],
                ['en', 'fr', 'es', 'de']
            ]
            with open(SETTINGS_FILE, 'w') as out_file:
                json.dump(settings, out_file, indent=2)
        if "Translations" not in settings:
            settings["Translations"] = []
            with open(SETTINGS_FILE, 'w') as out_file:
                json.dump(settings, out_file, indent=2)

    # Mount everything
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translator = Translator()
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # This is only for the Clipboard button
        self.set_border_width(10)
        self.set_default_size(400, 200)
        self.set_default_icon_name(APP_ID)

        self.header()
        self.window()

        # Languages available for speech
        try:
            self.lang_speech = list(lang.tts_langs(tld='com').keys())
        except RuntimeError as e:
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No network connection detected. Exiting."
            )
            print("Error: " + str(e))
            response = error_dialog.run()
            if response:
                sys.exit(1)

    # Header bar
    def header(self):
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        self.set_titlebar(header_bar)

        # Boxes creation
        header_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        options_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)

        header_bar.pack_start(header_box)
        header_bar.pack_end(options_box)

        # Header box
        ### return button
        self.return_button = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.return_button.set_tooltip_text("Previous translation")
        self.return_button.set_sensitive(len(self.settings["Translations"]) > 1)
        self.return_button.connect("clicked", self.ui_return)

        ### forward button
        self.forward_button = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        self.forward_button.set_tooltip_text("Next translation")
        self.forward_button.set_sensitive(False)
        self.forward_button.connect("clicked", self.ui_forward)

        ### Button box for history navigation buttons
        history_button_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        history_button_box.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        history_button_box.pack_start(self.return_button, True, True, 0)
        history_button_box.pack_start(self.forward_button, True, True, 0)

        ### First language
        first_language_list = Gtk.ListStore(str)
        first_language_list.append(["Auto"])
        for l in self.lang_name:
            first_language_list.append([l.capitalize()])
        self.first_language_combo = Gtk.ComboBox.new_with_model(first_language_list)
        first_language_cell = Gtk.CellRendererText()
        self.first_language_combo.pack_start(first_language_cell, True)
        self.first_language_combo.add_attribute(first_language_cell, 'text', 0)
        self.first_language_combo.set_active(0)
        self.first_language_combo.connect("changed", self.history_left_lang_update)

        ### Switch
        self.switch_button = Gtk.Button.new_from_icon_name("object-flip-horizontal-symbolic", Gtk.IconSize.BUTTON)
        self.switch_button.set_tooltip_text("Switch languages")
        self.switch_button.connect("clicked", self.ui_switch)

        ### Second language
        second_language_list = Gtk.ListStore(str)
        for l in self.lang_name:
            second_language_list.append([l.capitalize()])
        self.second_language_combo = Gtk.ComboBox.new_with_model(second_language_list)
        second_language_cell = Gtk.CellRendererText()
        self.second_language_combo.pack_start(second_language_cell, True)
        self.second_language_combo.add_attribute(second_language_cell, 'text', 0)
        self.second_language_combo.set_active(self.lang_code.index(self.settings['Languages'][1][0]))
        self.second_language_combo.connect("changed", self.history_right_lang_update)

        ### Button box for history navigation buttons
        language_button_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        language_button_box.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        language_button_box.set_homogeneous(False)
        language_button_box.pack_start(self.first_language_combo, True, True, 0)
        language_button_box.pack_start(self.switch_button, True, False, 0)
        language_button_box.pack_start(self.second_language_combo, True, True, 0)

        ### Voice
        self.voice = Gtk.Button()
        self.voice.set_tooltip_text("Reproduce")
        self.voice.connect("clicked", self.ui_voice)
        self.voice_image = Gtk.Image.new_from_icon_name("audio-speakers-symbolic", Gtk.IconSize.BUTTON)
        self.voice_spinner = Gtk.Spinner()  # For use while audio is running.
        self.voice.set_image(self.voice_image)

        ### Clipboard
        copy_button = Gtk.Button.new_from_icon_name("edit-paste-symbolic", Gtk.IconSize.BUTTON)
        copy_button.set_tooltip_text("Copy to Clipboard")
        copy_button.connect("clicked", self.ui_copy)

        ### Menu button
        builder = Gtk.Builder.new_from_resource("/com/github/gi_lom/dialect/menu.ui")
        menu = builder.get_object("app-menu")
        menu_button = Gtk.MenuButton()
        menu_button.set_direction(Gtk.ArrowType.NONE)
        menu_popover = Gtk.Popover.new_from_model(menu_button, menu)
        menu_button.set_popover(menu_popover)

        # Mount buttons
        ### Left side
        header_bar.pack_start(history_button_box)

        ### Center
        header_bar.set_custom_title(language_button_box)

        ### Right side
        options_box.pack_start(self.voice, True, True, 0)
        options_box.pack_start(copy_button, True, True, 0)
        options_box.pack_start(menu_button, True, True, 0)

    # Window
    def window(self):
        # Boxes
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.add(box)

        upper_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        lower_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(upper_box, True, True, 0)
        box.pack_end(lower_box, False, False, 0)

        # Left side
        #
        # Language box
        lang_left_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        lang_l0 = Gtk.Button.new_with_label("Auto")
        lang_l0.set_property("width-request", 65)
        lang_left_box.pack_start(lang_l0, False, False, 0)
        lang_l0.connect("clicked", self.ui_left_language_button)
        self.lang_left_buttons = []
        for i in range(BUTTON_NUM_LANGUAGES):
            self.lang_left_buttons.append(Gtk.Button())
            self.lang_left_buttons[i].set_property("width-request", BUTTON_LENGTH)
            self.lang_left_buttons[i].connect("clicked", self.ui_left_language_button)
            lang_left_box.pack_start(self.lang_left_buttons[i], False, False, 0)
        self.rewrite_left_language_buttons()
        lower_box.pack_start(lang_left_box, False, False, 0)

        # Text side
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_border_width(2)
        left_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.left_text = Gtk.TextView()
        self.left_text.set_wrap_mode(2)
        self.left_buffer = self.left_text.get_buffer()
        if len(self.settings["Translations"]) > 0:
            self.first_text = self.settings["Translations"][0]["Text"][0]
            self.left_buffer.set_text(self.first_text)
        else:
            self.left_buffer.set_text("")
        self.left_text.connect("key-press-event", self.update_trans_button)
        self.left_buffer.connect("changed", self.text_changed)
        self.connect("key-press-event", self.update_trans_button)
        left_scroll.add(self.left_text)
        upper_box.pack_start(left_scroll, True, True, 0)

        # Central part
        #
        # The button that starts the translation
        self.trans_start = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        self.trans_start.set_tooltip_text("Hint: you can press 'Ctrl+Enter' to translate.")
        self.trans_start.set_sensitive(self.left_buffer.get_char_count() != 0)
        self.trans_start.connect("clicked", self.translation)
        upper_box.pack_start(self.trans_start, False, False, 0)

        # Right side
        # Language box
        lang_right_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        self.lan_right_buttons = []
        for i in range(BUTTON_NUM_LANGUAGES):
            self.lan_right_buttons.append(Gtk.Button())
            self.lan_right_buttons[i].set_property("width-request", BUTTON_LENGTH)
            self.lan_right_buttons[i].connect("clicked", self.ui_right_language_button)
            lang_right_box.pack_start(self.lan_right_buttons[i], False, False, 0)
        self.rewrite_right_language_buttons()
        lower_box.pack_end(lang_right_box, False, True, 0)

        # Text side
        right_scroll = Gtk.ScrolledWindow()
        right_scroll.set_border_width(2)
        right_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        right_text = Gtk.TextView()
        right_text.set_wrap_mode(2)
        self.right_buffer = right_text.get_buffer()
        right_text.set_editable(False)
        if len(self.settings["Translations"]) > 0:
            self.second_text = self.settings["Translations"][0]["Text"][1]
            self.right_buffer.set_text(self.second_text)
        else:
            self.right_buffer.set_text("")
        right_scroll.add(right_text)
        upper_box.pack_end(right_scroll, True, True, 0)

    # User interface functions
    def ui_return(self, button):
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self.history_update()

    def ui_forward(self, button):
        if self.current_history != 0:
            self.current_history -= 1
            self.history_update()

    def ui_left_language_button(self, button):
        ll = button.get_label()
        if ll == 'Auto':
            self.first_language_combo.set_active(0)
        else:
            self.first_language_combo.set_active(self.lang_name.index(ll.lower()) + 1)

    def ui_right_language_button(self, button):
        ll = button.get_label()
        self.second_language_combo.set_active(self.lang_name.index(ll.lower()))

    def switch_all(self, first_language, second_language, first_text, second_text):
        self.first_language_combo.set_active(self.lang_code.index(second_language) + 1)
        self.second_language_combo.set_active(self.lang_code.index(first_language))
        self.left_buffer.set_text(second_text)
        self.right_buffer.set_text(first_text)

        # Re-enable widgets
        self.first_language_combo.set_sensitive(True)
        self.second_language_combo.set_sensitive(True)
        self.switch_button.set_sensitive(True)

    def switch_auto_lang(self, second_language_pos, first_text, second_text):
        revealed_language = str(self.translator.detect(first_text).lang)
        first_language_pos = self.lang_code.index(revealed_language) + 1
        first_language = self.lang_code[first_language_pos - 1]
        second_language = self.lang_code[second_language_pos]

        # Switch all
        GLib.idle_add(self.switch_all, first_language, second_language, first_text, second_text)

    def ui_switch(self, button):
        # Get variables
        self.first_language_combo.set_sensitive(False)
        self.second_language_combo.set_sensitive(False)
        self.switch_button.set_sensitive(False)
        first_buffer = self.left_buffer
        second_buffer = self.right_buffer
        first_language_pos = self.first_language_combo.get_active()
        second_language_pos = self.second_language_combo.get_active()
        first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        if first_language_pos == 0:
            if first_text == "":
                first_language_pos = self.lang_code.index(self.settings["Languages"][0][0]) + 1
            else:
                threading.Thread(
                    target=self.switch_auto_lang,
                    args=(second_language_pos, first_text, second_text)
                ).start()
                return
        first_language = self.lang_code[first_language_pos - 1]
        second_language = self.lang_code[second_language_pos]

        # Switch all
        self.switch_all(first_language, second_language, first_text, second_text)

    def ui_copy(self, button):
        second_buffer = self.right_buffer
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        self.clipboard.set_text(second_text, -1)
        self.clipboard.store()

    def ui_voice(self, button):
        second_buffer = self.right_buffer
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        second_language_pos = self.second_language_combo.get_active()
        second_language_voice = self.lang_code[second_language_pos]
        # Add here code that changes voice button behavior
        if second_text != "" and second_language_voice in self.lang_speech:
            self.voice.set_sensitive(False)
            self.voice.set_image(self.voice_spinner)
            self.voice_spinner.start()
            threading.Thread(target=self.voice_download,
                             args=(second_text, second_language_voice)).start()

    def voice_download(self, text, lang):
        file_to_play = BytesIO()
        try:
            tts = gTTS(text, lang)
        except Exception:
            # Raise an error message if download fails
            pass
        else:
            tts.write_to_fp(file_to_play)
            file_to_play.seek(0)
            sound_to_play = AudioSegment.from_file(file_to_play, format="mp3")
            play(sound_to_play)
        finally:
            # The code to execute no matter what
            GLib.idle_add(self.voice.set_sensitive, True)
            GLib.idle_add(self.voice.set_image, self.voice_image)
            GLib.idle_add(self.voice_spinner.stop)
            pass

    def ui_about(self, action, param):
        AboutText = Gtk.AboutDialog(transient_for=self, modal=True)
        AboutText.set_program_name("Dialect")
        AboutText.set_comments("A translation app for GTK environments based on Google Translate.")
        AboutText.set_license_type(Gtk.License(3))
        AboutText.set_website("https://github.com/gi-lom/dialect")
        AboutText.set_website_label("Github page")
        AboutText.set_logo_icon_name(APP_ID)
        AboutText.connect('response', lambda dialog, response: dialog.destroy())
        AboutText.show()

    # This starts the translation if Ctrl+Enter button is pressed
    def update_trans_button(self, button, keyboard):
        modifiers = keyboard.get_state() & Gtk.accelerator_get_default_mod_mask()

        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        unicode_key_val = Gdk.keyval_to_unicode(keyboard.keyval)
        if (GLib.unichar_isgraph(chr(unicode_key_val)) and
                modifiers in (shift_mask, 0) and not self.left_text.is_focus()):
            self.left_text.grab_focus()

        if control_mask == modifiers:
            if keyboard.keyval == Gdk.KEY_Return:
                GLib.idle_add(self.translation, button)
                return Gdk.EVENT_STOP

    def text_changed(self, buffer):
        self.trans_start.set_sensitive(self.left_buffer.get_char_count() != 0)
        if os.environ.get("DIALECT_LIVE") == "1":
            GLib.idle_add(self.translation, None)

    # The history part
    def reset_return_forward_buttons(self):
        self.return_button.set_sensitive(self.current_history < len(self.settings["Translations"]) - 1)
        self.forward_button.set_sensitive(self.current_history > 0)

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_buttons()
        lang_hist = self.settings["Translations"][self.current_history]
        self.first_language_combo.set_active(self.lang_code.index(lang_hist["Languages"][0]) + 1)
        self.second_language_combo.set_active(self.lang_code.index(lang_hist["Languages"][1]))
        self.left_buffer.set_text(lang_hist["Text"][0])
        self.right_buffer.set_text(lang_hist["Text"][1])

    # Update language buttons below (left)
    def history_left_lang_update(self, button):
        first_language_pos = self.first_language_combo.get_active()
        # If you select the same language of the other part, they get switched
        if first_language_pos - 1 == self.second_language_combo.get_active():
            un = self.settings["Languages"][0][0]
            dos = self.settings["Languages"][1][0]
            self.first_language_combo.set_active(self.lang_code.index(dos) + 1)
            self.second_language_combo.set_active(self.lang_code.index(un))
            first_buffer = self.left_buffer
            second_buffer = self.right_buffer
            first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
            second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
            first_buffer.set_text(second_text)
            second_buffer.set_text(first_text)
        else:
            code = self.lang_code[first_language_pos - 1]
            if self.settings["Languages"][0][0] not in self.settings["Languages"][0][1:]:
                self.settings["Languages"][0].pop()
                self.settings["Languages"][0].insert(0, code)
            self.settings["Languages"][0][0] = code
            with open(SETTINGS_FILE, 'w') as out_file:
                json.dump(self.settings, out_file, indent=2)
            if self.current_history == 0:
                self.rewrite_left_language_buttons()

    # Update language buttons below (right)
    def history_right_lang_update(self, button):
        second_language_pos = self.second_language_combo.get_active()
        code = self.lang_code[second_language_pos]
        if code == self.first_language_combo.get_active() - 1:
            un = self.settings["Languages"][0][0]
            dos = self.settings["Languages"][1][0]
            self.first_language_combo.set_active(self.lang_code.index(dos) + 1)
            self.second_language_combo.set_active(self.lang_code.index(un))
            first_buffer = self.left_buffer
            second_buffer = self.right_buffer
            first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
            second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
            first_buffer.set_text(second_text)
            second_buffer.set_text(first_text)
        else:
            if not self.settings["Languages"][1][0] in self.settings["Languages"][1][1:]:
                self.settings["Languages"][1].pop()
                self.settings["Languages"][1].insert(0, code)
            self.settings["Languages"][1][0] = code
            with open(SETTINGS_FILE, 'w') as out_file:
                json.dump(self.settings, out_file, indent=2)
            if self.current_history == 0:
                self.rewrite_right_language_buttons()

    # Every time a new language is selected, the language buttons below are updated
    def rewrite_left_language_buttons(self):
        for i in range(BUTTON_NUM_LANGUAGES):
            num = self.lang_code.index(self.settings['Languages'][0][i + 1])
            self.lang_left_buttons[i].set_label(self.lang_name[num].capitalize())

    def rewrite_right_language_buttons(self):
        for i in range(BUTTON_NUM_LANGUAGES):
            num = self.lang_code.index(self.settings['Languages'][1][i + 1])
            self.lan_right_buttons[i].set_label(self.lang_name[num].capitalize())

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def appeared_before(self):
        first_language_pos = self.first_language_combo.get_active()
        second_language_pos = self.second_language_combo.get_active()
        first_text = self.left_buffer.get_text(self.left_buffer.get_start_iter(), self.left_buffer.get_end_iter(), True)
        if (self.settings["Translations"][0]["Languages"][0] == self.lang_code[first_language_pos - 1] and
                self.settings["Translations"][0]["Languages"][1] == self.lang_code[second_language_pos] and
                self.settings["Translations"][0]["Text"][0] == first_text):
            return True
        return False

    def translation(self, button):
        # If it's like the last translation then it's useless to continue
        if len(self.settings["Translations"]) == 0 or not self.appeared_before():
            first_buffer = self.left_buffer
            second_buffer = self.right_buffer
            first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
            # If the first text is empty, then everything is simply resetted and nothing is saved in history
            if first_text == "":
                second_buffer.set_text("")
            else:
                first_language_pos = self.first_language_combo.get_active()
                second_language_pos = self.second_language_combo.get_active()

                if self.trans_queue:
                    self.trans_queue.pop(0)
                self.trans_queue.append({
                    'first_text': first_text,
                    'first_language_pos': first_language_pos,
                    'second_language_pos': second_language_pos
                })
                current_right_text = second_buffer.get_text(
                    second_buffer.get_start_iter(),
                    second_buffer.get_end_iter(),
                    True
                )
                if not current_right_text.endswith("..."):
                    self.right_buffer.set_text(current_right_text + "...")

                # Check if there are any active threads.
                if self.active_thread is None:
                    # If there are not any active threads, create one and start it.
                    self.active_thread = threading.Thread(target=self.RunTranslation, daemon=True)
                    self.active_thread.start()

    def RunTranslation(self):
        while True:
            # If the first language is revealed automatically, let's set it
            if self.trans_queue:
                trans_dict = self.trans_queue.pop(0)
                first_text = trans_dict['first_text']
                first_language_pos = trans_dict['first_language_pos']
                second_language_pos = trans_dict['second_language_pos']
                if first_language_pos == 0 and first_text != "":
                    revealed_language = str(self.translator.detect(first_text).lang)
                    first_language_pos = self.lang_code.index(revealed_language) + 1
                    GLib.idle_add(self.first_language_combo.set_active, first_language_pos)
                    self.settings["Languages"][0][0] = self.lang_code[second_language_pos]
                # If the two languages are the same, nothing is done
                if first_language_pos - 1 != second_language_pos:
                    second_text = ""
                    # If the text is over the highest number of characters allowed, it is truncated.
                    # This is done for avoiding exceeding the limit imposed by Google.
                    if len(first_text) > 100:
                        first_text = first_text[:MAX_LENGTH]
                    # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                    try:
                        second_text = self.translator.translate(
                            first_text,
                            src=self.lang_code[first_language_pos - 1],
                            dest=self.lang_code[second_language_pos]
                        ).text
                        self.current_history == 0
                    except Exception:
                        pass
                    GLib.idle_add(self.right_buffer.set_text, second_text)
                    # Finally, everything is saved in history
                    new_history_trans = {
                        "Languages": [self.lang_code[first_language_pos - 1], self.lang_code[second_language_pos]],
                        "Text": [first_text, second_text]
                    }
                    if len(self.settings["Translations"]) > 0:
                        self.return_button.set_sensitive(True)
                    if len(self.settings["Translations"]) == TRANS_NUMBER:
                        self.settings["Translations"].pop()
                    self.settings["Translations"].insert(0, new_history_trans)
                    # Save everything in the JSON file
                    with open(SETTINGS_FILE, 'w') as out_file:
                        json.dump(self.settings, out_file, indent=2)


class Dialect(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self, application_id=APP_ID)

    def do_activate(self):

        def setup_actions(window):
            """Setup menu actions."""
            about_action = Gio.SimpleAction.new('about', None)
            about_action.connect('activate', window.ui_about)
            self.add_action(about_action)

        win = self.props.active_window
        if not win:
            win = DialectWindow(
                application=self,
                title='Dialect'
            )
            setup_actions(win)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        GLib.set_application_name('Dialect')
        GLib.set_prgname('com.github.gi_lom.dialect')


def main(version):
    # Run the Application
    app = Dialect()
    return app.run(sys.argv)
