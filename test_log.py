import unittest

import log

class TestCase(unittest.TestCase):
    def test(self):
        tree = log.Log()
        red = tree.get('red')
    
        events = []
        def app(event):
            events.append(event)
        
        red.handlers.append(app)
        red.level = log.Level.WARNING
        red.info('hey')
        assert not events

        red.warning('hey')
        assert len(events) == 1

        blue = red.get('blue')

        assert blue.path() == 'red.blue', blue.path()
        assert blue is tree.get('red.blue')

        assert tree is tree.get()
        assert tree is tree.get('')

        assert blue is blue.get()
        assert blue is blue.get('')

        del events[:]
   
        def halt(x):
            return False
        
        red.filters.append(halt)
        blue.error('hey')
        
        assert len(events) == 0

if __name__ == '__main__':
    unittest.main()

