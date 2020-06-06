import logging
import os


class TestLogger(object):
    level_mapping = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARN,
        'error': logging.ERROR,
    }

    def __init__(self,
                 log_path,
                 logger_name='cloudify_tester',
                 log_format='%(asctime)s|%(levelname)s|%(message)s',
                 filehandler_level=logging.DEBUG,
                 console_level=logging.ERROR):
        self._logger = logging.getLogger(logger_name)
        self._logger.propagate = False
        # The logger will process all messages, we'll set the level to
        # actually log in the handlers.
        self._logger.setLevel(logging.DEBUG)

        # Set up formatter
        formatter = logging.Formatter(log_format)

        # Create file handler
        if log_path is not None:
            self._filehandler = logging.FileHandler(
                os.path.join(log_path, 'test_run.log'),
            )
            self._filehandler.setFormatter(formatter)
        else:
            self._filehandler = logging.NullHandler()
        self._filehandler_level = filehandler_level
        self._logger.addHandler(self._filehandler)
        self.file_logging_enable()

        # Create console handler if needed
        needs_console_handler = True
        for handler in self._logger.handlers:
            if not isinstance(handler, logging.FileHandler):
                needs_console_handler = False
                self._consolehandler = handler
                break
        if needs_console_handler:
            self._consolehandler = logging.StreamHandler()
            self._consolehandler_level = console_level
            self._consolehandler.setFormatter(formatter)
            self.console_logging_enable()
            self._logger.addHandler(self._consolehandler)

    def file_logging_enable(self):
        self._filehandler.setLevel(self._filehandler_level)

    def file_logging_disable(self):
        # Highest level normally is 50, so this will not even log critical
        # issues
        self._filehandler.setLevel(999)

    def file_logging_set_level(self, level):
        level = self.level_mapping[level]
        self._filehandler_level = level
        self._filehandler.setLevel(level)

    def console_logging_enable(self):
        self._consolehandler.setLevel(self._consolehandler_level)

    def console_logging_disable(self):
        # Highest level normally is 50, so this will not even log critical
        # issues
        self._consolehandler.setLevel(999)

    def console_logging_set_level(self, level):
        level = self.level_mapping[level]
        self._consolehandler_level = level
        self._consolehandler.setLevel(level)

    def debug(self, message):
        self._logger.debug(message)

    def info(self, message):
        self._logger.info(message)

    def warn(self, message):
        self._logger.warn(message)

    def error(self, message):
        self._logger.error(message)

    def exception(self, message):
        self._logger.exception(message)
