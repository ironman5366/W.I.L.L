import logging
import os
import config
from termcolor import colored


log = logging.getLogger('WILL')


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


def _get_logging_config():
    # We'll eventually want better validating here
    return config.load_config("logging")


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
