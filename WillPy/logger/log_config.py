import logging
import os
import sys
import WillPy.config as config
from voluptuous import Schema, Required, Invalid, MultipleInvalid
from WillPy.logger.fallback import error
from WillPy.logger.handlers import ColorStreamHandler


class LogConfig(object):
    def __init__(self, config_source):
        self.__dict__.update(config_source)

    def logging_level(self):
        return logging.DEBUG if self.debug else logging.ERROR


class ConfigurationBuilder(object):
    def __init__(self):
        try:
            self.log_config = config.load_config("logging")
        except config.HeaderNotFound:
            error("Configuration does not have a \"logging\" header. See")
            error("example_config.json for details on setting up your config file.")  # noqa
            sys.exit(1)

        if not self.is_valid_config():
            sys.exit(1)

    def is_valid_config(self):
        LOGGING_SCHEMA = Schema({
            Required("debug"): bool,
            Required("log_path"): self.is_valid_dir_path,
            Required("append_log"): bool
        })

        try:
            LOGGING_SCHEMA(self.log_config)
        except MultipleInvalid as e:
            error("Error parsing logging configuration.")
            error(e)
            return False
        return True

    def build(self):
        return LogConfig(self.log_config)

    @staticmethod
    def is_valid_dir_path(path):
        folder_path = os.path.dirname(os.path.realpath(path))
        if not os.path.exists(folder_path):
            raise Invalid("log_path directory doesn't exist!")


class LogBuilder(object):
    LOG_FORMAT = logging.Formatter(
        '%(levelname)s - %(asctime)s: %(message)s'
    )

    def __init__(self, configuration, logger):
        self.configuration = configuration
        self.log = logger

    def build(self):
        self.log.setLevel(self.configuration.logging_level())
        self.log.addHandler(self._build_console_handler())
        self.log.addHandler(self._build_file_handler())

    def _build_console_handler(self):
        console_handler = ColorStreamHandler()
        console_handler.setLevel(self.configuration.logging_level())
        console_handler.setFormatter(self.LOG_FORMAT)
        return console_handler

    def _build_file_handler(self):
        file_path = os.path.abspath(self.configuration.log_path)
        file_handler = logging.FileHandler(
            file_path,
            mode='a' if self.configuration.append_log else 'w'
        )
        file_handler.setLevel(self.configuration.logging_level())
        file_handler.setFormatter(self.LOG_FORMAT)
        return file_handler


def init_logger(log):
    log_config = ConfigurationBuilder().build()
    log_builder = LogBuilder(log_config, log)
    log_builder.build()
