# A simple logging library for Python

Differences between the Python logging API:

 * logit system will never call *sys.exit*
 * No camel case
 * No silent message dropping (let the program crash if there are bugs)
 * Decorator and contextmanager helpers
 * Attempt to be light and straightforward in every way
 * Sink and filter types are plain functions
 * Nicer looking API: `logit.log.planets.mercury` instead of `logging.getLogger('planets.mercury')`

Basic Usage:

*examplelib.py*

    import logit

    log = logit.log.examplelib

    def bar():
        log.bar.info('hey!')

    class Widget(object):
        log = log.Widget

        def foo(self):
            self.log.info('hello!')

*examplemain.py*

    import time
    import logit

    import examplelib

    log = logit.log.examplemain

    class FizBuzz(object):

        @log.trace_method
        def x(self):
            pass

    if __name__ == '__main__':
        logit.basic_config(level=logit.Level.TRACE)

        # Setup a rotating text log for all of examplelib.Widget's messages
        filesink = logit.RotateByTimeSink('logs/%Y/%m/%d/foo.log')
        examplelib.log.Widget.sinks.append(filesink)

        # Setup a JSON Stream:
        json_sink = logit.StreamSink(layout=logit.JSONLayout())
        examplelib.log.sinks.append(json_sink)

        # Print out some trace messages to stderr
        a = FizBuzz()
        a.x()

        # Print out some messages to the JSON stream
        examplelib.Widget().foo()
        a.x()
        examplelib.bar()
        logit.error('hello')
        examplelib.Widget().foo()
