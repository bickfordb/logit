import logit

def bar():
    logit.get(__name__).info('hey!')

class Widget(object):
    def foo(self):
        logit.get(Widget).info('hello!')
