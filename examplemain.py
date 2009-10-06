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
