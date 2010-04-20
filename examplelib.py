import logit

log = logit.log.examplelib

def bar():
    log.bar.info('hey!')

class Widget(object):
    log = log.Widget

    def foo(self):
        self.log.info('hello!')
