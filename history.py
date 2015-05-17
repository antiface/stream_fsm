# -*- coding: utf-8 -*-

import os
import sys
import tty, termios

from fsm import *

A = Action


def getch(*args):
    # credit: http://rosettacode.org/wiki/Keyboard_input/Keypress_check#Python
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class SearchWriter(object):
    def open(self, prompt='search: '):
        sys.stdout.write(prompt)
        self.prompt_len = len(prompt)
        self.chars = ''

    def close(self):
        for x in self.chars:
            sys.stdout.write('\x08 \x08')
        sys.stdout.write('\x08 \x08' * self.prompt_len)

    def update(self, chars):
        if chars != self.chars:
            for x in self.chars:
                sys.stdout.write('\x08 \x08')
            sys.stdout.write(chars)
            self.chars = chars


class SearchFSM(FSM, StreamManager):
    tree = (
        ('\r', A('close', 'close')),
        ('\x03', A('close', 'nada')), # Ctrl-C
        ('\x09', A('close', 'edit')), # Tab
        ('\x7f', A('backspace')),
        ('\x1b', (
            ('[', (
                ('A', A('next')),
                ('B', A('previous')),
                ('H', A('first')),
                ('F', A('last')),
            )),
        )),
        (('\x00', '\x1f'), A('')),
        ('', A('insert')),
    )
    getter = getch

    def __init__(self, history):
        super().__init__()
        self.history = history
        self.line_writer = SearchWriter()
        self.init()

    def init(self):
        self.index = len(self.history)
        self.chars = []
        self.selection = ''

    def get_selection(self):
        try:
            self.selection = self.history[self.index]
        except IndexError:
            self.selection = ''

    def find(self, chars):
        try:
            return chars in self.history[self.index]
        except IndexError:
            return False

    def find_first_at_index(self, reset=False):
        old_index = self.index
        if reset:
            self.index = len(self.history) - 1
        elif self.index >= 0:
            self.index -= 1
        chars = ''.join(self.chars)
        while self.index >= 0:
            if self.find(chars):
                break
            self.index -= 1
        if self.index < 0:
            self.index = old_index
        self.get_selection()

    def backspace(self):
        if self.chars:
            self.chars.pop()
            self.find_first_at_index(True)
            self.line_writer.update(self.selection)

    def insert(self):
        self.chars.append(self.ch)
        self.find_first_at_index(True)
        self.line_writer.update(self.selection)

    def next(self):
        self.find_first_at_index()
        self.line_writer.update(self.selection)

    def previous(self, reset=False):
        old_index = self.index
        if reset:
            self.index = 0
        elif self.index < len(self.history):
            self.index += 1
        chars = ''.join(self.chars)
        while self.index < len(self.history):
            if self.find(chars):
                break
            self.index += 1
        if self.index >= len(self.history):
            self.index = old_index
        self.get_selection()
        self.line_writer.update(self.selection)

    def first(self):
        self.find_first_at_index(True)
        self.line_writer.update(self.selection)

    def last(self):
        self.previous(True)
        self.line_writer.update(self.selection)

    def open(self):
        self.line_writer.open()

    def close(self, cmd):
        super().close()
        self.line_writer.close()
        self.value = cmd, self.index if self.index >= 0 else len(self.history)


class LineWriter(object):
    def __init__(self):
        self.init()

    def init(self, chars=None):
        self.chars = chars or []
        self.index = len(self.chars)

    def insert(self, ch):
        if self.index == len(self.chars):
            self.chars.append(ch)
        else:
            self.chars.insert(self.index, ch)
        sys.stdout.write(''.join(self.chars[self.index:]))
        self.index += 1
        for x in xrange(len(self.chars) - self.index):
            sys.stdout.write('\x08')

    def backspace(self):
        if self.index:
            sys.stdout.write('\x08 \x08')
            self.index -= 1
            self.chars.pop(self.index)

    def update(self, chars):
        for x in xrange(len(self.chars) - self.index):
            sys.stdout.write(' ')
        for x in self.chars:
            sys.stdout.write('\x08 \x08')
        sys.stdout.write(''.join(chars))
        self.init(chars)

    def left(self):
        if self.index:
            sys.stdout.write('\x08')
            self.index -= 1

    def right(self):
        if self.index < len(self.chars):
            sys.stdout.write(self.chars[self.index])
            self.index += 1

    def home(self):
        sys.stdout.write('\x08' * self.index)
        self.index = 0

    def end(self):
        sys.stdout.write(''.join(self.chars[self.index:]))
        self.index = len(self.chars)


