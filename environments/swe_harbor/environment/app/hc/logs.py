import logging


class Handler(logging.Handler):
    """Stub logging handler to satisfy hc.settings LOGGING config."""

    def emit(self, record):
        pass
