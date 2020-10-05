# Copyright 2020 gi-lom
# Copyright 2020 Mufeed Ali
# Copyright 2020 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import threading
from io import BytesIO

from gi.repository import Gdk, Gio, GLib, Gtk, Handy

from googletrans import LANGUAGES, Translator
from gtts import gTTS, lang
from pydub import AudioSegment
from pydub.playback import play

from dialect.define import APP_ID, RES_PATH, MAX_LENGTH, TRANS_NUMBER, \
    LANG_NUMBER, BUTTON_LENGTH, BUTTON_NUM_LANGUAGES


@Gtk.Template(resource_path=f'{RES_PATH}/window.ui')
class DialectWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'DialectWindow'

    # Get widgets
    main_stack = Gtk.Template.Child()
    exit_btn = Gtk.Template.Child()

    langs_button_box = Gtk.Template.Child()
    switch_btn = Gtk.Template.Child()

    return_btn = Gtk.Template.Child()
    forward_btn = Gtk.Template.Child()

    menu_btn = Gtk.Template.Child()

    left_text = Gtk.Template.Child()
    clear_btn = Gtk.Template.Child()
    paste_btn = Gtk.Template.Child()
    translate_btn = Gtk.Template.Child()

    right_text = Gtk.Template.Child()
    copy_btn = Gtk.Template.Child()
    voice_btn = Gtk.Template.Child()

    # Language values
    lang_codes = list(LANGUAGES.keys())
    lang_names = list(LANGUAGES.values())
    lang_speech = None
    # Current input Text
    current_input_text = ''
    current_history = 0
    history = []
    type_time = 0
    trans_queue = []
    active_thread = None
    # These are for being able to go backspace
    first_key = 0
    second_key = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # GSettings object
        self.settings = Gio.Settings.new(APP_ID)
        # Get saved languages
        self.left_langs = list(self.settings.get_value('left-langs'))
        self.right_langs = list(self.settings.get_value('right-langs'))

        # Google Translate object
        self.translator = Translator()

        # Clipboard
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)  # This is only for the Clipboard button

        # Setup window
        self.setup()

    def setup(self):
        self.set_default_icon_name(APP_ID)

        # Load saved dark mode
        gtk_settings = Gtk.Settings.get_default()
        dark_mode = self.settings.get_boolean('dark-mode')
        gtk_settings.set_property('gtk-application-prefer-dark-theme',
                                  dark_mode)

        # Get languages available for speech
        threading.Thread(target=self.load_lang_speech).start()

        self.setup_headerbar()
        self.setup_translation()

    def load_lang_speech(self):
        try:
            self.lang_speech = list(lang.tts_langs(tld='com').keys())
            GLib.idle_add(self.main_stack.set_visible_child_name, 'translate')

        except RuntimeError as exc:
            def quit(self):
                sys.exit(1)

            self.main_stack.set_visible_child_name('error')
            self.exit_btn.connect('clicked', quit)
            print('Error: ' + str(exc))

    def setup_headerbar(self):
        # Connect history buttons
        self.return_btn.connect('clicked', self.ui_return)
        self.forward_btn.connect('clicked', self.ui_forward)

        # First language combo
        first_language_list = Gtk.ListStore(str)
        first_language_list.append(['Auto'])
        for lang_name in self.lang_names:
            first_language_list.append([lang_name.capitalize()])
        self.first_language_combo = Gtk.ComboBox.new_with_model(first_language_list)
        first_language_cell = Gtk.CellRendererText()
        self.first_language_combo.pack_start(first_language_cell, True)
        self.first_language_combo.add_attribute(first_language_cell, 'text', 0)
        self.first_language_combo.set_active(0)

        # Second language combo
        second_language_list = Gtk.ListStore(str)
        for lang_name in self.lang_names:
            second_language_list.append([lang_name.capitalize()])
        self.second_language_combo = Gtk.ComboBox.new_with_model(second_language_list)
        second_language_cell = Gtk.CellRendererText()
        self.second_language_combo.pack_start(second_language_cell, True)
        self.second_language_combo.add_attribute(second_language_cell, 'text', 0)
        self.second_language_combo.set_active(self.lang_codes.index(self.right_langs[0]))

        # Setup combos in the button box
        self.langs_button_box.pack_start(self.first_language_combo,
                                         True, True, 0)
        self.langs_button_box.child_set_property(self.first_language_combo,
                                                 'position', 0)
        self.langs_button_box.pack_start(self.second_language_combo,
                                         True, True, 0)
        self.langs_button_box.set_homogeneous(False)

        # Switch button
        self.switch_btn.connect('clicked', self.ui_switch)

        # Add menu to menu button
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/menu.ui')
        menu = builder.get_object('app-menu')
        menu_popover = Gtk.Popover.new_from_model(self.menu_btn, menu)
        self.menu_btn.set_popover(menu_popover)

    def setup_translation(self):
        # Left buffer
        self.left_buffer = self.left_text.get_buffer()
        self.left_buffer.set_text('')
        self.left_text.connect('key-press-event', self.update_trans_button)
        self.left_buffer.connect('changed', self.text_changed)
        self.connect('key-press-event', self.update_trans_button)
        # Clear button
        self.clear_btn.connect('clicked', self.ui_clear)
        # Paste button
        self.paste_btn.connect('clicked', self.ui_paste)
        # Translate button
        self.translate_btn.connect('clicked', self.translation)

        # Right buffer
        self.right_buffer = self.right_text.get_buffer()
        self.right_buffer.set_text('')
        # Clipboard button
        self.copy_btn.connect('clicked', self.ui_copy)
        # Voice btn
        self.voice_btn.connect('clicked', self.ui_voice)
        self.voice_image = Gtk.Image.new_from_icon_name(
            'audio-speakers-symbolic', Gtk.IconSize.BUTTON)
        self.voice_spinner = Gtk.Spinner()  # For use while audio is running.
        self.voice_btn.set_image(self.voice_image)

    """
    User interface functions
    """
    def ui_return(self, _button):
        if self.current_history != TRANS_NUMBER:
            self.current_history += 1
            self.history_update()

    def ui_forward(self, _button):
        if self.current_history != 0:
            self.current_history -= 1
            self.history_update()

    def ui_left_language_button(self, button):
        button_label = button.get_label()
        if button_label == 'Auto':
            self.first_language_combo.set_active(0)
        else:
            self.first_language_combo.set_active(self.lang_names.index(button_label.lower()) + 1)

    def ui_right_language_button(self, button):
        button_label = button.get_label()
        self.second_language_combo.set_active(self.lang_names.index(button_label.lower()))

    def switch_all(self, first_language, second_language, first_text, second_text):
        self.first_language_combo.set_active(self.lang_codes.index(second_language) + 1)
        self.second_language_combo.set_active(self.lang_codes.index(first_language))
        self.left_buffer.set_text(second_text)
        self.right_buffer.set_text(first_text)

        # Re-enable widgets
        self.first_language_combo.set_sensitive(True)
        self.second_language_combo.set_sensitive(True)
        self.switch_btn.set_sensitive(True)

    def switch_auto_lang(self, second_language_pos, first_text, second_text):
        revealed_language = str(self.translator.detect(first_text).lang)
        first_language_pos = self.lang_codes.index(revealed_language) + 1
        first_language = self.lang_codes[first_language_pos - 1]
        second_language = self.lang_codes[second_language_pos]

        # Switch all
        GLib.idle_add(self.switch_all, first_language, second_language, first_text, second_text)

    def ui_switch(self, button):
        # Get variables
        self.first_language_combo.set_sensitive(False)
        self.second_language_combo.set_sensitive(False)
        button.set_sensitive(False)
        first_buffer = self.left_buffer
        second_buffer = self.right_buffer
        first_language_pos = self.first_language_combo.get_active()
        second_language_pos = self.second_language_combo.get_active()
        first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        if first_language_pos == 0:
            if first_text == '':
                first_language_pos = self.lang_codes.index(self.left_langs[0]) + 1
            else:
                threading.Thread(
                    target=self.switch_auto_lang,
                    args=(second_language_pos, first_text, second_text)
                ).start()
                return
        first_language = self.lang_codes[first_language_pos - 1]
        second_language = self.lang_codes[second_language_pos]

        # Switch all
        self.switch_all(first_language, second_language, first_text, second_text)

    def ui_clear(self, _button):
        self.left_buffer.set_text('')

    def ui_copy(self, _button):
        second_buffer = self.right_buffer
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        self.clipboard.set_text(second_text, -1)
        self.clipboard.store()

    def ui_paste(self, _button):
        text = self.clipboard.wait_for_text()
        if text is not None:
            end_iter = self.left_buffer.get_end_iter()
            self.left_buffer.insert(end_iter, text)

    def ui_voice(self, _button):
        second_buffer = self.right_buffer
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        second_language_pos = self.second_language_combo.get_active()
        second_language_voice = self.lang_codes[second_language_pos]
        # Add here code that changes voice button behavior
        if second_text != '' and second_language_voice in self.lang_speech:
            self.voice_btn.set_sensitive(False)
            self.voice_btn.set_image(self.voice_spinner)
            self.voice_spinner.start()
            threading.Thread(
                target=self.voice_download,
                args=(second_text, second_language_voice)
            ).start()

    def voice_download(self, text, language):
        file_to_play = BytesIO()
        try:
            tts = gTTS(text, language)
        except Exception:
            # Raise an error message if download fails
            pass
        else:
            tts.write_to_fp(file_to_play)
            file_to_play.seek(0)
            sound_to_play = AudioSegment.from_file(file_to_play, format='mp3')
            play(sound_to_play)
        finally:
            # The code to execute no matter what
            GLib.idle_add(self.voice_btn.set_sensitive, True)
            GLib.idle_add(self.voice_btn.set_image, self.voice_image)
            GLib.idle_add(self.voice_spinner.stop)

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
        return Gdk.EVENT_PROPAGATE

    def text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.translate_btn.set_sensitive(sensitive)
        self.clear_btn.set_sensitive(sensitive)
        if self.settings.get_boolean('live-translation'):
            GLib.idle_add(self.translation, None)

    # The history part
    def reset_return_forward_btns(self):
        self.return_btn.set_sensitive(self.current_history < len(self.history) - 1)
        self.forward_btn.set_sensitive(self.current_history > 0)

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_btns()
        lang_hist = self.history[self.current_history]
        self.first_language_combo.set_active(self.lang_codes.index(lang_hist['Languages'][0]) + 1)
        self.second_language_combo.set_active(self.lang_codes.index(lang_hist['Languages'][1]))
        self.left_buffer.set_text(lang_hist['Text'][0])
        self.right_buffer.set_text(lang_hist['Text'][1])

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def appeared_before(self):
        first_language_pos = self.first_language_combo.get_active()
        second_language_pos = self.second_language_combo.get_active()
        first_text = self.left_buffer.get_text(self.left_buffer.get_start_iter(), self.left_buffer.get_end_iter(), True)
        if (self.history[0]['Languages'][0] == self.lang_codes[first_language_pos - 1] and
                self.history[0]['Languages'][1] == self.lang_codes[second_language_pos] and
                self.history[0]['Text'][0] == first_text):
            return True
        return False

    def translation(self, _button):
        # If it's like the last translation then it's useless to continue
        if len(self.history) == 0 or not self.appeared_before():
            self.voice_btn.set_sensitive(True)
            first_buffer = self.left_buffer
            second_buffer = self.right_buffer
            first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
            # If the first text is empty, then everything is simply resetted and nothing is saved in history
            if first_text == '':
                second_buffer.set_text('')
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
                if not current_right_text.endswith('...'):
                    self.right_buffer.set_text(current_right_text + '...')

                # Check if there are any active threads.
                if self.active_thread is None:
                    # If there are not any active threads, create one and start it.
                    self.active_thread = threading.Thread(target=self.run_translation, daemon=True)
                    self.active_thread.start()

    def run_translation(self):
        while True:
            # If the first language is revealed automatically, let's set it
            if self.trans_queue:
                trans_dict = self.trans_queue.pop(0)
                first_text = trans_dict['first_text']
                first_language_pos = trans_dict['first_language_pos']
                second_language_pos = trans_dict['second_language_pos']
                if first_language_pos == 0 and first_text != '':
                    revealed_language = str(self.translator.detect(first_text).lang)
                    first_language_pos = self.lang_codes.index(revealed_language) + 1
                    GLib.idle_add(self.first_language_combo.set_active, first_language_pos)
                    self.left_langs[0] = self.lang_codes[second_language_pos]
                    self.settings.set_value('left-langs',
                                            GLib.Variant('as', self.left_langs))
                # If the two languages are the same, nothing is done
                if first_language_pos - 1 != second_language_pos:
                    second_text = ''
                    # If the text is over the highest number of characters allowed, it is truncated.
                    # This is done for avoiding exceeding the limit imposed by Google.
                    if len(first_text) > 100:
                        first_text = first_text[:MAX_LENGTH]
                    # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                    try:
                        second_text = self.translator.translate(
                            first_text,
                            src=self.lang_codes[first_language_pos - 1],
                            dest=self.lang_codes[second_language_pos]
                        ).text
                    except Exception:
                        pass
                    GLib.idle_add(self.right_buffer.set_text, second_text)
                    # Finally, everything is saved in history
                    new_history_trans = {
                        'Languages': [self.lang_codes[first_language_pos - 1], self.lang_codes[second_language_pos]],
                        'Text': [first_text, second_text]
                    }
                    if len(self.history) > 0:
                        self.return_btn.set_sensitive(True)
                    if len(self.history) == TRANS_NUMBER:
                        self.history.pop()
                    self.history.insert(0, new_history_trans)

