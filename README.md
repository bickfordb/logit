A more modern logging library for Python
=================================

Differences between the Python logging API:

 * Less camel case
 * No silent message dropping (let the program crash if there are bugs)
 * Decorator and contextmanager helpers
 * Shoot for simplicity / straightforward wherever possible
 * Slightly nicer API: "log.get('planets.mercury')" instead of "logging.getLogger('planets.mercury')"

