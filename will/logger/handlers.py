import logging
from termcolor import colored


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
