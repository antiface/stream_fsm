# -*- coding: utf-8 -*-

from contextlib import contextmanager
import sys
try:
    # for py26
    import unittest2 as unittest
except ImportError:
    import unittest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from fsm import EventAccessorFactory, StreamManager, Action, FSM


@contextmanager
def captured_output():
    try:
        sys.stdout, sys.stderr = StringIO(), StringIO()
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__


def mock_getter_factory(data=('a', 'b')):
    it = iter(data)
    def getter(*args):
        return next(it)
    return getter


class TestEventAccessor(unittest.TestCase):

    def test_mock_getter(self):
        g = mock_getter_factory()
        self.assertEqual(g(), 'a')
        self.assertEqual(g(), 'b')
        self.assertRaises(StopIteration, g)

    def test_getq(self):
        accessor = EventAccessorFactory(getter=mock_getter_factory())
        queue = accessor.getq()
        self.assertEqual(list(queue), ['a'])
        accessor.getq()
        self.assertEqual(list(queue), ['a'])
        queue.popleft()
        accessor.getq()
        self.assertEqual(list(queue), ['b'])
        queue.popleft()
        accessor.getq()
        self.assertEqual(list(queue), [])

    def test_append(self):
        accessor = EventAccessorFactory(getter=mock_getter_factory())
        accessor.append('x')
        queue = accessor.getq()
        self.assertEqual(list(queue), ['x'])
        queue.popleft()
        queue = accessor.getq()
        self.assertEqual(list(queue), ['a'])


class TestStreamManager(unittest.TestCase):

    def test_basic_run(self):
        class BasicStream(StreamManager):
            getter = mock_getter_factory()
            value = []
            def update(self, chars):
                pass
            def process(self, event):
                self.value.append(event)
                sys.stdout.write(event)
        stream = BasicStream()
        with captured_output() as (out, err):
            ret = stream.run()
        self.assertEqual(out.getvalue(), "ab")
        self.assertEqual(ret, ['a', 'b'])


class TestAction(unittest.TestCase):

    def test_action(self):
        a = Action('a', 'b', 'c')
        t = tuple(('a', 'b', 'c'))
        self.assertIsInstance(a, Action)
        self.assertIsInstance(a, tuple)
        self.assertEqual(a, t)


class TestFSM(unittest.TestCase):

    def test_flat_fsm(self):
        class FlatFSM(FSM):
            tree = (
                ('a', Action('action_a')),
                ('b', Action('action_b', 'B')),
                ('c', Action('action_b', 'C')),
                (('x', 'z'), Action('action_interval')),
                ('', Action('action_default')),
            )
            value = []
            def action_a(self):
                self.value.append('a')
            def action_b(self, *args):
                self.value.append('b%s' % str(args))
            def action_interval(self):
                self.value.append('i(%s)' % self.ch)
            def action_default(self):
                self.value.append('d(%s)' % self.ch)

        fsm = FlatFSM()
        for x in 'abcys':
            fsm.process(x)
        self.assertEqual(fsm.value, ['a', "b('B',)", "b('C',)", 'i(y)', 'd(s)'])

    def test_nested_fsm(self):
        class NestedFSM(FSM):
            tree = (
                ('a', Action('action_a')),
                ('b', (
                    ('c', Action('action_bc')),
                    ('x', (
                        ('y', Action('action_bxy')),
                    )),
                )),
            )
            value = []
            def action_a(self):
                self.value.append('a')
            def action_bc(self):
                self.value.append('bc')
            def action_bxy(self):
                self.value.append('bxy')

        fsm = NestedFSM()
        for x in 'abcbxy':
            fsm.process(x)
        self.assertEqual(fsm.value, ['a', 'bc', 'bxy'])

    def test_missing_event(self):
        class NoDropMissingFSM(FSM):
            tree = ()
            events_reassigned = []
            def reassign(self, ev):
                self.events_reassigned.append(ev)
        class DropMissingFSM(NoDropMissingFSM):
            drop_missing_event = True

        fsm = DropMissingFSM()
        fsm.process('x')
        self.assertEqual(fsm.events_reassigned, [])
        fsm = NoDropMissingFSM()
        fsm.process('x')
        self.assertEqual(fsm.events_reassigned, ['x'])


if __name__ == '__main__':
    unittest.main()
