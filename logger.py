import logging
import os
import sys
import config
from voluptuous import Schema, Required, Invalid, MultipleInvalid
from termcolor import colored


log = logging.getLogger('WILL')


def fallback_error(error_msg):
    sys.stderr.write(
        colored("CRITICAL: {0}\n".format(error_msg), 'red')
    )


class ColorStreamHandler(logging.StreamHandler):
    COLORS = {
        "DEBUG": 'green',
        "INFO": 'white',
        "WARNING": 'yellow',
        "ERROR": 'red',
        "CRITICAL": 'red'
    }

    def emit(self, record):
        try:
            self.stream.write(self._build_log_text(record))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def _build_log_text(self, record):
        return "{0}\n".format(
            self._color_text_by_threat_level(
                self.format(record),
                record.levelname
            )
        )

    def _color_text_by_threat_level(self, text, threat_level):
        return colored(text, self.COLORS[threat_level])


def _setup_logger():
    logging_formatter = logging.Formatter(
        '%(levelname)s - %(asctime)s: %(message)s'
    )

    log.setLevel(_get_logging_level())

    log.addHandler(
        _build_console_handler(logging_formatter)
    )
    log.addHandler(
        _build_file_handler(logging_formatter)
    )


def _valid_logging_config(log_config):
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
        fallback_error("Error parsing logging configuration.")
        fallback_error(e)
        return False
    return True


def _get_logging_config():
    try:
        log_config = config.load_config("logging")
    except config.HeaderNotFound:
        fallback_error("Configuration does not have a \"logging\" header. See")
        fallback_error("example_config.json for details on setting up your config file.")  # noqa
        sys.exit(1)

    if not _valid_logging_config(log_config):
        sys.exit(1)
    return log_config


def _get_logging_level():
    will_config = _get_logging_config()
    return logging.DEBUG if will_config["debug"] else logging.ERROR


def _build_console_handler(formatter):
    c_handler = ColorStreamHandler()
    c_handler.setLevel(_get_logging_level())
    c_handler.setFormatter(formatter)
    return c_handler


def _build_file_handler(formatter):
    will_config = _get_logging_config()
    file_path = os.path.abspath(will_config["log_path"])
    append_config = will_config["append_log"]

    f_handler = logging.FileHandler(
        file_path,
        mode='a' if append_config else 'w'
    )
    f_handler.setLevel(_get_logging_level())
    f_handler.setFormatter(formatter)

    return f_handler


_setup_logger()
