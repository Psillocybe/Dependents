import sublime, sublime_plugin
import subprocess
import threading
import os
import re
from subprocess import Popen, PIPE
from .preconditions import *
from .thread_progress import ThreadProgress

class DependentsCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings('Dependents.sublime-settings')

        self.window.root    = settings.get('root')
        self.window.config  = settings.get('config')

        if not self.window.root:
            show_error('Please set the "root" in \nPreferences -> Package Settings -> Dependents -> Settings - User')
            return

        self.view           = self.window.active_view()
        self.view.filename  = self.view.file_name()

        # The part of the path before the root
        self.view.path = self.view.filename[:self.view.filename.index(self.window.root)]

        if not met(self.view.path):
            return

        thread = DependentsThread(self.window, self.view)
        thread.start();

        ThreadProgress(thread, 'Finding dependents', '')

class DependentsThread(threading.Thread):
    """
    A thread to prevent the determination of the dependents from freezing the UI
    """
    def __init__(self, window, view):
        self.window = window
        self.view = view
        threading.Thread.__init__(self)

    def run(self):
        """
        Finds the dependents of the current file and jumps to that file or shows a panel of dependent files
        """

        self.dependents = self.trim_paths(self.get_dependents())

        if len(self.dependents) == 1:
            self.open_file(self.dependents[0])
        else:
            sublime.set_timeout(self.show_quick_panel, 10)

    def get_dependents(self):
        """
        Asks the node tool for the dependents of the current module
        """
        cmd = [
            '/usr/local/bin/node',
            self.view.path + 'node_modules/dependents/bin/dependents.js',
            self.view.filename,
            self.view.path + self.window.root
        ]

        # if self.window.config:
        #     cmd.append(self.window.config)

        print('Executing: ', ' '.join(cmd))

        dependents = Popen(cmd, stdout=PIPE).communicate()[0]
        dependents = dependents.decode('utf-8').split('\n')
        print('Found ', '\n'.join(dependents))
        return dependents

    def trim_paths(self, files):
        """
        Returns the filepaths for each file minus the root and its trailing slash
        """
        trimmed = []

        for f in files:
            if f:
                trimmed.append(f[f.index(self.window.root) + len(self.window.root) + 1:])

        return trimmed

    def show_quick_panel(self):
        if not self.dependents:
            show_error('\nCan\'t find any file that depends on this file')
            return

        self.window.show_quick_panel(self.dependents, self.on_done)

    def on_done(self, picked):
        if picked == -1:
            return

        dependent = self.dependents[picked]
        self.open_file(dependent)

    def open_file(self, dependent):
        # We removed the root originally when populating the dependents list
        filename = self.view.path + self.window.root + '/' + dependent

        if not os.path.isfile(filename):
            cant_find_file()
            return

        def open():
            self.window.open_file(filename)

        sublime.set_timeout(open, 10)

def cant_find_file():
    show_error('Can\'t find that file')

def show_error(string):
    sublime.error_message(u'Dependents\n%s' % string)
