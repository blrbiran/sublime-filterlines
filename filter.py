import functools
import itertools
import re
import sublime
import sublime_plugin

settings_path = 'FilterLogs.sublime-settings'

class PromptFilterLogsToLinesCommand(sublime_plugin.WindowCommand):

    def run(self, search_type = 'string', invert_search = False, multiple_search = False):
        if not invert_search:
            self._run_A(search_type, "filter_logs_to_lines", "Filter", multiple_search)
        else:
            self._run_B(search_type, "filter_logs_to_lines", "Filter", multiple_search)

    def _run(self, search_type, filter_command, filter_verb, invert_search, multiple_search):
        self.filter_command = filter_command
        self.search_type = search_type
        self.invert_search = invert_search
        self.filter_verb = filter_verb
        self.multiple_search = multiple_search
        if search_type == 'string':
            prompt = "%s logs %s: " % (filter_verb, 'not containing' if self.invert_search else 'containing')
        else:
            prompt = "%s logs %s: " % (filter_verb, 'not matching' if self.invert_search else 'matching')
        if not self.invert_search:
            view = self.window.active_view()
            first = view.sel()[0]  # first region (or point)
            if first.size():
                region = first
                word = view.substr(region)
                self.search_text_1 = word
                self.search_text_1 = "^.*(" + self.search_text_1 + ")+.*$"
            elif self.search_text_1:
                pass
            else:
                region = view.word(first.begin())
                word = view.substr(region).strip()
                self.search_text_1 = word
                self.search_text_1 = "^.*(" + self.search_text_1 + ")+.*$"
            sublime.active_window().show_input_panel(prompt, self.search_text_1, self.on_search_text_entered, None, None)
        else:
            view = self.window.active_view()
            first = view.sel()[0]  # first region (or point)
            if first.size():
                region = first
                word = view.substr(region)
                self.search_text_2 = word
                self.search_text_2 = "^.*(" + self.search_text_2 + ")+.*$"
            elif self.search_text_2:
                pass
            else:
                region = view.word(first.begin())
                word = view.substr(region).strip()
                self.search_text_2 = word
                self.search_text_2 = "^.*(" + self.search_text_2 + ")+.*$"
            sublime.active_window().show_input_panel(prompt, self.search_text_2, self.on_search_text_entered, None, None)

    def _run_A(self, search_type, filter_command, filter_verb, multiple_search):
        self.load_settings()
        self._run(search_type, filter_command, filter_verb, False, multiple_search)

    def _run_B(self, search_type, filter_command, filter_verb, multiple_search):
        self.load_settings()
        self._run(search_type, filter_command, filter_verb, True, multiple_search)

    def on_search_text_entered(self, search_text):
        self.search_text = search_text
        self.window_name = self.window.active_view().name()
        if self.window.active_view():
            self.window.active_view().run_command(self.filter_command, {
                "needle": self.search_text, "search_type": self.search_type, "invert_search": self.invert_search, "window_name": self.window_name })
        if not self.invert_search and self.multiple_search:
            self.invert_search = True
            self.search_text_2 = "^.*()+.*$"
            self.save_settings()
            self._run_B(self.search_type, "filter_logs_to_lines", "Filter", self.multiple_search)
        self.save_settings()

    def load_settings(self):
        self.settings = sublime.load_settings(settings_path)
        self.search_text_1 = ""
        self.search_text_2 = ""
        if self.settings.get('preserve_search', True):
            self.search_text_1 = self.settings.get('latest_search_1', '')
            self.search_text_2 = self.settings.get('latest_search_2', '')

    def save_settings(self):
        if self.settings.get('preserve_search', True):
            self.settings.set('latest_search_1', self.search_text_1)
            self.settings.set('latest_search_2', self.search_text_2)

class FilterLogsToLinesCommand(sublime_plugin.TextCommand):

    def run(self, edit, needle, search_type, invert_search, window_name):
        settings = sublime.load_settings(settings_path)
        flags = self.get_search_flags(search_type, settings)
        lines = itertools.groupby(self.view.find_all(needle, flags), self.view.line)
        lines = [l for l, _ in lines]
        self.line_numbers = settings.get('line_numbers', False)
        self.new_tab = settings.get('create_new_tab', True)
        self.invert_search = invert_search ^ (not self.new_tab)
        self.window_name = window_name
        self.show_filtered_lines(edit, lines)

    def get_search_flags(self, search_type, settings):
        flags = 0
        if search_type == 'string':
            flags = sublime.LITERAL
            if not settings.get('case_sensitive_string_search', False):
                flags = flags | sublime.IGNORECASE
        elif search_type == 'regex':
            if not settings.get('case_sensitive_regex_search', False):
                flags = sublime.IGNORECASE
        return flags

    def show_filtered_lines(self, edit, lines):
        if self.invert_search:
            filtered_line_numbers = [self.view.rowcol(line.begin())[0] for line in lines]
            lines = self.view.lines(sublime.Region(0, self.view.size()))
            for line_number in reversed(filtered_line_numbers):
                del lines[line_number]

        if self.new_tab:
            text = '\n'.join([self.prepare_output_line(l) for l in lines]);
            self.create_new_tab(text)
        else:
            for line in reversed(lines):
                self.view.erase(edit, self.view.full_line(line))

    def create_new_tab(self, text):
        results_view = self.view.window().new_file()
        results_view.set_name('Filter Results')
        results_view.set_scratch(True)
        results_view.settings().set('word_wrap', self.view.settings().get('word_wrap'))
        results_view.run_command('append', {'characters': text, 'force': True, 'scroll_to_end': False})
        results_view.set_syntax_file(self.view.settings().get('syntax'))

    def prepare_output_line(self, line):
        if self.line_numbers and not self.invert_search and self.window_name != 'Filter Results':
            line_number = self.view.rowcol(line.begin())[0] + 1
            return '%5d: %s' % (line_number, self.view.substr(line))
        else:
            return self.view.substr(line)
