from cloudify_tester.config import (
    Config,
    default_schemas,
    SchemaError,
)
from cloudify_tester.helpers.logger import TestLogger

import sys


_logger = None


def get_logger():
    # TODO: docstring
    global _logger
    if _logger is not None:
        logger = _logger
    else:
        logger = TestLogger(
            log_path=None,
            logger_name='config',
            log_format='%(message)s'
        )
        logger.console_logging_set_level('debug')

        # Avoid duplicating handlers
        _logger = logger
    return logger


def load_config(config_file=None, missing_config_fail=True):
    # TODO: docstring
    logger = get_logger()
    config = None
    try:
        if config_file:
            config_files = [config_file]
        else:
            config_files = []
        config = Config(
            config_files=config_files,
            config_schema_files=default_schemas,
            logger=logger,
        )
    except SchemaError as e:
        print(e.message)
        sys.exit(1)
    except IOError:
        message = 'Could not find {config}'.format(
            config=config_file,
        )
        if missing_config_fail:
            logger.error(message)
            sys.exit(2)
        else:
            logger.warn(message)
    return config
