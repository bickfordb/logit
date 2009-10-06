#!/usr/bin/python
"""Minimal, modern, simple hierarchical logging system"""
from __future__ import with_statement

__author__ = "Brandon Bickford <bickfordb@gmail.com>"
__version__ = "1.0"
__license__ = "LGPL v3.0 or later."

import datetime
import errno
import os
import sys
import string
import threading
import traceback
import types
import weakref

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        json = None

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

def obj_type_to_name(object):
    """Convert an object to a logger name"""
    if isinstance(object, types.ModuleType):
        return object.__name__
    else:
        obj_type = object if isinstance(object, type) else type(object)
        mod = obj_type.__module__
        if mod != '__main__':
            return mod + '.' + obj_type.__name__
        else:
            return obj_type.__name__

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
    def __init__(self, name=u'', children=None, level=Level.NOTSET, parent=None, filters=(), sinks=(), event_type=Event):
        self.children = children if children is not None else {}
        self.level = level
        self._parent = weakref.ref(parent) if parent is not None else None
        self.event_type = event_type
        self.filters = list(filters)
        self.sinks = list(sinks)

        if name is None:
            name = u''
        elif isinstance(name, str):
            try:
                name = name.decode('utf-8')
            except UnicodeDecodeError, decoding_error:
                name = name.decode('latin-1')
        self.name = name

    def __repr__(self):
        return u"<log.Log(name=%r, level=%r) at 0x%X>" % (self.path(), self.level, id(self))

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
            return p.effective_level
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

    def get(self, name_or_obj=None):
        if name_or_obj is None or name_or_obj == '':
            return self
        if not isinstance(name_or_obj, basestring):
            name = obj_type_to_name(name_or_obj)
        else:
            name = name_or_obj

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
        try:
            exc_info = kwargs.pop('exc_info')
        except KeyError:
            exc_info = None

        event = self.event_type(logger=self, level=level, message=message, args=args, kwargs=kwargs, exc_info=exc_info)
        self.event(event)

    def trace(self, message, *args, **kwargs):
        """Log a trace message"""
        self.log(Level.TRACE, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        """Log a warning message"""
        self.log(Level.ERROR, message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        """Log a warning message"""
        try:
            exc_info = kwargs.pop('exc_info')
        except KeyError:
            exc_info = sys.exc_info()

        try:
            level = kwargs.pop('level')
        except KeyError:
            level = Level.ERROR
        self.log(level, message, exc_info=exc_info, *args, **kwargs)

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

    def event(self, event):
        """Handle a log event"""
        if self.effective_level > event.level:
            self.skip(event)
            return

        for filter_ in self.filters:
            if not filter_(event):
                self.skip(event)
                return

        for sink in self.sinks:
            sink(event)

        parent = self.parent()
        if parent is not None:
            parent.event(event)

    def basic_config(self,
            layout_fields=None,
            layout_sep="\t",
            level=Level.ERROR,
            stream=sys.stderr,
            filename=None,
            file_mode='a'):
        """Setup basic logging.

        Note: this will reset the configuration on this logger, so this
        is safe to call repeatedly, but you may inadvertently reset settings made elsewhere.
        """
        if filename is not None:
            stream = open(filename, file_mode)

        sink = StreamSink(stream=stream, layout=TextLayout(fields=layout_fields, sep=layout_sep))

        self.sinks = [sink]
        self.level = level

    def trace_it(self, function):
        """Trace a function

        Example usage:

        dogs/spaniel.py:

        _log = log.get("dogs.spaniel")
        @_log.trace_it
        def bark():
            ....
        """
        def _trace_it(*args, **kwargs):
            self.log(Level.TRACE, 'entering %r' % (function, ))
            result = function(*args, **kwargs)
            self.log(Level.TRACE, 'exited %r' % (function, ))
            return result
        _trace_it.__name__ = function.__name__ + '_trace_it'
        _trace_it.__doc__ = function.__doc__
        return _trace_it



    def intercept(self, message='Got an exception', level=Level.ERROR, exception_types=(Exception, )):
        """Intercept exceptions and log a message."""
        def _catch_it(function):
            def new_function(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except exception_types, exception:
                    self.exception(message, level=level, exc_info=sys.exc_info(),
                            function=function, kwargs=kwargs, args=args,
                            append_traceback=True)
                    raise

_root_logger = Log()
get = _root_logger.get
basic_config = _root_logger.basic_config
error = _root_logger.error
warning = _root_logger.warning
info = _root_logger.info
debug = _root_logger.debug
trace = _root_logger.trace
trace_it = _root_logger.trace_it

def trace_method(method):
    """Trace a method"""
    def trace_method_(self, *args, **kwargs):
        log = get(self)
        log.trace('entering %(method)r', method=method)
        result = method(self, *args, **kwargs)
        log.trace('exited %(method)r', method=method)
        return result
    return trace_method_

def trace_function(function):
    """Trace a function"""
    def trace_function_(*args, **kwargs):
        log = get()
        log.trace('entering %(function)r', function=function)
        result = function(*args, **kwargs)
        log.trace('exited %(function)r', function=function)
        return result
    return trace_function_

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
            fields = [self.layout_time, self.layout_log, self.layout_level, self.safe_layout_message]
        self.fields = fields
        self.sep = sep

    @classmethod
    def layout_log(cls, event):
        return event.logger.path()

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

    def __call__(self, event):
        result = self.sep.join(field_function(event) for field_function in self.fields)
        return result


if json:
    class FallbackJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            return repr(obj)
else:
    FallbackJSONEncoder = None

class JSONLayout(object):
    def __init__(self, encoder=FallbackJSONEncoder()):
        self.encoder = encoder

    def __call__(self, event):

        tb = traceback.format_exception(*event.exc_info) \
                if event.exc_info is not None else None

        result = {
                'time': unicode(event.time),
                'message': TextLayout.layout_message(event),
                'args': event.args,
                'kwargs': event.kwargs,
                'level': Level.labels.get(event.level, event.level),
                'traceback': tb,
        }
        return self.encoder.encode(result)

class StreamSink(Sink):
    def __init__(self, stream=sys.stderr, layout=None, **kwargs):
        super(StreamSink, self).__init__(**kwargs)
        self.stream = stream
        self.lock = threading.Lock()
        self.layout = layout if layout is not None else TextLayout()

    def __call__(self, event):
        if self.level > event.level:
            return
        with self.lock:
            self.stream.write(self.layout(event) + "\n")
            self.stream.flush()

class LogProperty(object):
    def __init__(self, force_logger=None, parent=None):
        if force_logger and isinstance(force_logger, basestring):
            force_logger = get(force_logger)
        self.force_logger = force_logger
        self.parent = None

    def __get__(self, obj, objtype):
        if not self.force_logger:
            if parent:
                return parent.get(objtype)
            else:
                return get(objtype)
        else:
            return self.force_logger


class RotateByTimeSink(StreamSink):
    """Rotate a log by time
    
    This will defer setup until messages are actually sent.

    Usage:
    import log

    sink = log.RotateByTimeSink('/var/logs/myservice-%Y%m%d-%H0000.log')
    log.get().sinks.append(sink)

    Arguments
    base_path -- string, a path formattable with strftime
    make_dirs -- bool, try to create a subdirectory whenever we switch to a new log
    """
    def __init__(self, base_path, make_dirs=True, **kwargs):
        self.base_path = base_path
        self.curr_path = None
        self.make_dirs = make_dirs
        super(RotateByTimeSink, self).__init__(stream=None, **kwargs)

    def safe_mkdir(self, directory):
        """Try to make a directory and ignore file exists errors."""
        try:
            os.makedirs(directory)
        except OSError, error:
            if error.errno != errno.EEXIST:
                raise

    @property
    def path(self):
        """Get the current path for this logging.

        When this changes, the log will rotate to this new path.
        """
        return datetime.datetime.now().strftime(self.base_path)

    def check_rotate(self):
        """Check to see if rotation is necessary, and if so, reset the stream."""
        if self.path != self.curr_path:
            with self.lock:
                self.curr_path = self.path
                if self.stream is not None:
                    self.stream.close()
                    self.stream = None
                if self.make_dirs:
                    self.safe_mkdir(os.path.dirname(self.curr_path))
                self.stream = open(self.curr_path, 'a')

    def __call__(self, event):
        self.check_rotate()
        super(RotateByTimeSink, self).__call__(event)

