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
