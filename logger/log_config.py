import logging
import os
import sys
import config
from voluptuous import Schema, Required, Invalid, MultipleInvalid
from logger.fallback import error
from logger.handlers import ColorStreamHandler


LOG_FORMAT = logging.Formatter(
    '%(levelname)s - %(asctime)s: %(message)s'
)


class LogConfig(object):
    def __init__(self, config_source):
        self.__dict__.update(config_source)

    def logging_level(self):
        return logging.DEBUG if self.debug else logging.ERROR

    def log_file_path(self):
        return os.path.abspath(self.log_path)


def init_logger(log):
    log_config = get_logging_config()
    log.setLevel(log_config.logging_level())

    log.addHandler(
        build_console_handler(log_config)
    )
    log.addHandler(
        build_file_handler(log_config)
    )


def is_valid_logging_config(log_config):
    def valid_dir_path(path):
        folder_path = os.path.dirname(os.path.realpath(path))
        if not os.path.exists(folder_path):
            raise Invalid("log_path directory doesn't exist!")
    logging_schema = Schema({
        Required("debug"): bool,
        Required("log_path"): valid_dir_path,
        Required("append_log"): bool
    })
    try:
        logging_schema(log_config)
    except MultipleInvalid as e:
        error("Error parsing logging configuration.")
        error(e)
        return False
    return True


def get_logging_config():
    try:
        log_config = config.load_config("logging")
    except config.HeaderNotFound:
        error("Configuration does not have a \"logging\" header. See")
        error("example_config.json for details on setting up your config file.")  # noqa
        sys.exit(1)

    if not is_valid_logging_config(log_config):
        sys.exit(1)
    return LogConfig(log_config)


def build_console_handler(log_config):
    console_handler = ColorStreamHandler()
    console_handler.setLevel(log_config.logging_level())
    console_handler.setFormatter(LOG_FORMAT)
    return console_handler


def build_file_handler(log_config):
    file_handler = logging.FileHandler(
        log_config.log_file_path(),
        mode='a' if log_config.append_log else 'w'
    )
    file_handler.setLevel(log_config.logging_level())
    file_handler.setFormatter(LOG_FORMAT)

    return file_handler