class KeybFSM(FSM, StreamManager):
    """consumed events can't be reassigned
    """
    tree = (
        ('\r', A('close')),
        ('\x03', A('close', '')), # Ctrl-C
        ('\x12', A('search')), # Ctrl-R
        ('\x15', A('clear')), # Ctrl-U
        ('\x7f', A('backspace')),
        ('\x1b', (
            ('[', (
                ('A', A('up')),
                ('B', A('down')),
                ('C', A('right')),
                ('D', A('left')),
                ('H', A('home')),
                ('F', A('end')),
            )),
        )),
        (('\x00', '\x1f'), A('')),
        ('', A('insert')),
    )
    getter = getch

    def __init__(self, history):
        super().__init__()
        self.history = history
        self.line_writer = LineWriter()
        self.search_fsm = SearchFSM(history)
        self.init()

    def init(self):
        self.index = len(self.history)
        self.set_chars()

    def set_chars(self):
        try:
            self.chars = self.history[self.index]
        except IndexError:
            self.chars = ''

    def update(self):
        self.line_writer.update(list(self.chars))

    def insert(self):
        self.line_writer.insert(self.ch)

    def close(self, chars=None):
        super().close()
        self.value = ''.join(self.line_writer.chars) if chars is None else chars

    def backspace(self):
        self.line_writer.backspace()

    def left(self):
        self.line_writer.left()

    def right(self):
        self.line_writer.right()

    def home(self):
        self.line_writer.home()

    def end(self):
        self.line_writer.end()

    def up(self):
        if self.index > 0:
            self.index -= 1
            self.chars = self.history[self.index]
            self.update()

    def down(self):
        if self.index < len(self.history):
            self.index += 1
            self.set_chars()
            self.update()

    def clear(self):
        self.init()
        self.update()

    def search(self):
        self.clear()
        self.search_fsm.open()
        todo, index = self.search_fsm.run()
        if todo == 'edit':
            self.index = index
            self.set_chars()
            self.update()
        elif todo == 'close':
            self.close(self.history[index])
        elif todo == 'nada':
            self.update()


class EntryHistory(object):
    def __init__(self, file='default.hst', folder='~/.history', max_len=50):
        self.max_len = max_len
        self.folder = os.path.abspath(os.path.expanduser(folder))
        if not os.path.isdir(self.folder):
            try:
                os.makedirs(self.folder)
            except OSError:
                raise RuntimeError("Folder '%s' does not exist, and cannot create it, aborting" % self.folder)
        elif not os.access(self.folder, os.W_OK):
            raise RuntimeError("Folder %s write access denied, aborting" % self.folder)
        self.file = os.path.join(self.folder, file)
        try:
            with open(self.file, 'r') as f:
                self.history = [x.strip() for x in f.readlines() if x.strip()]
        except IOError:
            self.history = []
        self.input_stream = KeybFSM(history=self.history)

    def close(self, value):
        if value:
            try:
                self.history.remove(value)
            except ValueError:
                pass
            self.history.append(value)
            try:
                with open(self.file, 'w') as f:
                    f.write('\n'.join(self.history[-self.max_len:]))
            except IOError:
                pass

    def __call__(self):
        value = self.input_stream.run()
        self.close(value)
        return value


if __name__ == '__main__':
    val = EntryHistory()()
    print '\n', val
