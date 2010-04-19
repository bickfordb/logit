A more modern logging library for Python
=================================

Differences between the Python logging API:

 * Logging system will never call sys.exit
 * Less camel case
 * No silent message dropping (let the program crash if there are bugs)
 * Decorator and contextmanager helpers
 * Attempt to be light and straightforward in every way
 * Slightly nicer API: "logit.get(planets.Mercury)" instead of "logging.getLogger('planets.mercury')"

Basic Usage:

examplelib.py: 
---
    import logit

    def bar():
        logit.get(__name__).info('hey!')

    class Widget(object):
        def foo(self):
            logit.get(Widget).info('hello!')


examplemain.py:
---
    import time

    import examplelib
    import logit

    class FizBuzz(object):
        @logit.trace_method
        def x(self):
            pass

    if __name__ == '__main__':
        logit.basic_config(level=logit.Level.TRACE)

        # Setup a rotating text log for all of examplelib.Widget's messages
        filesink = logit.RotateByTimeSink('logs/%Y/%m/%d/foo.log')
        logit.get(examplelib.Widget).sinks.append(filesink)

        # Setup a JSON Stream:
        json_sink = logit.StreamSink(layout=logit.JSONLayout())
        logit.get(examplelib).sinks.append(json_sink)

        # Print out some trace messages to stderr
        a = FizBuzz()
        a.x()

        # Print out some messages to the JSON stream
        examplelib.Widget().foo()
        a.x()
        examplelib.bar()
        logit.error('hello')
        examplelib.Widget().foo()
