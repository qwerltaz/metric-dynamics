import logging
import logging.config


def get_logger() -> logging.Logger:
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "[%(levelname)s] %(message)s"
            },
            "verbose": {
                "format": "[%(levelname)s] %(asctime)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "verbose",
                "filename": ".log",
                "mode": "w",
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "local_logger": {
                "level": "DEBUG",
                "handlers": ["stdout", "file"]
            }
        }
    }

    logger = logging.getLogger("local_logger")
    logging.config.dictConfig(logging_config)

    return logger
