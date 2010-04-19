import unittest

import logit

class LogItBasicTestCase(unittest.TestCase):
    def setUp(self):
        self.root = logit.Log()
        self.events = []
        self.root.sinks.append(self.events.append)

    def test_get(self):
        result = self.root.get('something')
        assert isinstance(result, logit.Log)
        assert result is not None

    def test_getitem(self):
        assert self.root['red'] == self.root.get('red')

    def test_getattr(self):
        assert self.root.red == self.root.get('red')

    def test_get_empty(self):
        assert self.root is self.root.get('')
        assert self.root is self.root.get(u'')

    def test_get_path(self):
        assert self.root.get('a.b.c') is self.root.a.b.c

    def test_path(self):
        assert self.root.a.b.c.path() == 'a.b.c'

    def test_parent(self):
        assert self.root.something.parent() is self.root

    def test_log_level(self):
        sublogger = self.root.sublogger
        sublogger_events = []
        sublogger.sinks.append(sublogger_events.append)
        self.root.sublogger.level = logit.Level.WARNING
        self.root.sublogger.info('hey')
        assert len(sublogger_events) == 0
        # Warning events should go through:
        sublogger.warning('hey')
        assert len(self.events) == 1

    def test_filter(self):
        sublogger = self.root.sublogger

        def always_false(event):
            return False

        # Make sure errors normally go through:
        sublogger.error('some error')
        assert len(self.events) == 1
        del self.events[:]

        # Now add a filter that always blocks events:
        sublogger.filters.append(always_false)
        sublogger.error('some error')
        assert len(self.events) == 0
    
    def test_info(self):
        self.root.info("info")

if __name__ == '__main__':
    unittest.main()
