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
from dialect.lang_selector import DialectLangSelector


@Gtk.Template(resource_path=f'{RES_PATH}/window.ui')
class DialectWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'DialectWindow'

    # Get widgets
    main_stack = Gtk.Template.Child()
    main_box = Gtk.Template.Child()
    exit_btn = Gtk.Template.Child()

    title_stack = Gtk.Template.Child()
    langs_button_box = Gtk.Template.Child()
    switch_btn = Gtk.Template.Child()
    left_lang_btn = Gtk.Template.Child()
    left_lang_label = Gtk.Template.Child()
    right_lang_btn = Gtk.Template.Child()
    right_lang_label = Gtk.Template.Child()

    return_btn = Gtk.Template.Child()
    forward_btn = Gtk.Template.Child()

    menu_btn = Gtk.Template.Child()

    left_text = Gtk.Template.Child()
    clear_btn = Gtk.Template.Child()
    paste_btn = Gtk.Template.Child()
    translate_btn = Gtk.Template.Child()

    right_box = Gtk.Template.Child()
    right_text = Gtk.Template.Child()
    trans_spinner = Gtk.Template.Child()
    copy_btn = Gtk.Template.Child()
    voice_btn = Gtk.Template.Child()

    actionbar = Gtk.Template.Child()
    left_lang_btn2 = Gtk.Template.Child()
    switch_btn2 = Gtk.Template.Child()
    right_lang_btn2 = Gtk.Template.Child()

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
    mobile_mode = None

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

        # Connect responsive design function
        self.connect('check-resize', self.responsive_listener)

        # Get languages available for speech
        threading.Thread(target=self.load_lang_speech).start()

        self.setup_headerbar()
        self.setup_actionbar()
        self.setup_translation()

    def load_lang_speech(self):
        try:
            self.lang_speech = list(lang.tts_langs(tld='com').keys())
            GLib.idle_add(self.main_stack.set_visible_child_name, 'translate')

        except RuntimeError as exc:
            def quit(_button):
                sys.exit(1)

            self.main_stack.set_visible_child_name('error')
            self.exit_btn.connect('clicked', quit)
            print('Error: ' + str(exc))

    def setup_headerbar(self):
        # Connect history buttons
        self.return_btn.connect('clicked', self.ui_return)
        self.forward_btn.connect('clicked', self.ui_forward)

        # Left lang selector
        self.left_lang_selector = DialectLangSelector()
        self.left_lang_selector.connect('notify::selected',
                                        self.on_left_lang_changed)
        # Load saved left lang
        self.left_lang_selector.set_property('selected', self.left_langs[0])
        # Set popover selector to button
        self.left_lang_btn.set_popover(self.left_lang_selector)

        # Right lang selector
        self.right_lang_selector = DialectLangSelector()
        self.right_lang_selector.connect('notify::selected',
                                         self.on_right_lang_changed)
        # Load saved right lang
        self.right_lang_selector.set_property('selected', self.right_langs[0])
        # Set popover selector to button
        self.right_lang_btn.set_popover(self.right_lang_selector)

        # Add languages to both list
        for code, name in LANGUAGES.items():
            self.left_lang_selector.insert(code, name.capitalize())
            self.right_lang_selector.insert(code, name.capitalize())

        self.langs_button_box.set_homogeneous(False)

        # Switch button
        self.switch_btn.connect('clicked', self.ui_switch)

        # Add menu to menu button
        builder = Gtk.Builder.new_from_resource(f'{RES_PATH}/menu.ui')
        menu = builder.get_object('app-menu')
        menu_popover = Gtk.Popover.new_from_model(self.menu_btn, menu)
        self.menu_btn.set_popover(menu_popover)

    def setup_actionbar(self):
        # Set popovers to lang buttons
        self.left_lang_btn2.set_popover(self.left_lang_selector)
        self.right_lang_btn2.set_popover(self.right_lang_selector)

        # Switch button
        self.switch_btn2.connect('clicked', self.ui_switch)

    def setup_translation(self):
        # Left buffer
        self.left_buffer = self.left_text.get_buffer()
        self.left_buffer.set_text('')
        self.left_buffer.connect('changed', self.text_changed)
        self.left_buffer.connect('end-user-action', self.user_action_ended)
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

    def responsive_listener(self, window):
        if self.get_allocation().width < 600:
            if self.mobile_mode is True:
                return

            self.mobile_mode = True
            self.toggle_mobile_mode()
        else:
            if self.mobile_mode is None or True:
                self.mobile_mode = False
                self.toggle_mobile_mode()

    def toggle_mobile_mode(self):
        if self.mobile_mode:
            # Show actionbar
            self.actionbar.show()
            # Change headerbar title
            self.title_stack.set_visible_child_name('label')
            # Change translation box orientation
            self.main_box.set_orientation(Gtk.Orientation.VERTICAL)
            # Change lang selectors position
            self.left_lang_selector.set_relative_to(self.left_lang_btn2)
            self.right_lang_selector.set_relative_to(self.right_lang_btn2)
        else:
            # Hide actionbar
            self.actionbar.hide()
            # Reset headerbar title
            self.title_stack.set_visible_child_name('selector')
            # Reset translation box orientation
            self.main_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            # Reset lang selectors position
            self.left_lang_selector.set_relative_to(self.left_lang_btn)
            self.right_lang_selector.set_relative_to(self.right_lang_btn)

    def on_left_lang_changed(self, _obj, _param):
        code = self.left_lang_selector.get_property('selected')

        if code in LANGUAGES:
            self.left_lang_label.set_label(LANGUAGES[code].capitalize())
            # Updated saved left langs list
            if code in self.left_langs:
                # Bring lang to the top
                index = self.left_langs.index(code)
                self.left_langs.insert(0, self.left_langs.pop(index))
            else:
                self.left_langs.pop()
                self.left_langs.insert(0, code)
            self.settings.set_value('left-langs',
                                    GLib.Variant('as', self.left_langs))
        else:
            self.left_lang_label.set_label('Auto')

        # Rewrite recent langs
        self.left_lang_selector.clear_recent()
        self.left_lang_selector.insert_recent('auto', 'Auto')
        for code in self.left_langs[1:]:
            name = LANGUAGES[code].capitalize()
            self.left_lang_selector.insert_recent(code, name)

        # Refresh list
        self.left_lang_selector.refresh_selected()

    def on_right_lang_changed(self, _obj, _param):
        code = self.right_lang_selector.get_property('selected')
        name = LANGUAGES[code].capitalize()
        self.right_lang_label.set_label(name)
        # Updated saved right langs list
        if code in self.right_langs:
            # Bring lang to the top
            index = self.right_langs.index(code)
            self.right_langs.insert(0, self.right_langs.pop(index))
        else:
            self.right_langs.pop()
            self.right_langs.insert(0, code)
        self.settings.set_value('right-langs',
                                GLib.Variant('as', self.right_langs))

        # Rewrite recent langs
        self.right_lang_selector.clear_recent()
        for code in self.right_langs[1:]:
            name = LANGUAGES[code].capitalize()
            self.right_lang_selector.insert_recent(code, name)

        # Refresh list
        self.right_lang_selector.refresh_selected()

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

    def add_history_entry(self, first_language, second_language, first_text, second_text):
        new_history_trans = {
            'Languages': [first_language, second_language],
            'Text': [first_text, second_text]
        }
        if self.current_history > 0:
            del self.history[:self.current_history]
            self.current_history = 0
        if len(self.history) > 0:
            self.return_btn.set_sensitive(True)
        if len(self.history) == TRANS_NUMBER:
            self.history.pop()
        self.history.insert(0, new_history_trans)
        GLib.idle_add(self.reset_return_forward_btns)

    def switch_all(self, first_language, second_language, first_text, second_text):
        self.left_lang_selector.set_property('selected', second_language)
        self.right_lang_selector.set_property('selected', first_language)
        self.left_buffer.set_text(second_text)
        self.right_buffer.set_text(first_text)
        self.add_history_entry(first_language, second_language, first_text, second_text)

        # Re-enable widgets
        self.left_lang_btn.set_sensitive(True)
        self.right_lang_btn.set_sensitive(True)
        self.switch_btn.set_sensitive(True)
        self.translate_btn.set_sensitive(self.left_buffer.get_char_count() != 0)

    def switch_auto_lang(self, second_language, first_text, second_text):
        first_language = str(self.translator.detect(first_text).lang)

        # Switch all
        GLib.idle_add(self.switch_all, first_language, second_language, first_text, second_text)

    def ui_switch(self, _button):
        # Get variables
        self.left_lang_btn.set_sensitive(False)
        self.right_lang_btn.set_sensitive(False)
        self.switch_btn.set_sensitive(False)
        self.translate_btn.set_sensitive(False)
        first_buffer = self.left_buffer
        second_buffer = self.right_buffer
        first_language = self.left_lang_selector.get_property('selected')
        second_language = self.right_lang_selector.get_property('selected')
        first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
        second_text = second_buffer.get_text(second_buffer.get_start_iter(), second_buffer.get_end_iter(), True)
        if first_language == 'auto':
            if first_text == '':
                first_language = self.left_langs[0]
            else:
                threading.Thread(
                    target=self.switch_auto_lang,
                    args=(second_language, first_text, second_text)
                ).start()
                return

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
        second_language_voice = self.right_lang_selector.get_property('selected')
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

        if not self.settings.get_boolean('live-translation'):
            if control_mask == modifiers:
                if keyboard.keyval == Gdk.KEY_Return:
                    if not self.settings.get_value('translate-accel'):
                        self.translation(button)
                        return Gdk.EVENT_STOP
                    return Gdk.EVENT_PROPAGATE
            elif keyboard.keyval == Gdk.KEY_Return:
                if self.settings.get_value('translate-accel'):
                    self.translation(button)
                    return Gdk.EVENT_STOP
                return Gdk.EVENT_PROPAGATE

        return Gdk.EVENT_PROPAGATE

    def text_changed(self, buffer):
        sensitive = buffer.get_char_count() != 0
        self.translate_btn.set_sensitive(sensitive)
        self.clear_btn.set_sensitive(sensitive)

    def user_action_ended(self, buffer):
        if self.settings.get_boolean('live-translation'):
            self.translation(None)

    # The history part
    def reset_return_forward_btns(self):
        self.return_btn.set_sensitive(self.current_history < len(self.history) - 1)
        self.forward_btn.set_sensitive(self.current_history > 0)

    # Retrieve translation history
    def history_update(self):
        self.reset_return_forward_btns()
        lang_hist = self.history[self.current_history]
        self.left_lang_selector.set_property('selected',
                                             lang_hist['Languages'][0])
        self.right_lang_selector.set_property('selected',
                                              lang_hist['Languages'][1])
        self.left_buffer.set_text(lang_hist['Text'][0])
        self.right_buffer.set_text(lang_hist['Text'][1])

    # THE TRANSLATION AND SAVING TO HISTORY PART
    def appeared_before(self):
        first_language = self.left_lang_selector.get_property('selected')
        second_language = self.right_lang_selector.get_property('selected')
        first_text = self.left_buffer.get_text(self.left_buffer.get_start_iter(), self.left_buffer.get_end_iter(), True)
        if (self.history[self.current_history]['Languages'][0] == first_language and
                self.history[self.current_history]['Languages'][1] == second_language and
                self.history[self.current_history]['Text'][0] == first_text):
            return True
        return False

    def translation(self, _button):
        # If it's like the last translation then it's useless to continue
        if len(self.history) == 0 or not self.appeared_before():
            self.copy_btn.set_sensitive(True)
            self.voice_btn.set_sensitive(True)
            first_buffer = self.left_buffer
            second_buffer = self.right_buffer
            first_text = first_buffer.get_text(first_buffer.get_start_iter(), first_buffer.get_end_iter(), True)
            # If the first text is empty, then everything is simply resetted and nothing is saved in history
            if first_text == '':
                second_buffer.set_text('')
            else:
                first_language = self.left_lang_selector.get_property('selected')
                second_language = self.right_lang_selector.get_property('selected')

                if self.trans_queue:
                    self.trans_queue.pop(0)
                self.trans_queue.append({
                    'first_text': first_text,
                    'first_language': first_language,
                    'second_language': second_language
                })

                # Check if there are any active threads.
                if self.active_thread is None:
                    self.trans_spinner.start()
                    self.right_box.set_sensitive(False)
                    # If there are not any active threads, create one and start it.
                    self.active_thread = threading.Thread(target=self.run_translation, daemon=True)
                    self.active_thread.start()

    def run_translation(self):
        while self.trans_queue:
            # If the first language is revealed automatically, let's set it
            trans_dict = self.trans_queue.pop(0)
            first_text = trans_dict['first_text']
            first_language = trans_dict['first_language']
            second_language = trans_dict['second_language']
            if first_language == 'auto' and first_text != '':
                first_language = str(self.translator.detect(first_text).lang)
                GLib.idle_add(self.left_lang_selector.set_property,
                              'selected', first_language)
                self.left_langs[0] = first_language
                self.settings.set_value('left-langs',
                                        GLib.Variant('as', self.left_langs))
            # If the two languages are the same, nothing is done
            if first_language != second_language:
                second_text = ''
                # If the text is over the highest number of characters allowed, it is truncated.
                # This is done for avoiding exceeding the limit imposed by Google.
                if len(first_text) > 100:
                    first_text = first_text[:MAX_LENGTH]
                # THIS IS WHERE THE TRANSLATION HAPPENS. The try is necessary to circumvent a bug of the used API
                try:
                    second_text = self.translator.translate(
                        first_text,
                        src=first_language,
                        dest=second_language
                    ).text
                except Exception:
                    pass
                GLib.idle_add(self.right_buffer.set_text, second_text)

                # Finally, everything is saved in history
                self.add_history_entry(first_language, second_language, first_text, second_text)
        GLib.idle_add(self.trans_spinner.stop)
        GLib.idle_add(self.right_box.set_sensitive, True)
        self.active_thread = None
