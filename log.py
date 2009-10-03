#!/usr/bin/python
"""Hierarchical logging system
"""
from __future__ import with_statement

import datetime
import sys
import threading
import weakref

class Level(int):
    """Log levels"""
    NOTSET = 0
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40

    labels = {
            TRACE: u'TRACE',
            DEBUG: u'DEBUG',
            ERROR: u'ERROR',
            INFO: u'INFO',
            NOTSET: u'NOTSET',
            WARNING: u'WARNING',
    }

class Event(object):
    """A log event"""
    def __init__(self, logger=None, level=Level.NOTSET, message=u'', args=(), kwargs=None, exc_info=None, time=None):
        self.exc_info = exc_info
        self.logger = logger
        self.level = level
        self.message = message
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.time = time if time is not None else datetime.datetime.now()
 
    def __repr__(self):
        return u"%s(logger=%r, level=%r, message=%r, args=%r, kwargs=%r, time=%r)" % \
                (self.__class__.__name__, self.logger, self.level, self.message, self.args, self.kwargs, self.time)
    
class Log(object):
    """A logger is something which logs messages and events.

    Contructor arguments:
    name -- string, the name of the logger
    children -- None or a dictionary, name to logger mapping of child loggers
    level -- Level.X, the minimum logging level for this logger
    parent -- the logging level for this logger
    filters -- a list of callables.  If any of the callables returns False when accepting an event, the event will be skipped
    event_type -- the type of Event produced by message logging calls
    """
    def __init__(self, name=u'', children=None, level=Level.NOTSET, parent=None, filters=(), handlers=(), event_type=Event):
        self.children = children if children is not None else {}
        self.level = level
        self._parent = weakref.ref(parent) if parent is not None else None
        self.event_type = event_type
        self.filters = list(filters)
        self.handlers = list(handlers)

        if name is None:
            name = u''
        elif isinstance(name, str):
            try:
                name = name.decode('utf-8')
            except UnicodeDecodeError, decoding_error:
                name = name.decode('latin-1')
        self.name = name

    def parent(self):
        """Get the parent logger"""
        if self._parent is not None:
            return self._parent()
        else:
            return None

    @property
    def effective_level(self):
        if self.level != Level.NOTSET:
            return self.level
        p = self.parent()
        if p is not None:
            return p.effective_level()
        else:
            return self.level

    def ancestors(self):
        p = self.parent()
        if p is not None:
            yield p
            for a in p.ancestors():
                yield a

    def path(self):
        """Get the path of a logger as a string"""
        names = [self.name]
        for ancestor in self.ancestors():
            names.append(ancestor.name)
        return u'.'.join(reversed(filter(None, names)))

    def get(self, name=None):
        if not name:
            return self

        rest = name.strip()
        head = ''
        while rest:
            parts = rest.split('.', 1)
            if len(parts) == 1:
                head = parts[0]
                rest = ''
                head = head.strip()
            else:
                head, rest = parts
            if head:
                break

        if not head:
            return self

        try:
            logger = self.children[head]
        except KeyError:
            logger = self.children[head] = type(self)(head, parent=self)
        return logger.get(rest) if rest else logger

    def log(self, level, message, *args, **kwargs):
        """Log a message
        
        Arguments
        level -- int, a log level see WARN, CRITICAL, ...

        """
        event = self.event_type(logger=self, level=level, message=message, args=args, kwargs=kwargs)
        self.event(event)

    def trace(self, message, *args, **kwargs):
        """Log a trace message"""
        self.log(Level.TRACE, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        """Log a warning message"""
        self.log(Level.ERROR, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """Log a warning message"""
        self.log(Level.WARNING, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        """Log a info message"""
        self.log(Level.INFO, message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        """Log a info message"""
        self.log(Level.DEBUG, message, *args, **kwargs)

    def skip(self, event):
        """Override this to do something when events are skipped."""
        pass

    def skip(self, event):
        """Override this to do something when events are skipped."""
        pass

    def event(self, event):
        """Handle a log event"""
        if self.effective_level() > event.level:
            self.skip(event)
            return

        for filter_ in self.filters:
            if not filter_(event):
                self.skip(event)
                return

        for handler in self.handlers:
            handler(event)

        parent = self.parent()
        if parent is not None:
            parent.event(event)

    def basic_config(self,
            layout_fields=None,
            layout_sep="\t",
            level=Level.NOTSET,
            stream=sys.stderr,
            filename=None,
            file_mode='a'):
        """Setup basic logging.
        
        Note: this will reset the configuration on this logger, so this
        is safe to call repeatedly, but you may inadvertently reset settings made elsewhere.
        """
        if filename is not None:
            stream = open(filename, file_mode)

        handler = StreamSink(stream=stream, fields=layout_fields, sep=layout_sep)
         
        self.handlers = [handler]
        self.level = level

    def trace_it(self, message='tracing', level=Level.TRACE, before=True, after=True):
        """Trace a function
        
        Example usage:

        dogs/spaniel.py:

        _log = log.get("dogs.spaniel")
        @_log.traceit("Got a bark")
        def bark():
            ....

        """
        def _trace_decorator(function):
            def new_function(*args, **kwargs):
                if before:
                    self.log(level, message, function=function, args=args, kwargs=kwargs)
                result = function(*args, **kwargs)
                if after:
                    self.log(level, message)
                return result
            new_function.__name__ = function.__name__ + '_traced'
            new_function.__doc__ = function.__doc__
            return new_function
        return _trace_decorator

    def intercept(self, message='Got an exception', level=Level.ERROR, exception_types=(Exception, )):
        """Intercept exceptions and log a message."""
        def _catch_it(function):
            def new_function(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except exception_types, exception:
                    self.log(level, message, exc_info=sys.exc_info(),
                            function=function, kwargs=kwargs, args=args,
                            append_traceback=True)
                    raise

class Sink(object):
    def __init__(self, level=Level.NOTSET):
        self.level = level

def safesub(s, vals):
    """Try to Substitute vals into s and if any Exception(s) occur, return s"""
    try:
        return s % vals
    except Exception, some_exception: 
        return s

class Layout(object):
    def __call__(self, event):
        """Layout an event into some formatted value (a string?)"""
        return ''

class TextLayout(Layout):
    def __init__(self, sep='\t', fields=None):
        if fields is None:
            fields = [self.layout_time, self.layout_level, self.safe_layout_message]
        self.fields = fields
        self.sep = sep

    @classmethod
    def layout_message(self, event):
        msg = event.message
        if event.args:
            msg = msg % event.args

        if event.kwargs:
            msg = msg % event.kwargs

        return msg

    @classmethod
    def safe_layout_message(self, event):
        msg = event.message
        if event.args:
            msg = safesub(msg, event.args)
        if event.kwargs:
            msg = safesub(msg, event.kwargs)
        return msg

    @classmethod
    def layout_time(self, event):
        return unicode(event.time)

    @classmethod
    def layout_level(self, event):
        return Level.labels.get(event.level, unicode(event.level))

    def ___call__(self, event):
        return self.sep.join(field_function(event) for field_function in self.fields)

class StreamSink(Sink):
    def __init__(self, stream=sys.stderr, formatter=None, **kwargs):
        super(StreamSink, self).__init__(**kwargs)
        self.stream = stream
        self.lock = threading.Lock()
        self.formatter = formatter if formatter is not None else Formatter()

    def __call__(self, event):
        if self.level > event.level:
            return
        with self.lock:
            print >> self.stream, self.formatter(event)
            self.stream.flush()

_root_logger = Log()
get = _root_logger.get
basic_config = _root_logger.basic_config
error = _root_logger.error
warning = _root_logger.warning
info = _root_logger.info
debug = _root_logger.debug
trace = _root_logger.trace





