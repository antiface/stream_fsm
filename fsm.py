# -*- coding: utf-8 -*-

from builtins import super
from collections import deque


class EventAccessorFactory(deque):
    def __init__(self, pusher=None, getter=None):
        super().__init__()
        self.getter = getter
        self.pusher = pusher
        self.ongoing = True

    def getq(self):
        if not self:
            try:
                self.append(self.getter())
            except StopIteration:
                self.ongoing = False
        return self

    def pushe(self, data):
        self.append(data)
        self.pusher(self)


class StreamManager(object):
    """A stream analyser, grammar or finite state machine
       supporting both push and pull patterns.
    """

    def __init__(self):
        super().__init__()
        self.accessor = EventAccessorFactory(self.pushq, self.getter)

    def reassign(self, ch):
        self.accessor.append(ch)

    def run(self):
        self.accessor.ongoing = True
        while self.accessor.ongoing:
            self.pushq(self.accessor.getq())
        return self.value

    def pushq(self, queue):
        while queue:
            self.process(queue.popleft())

    def close(self):
        self.accessor.ongoing = False


class Action(tuple):
    def __new__(cls, *args):
        return tuple.__new__(cls, args)


class FSM(object):
    def __init__(self):
        super().__init__()
        self.subtree = self.tree

    def process(self, ch):
        for sub in self.subtree:
            ev = sub[0]
            if not ev or ch == ev:
                break
            elif isinstance(ev, tuple):
                if ev[0] <= ch <= ev[1]:
                    break
        # event is not found in subtree
        else:
            if not getattr(self, 'drop_missing_event', False):
                self.reassign(ch)
            self.subtree = self.tree
            return
        action = sub[1]
        if isinstance(action, Action):
            self.subtree = self.tree
            if not action[0]:
                return
            self.ch = ch
            f = getattr(self, action[0])
            f(*action[1:])
        else:
            self.subtree = action
