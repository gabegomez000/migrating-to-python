import logging
import logging.config


def setup_logging(log_file=None):
    """Configure logging with a console handler and an optional file handler.

    Args:
        log_file: Path to a log file. If None, only console output is configured.

    Returns:
        A Logger named 'Console'.
    """
    handlers = {
        'Console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'stream': 'ext://sys.stderr',
            'formatter': 'simple',
        },
    }
    handler_names = ['Console']

    if log_file:
        handlers['file'] = {
            'class': 'logging.FileHandler',
            'filename': log_file,
            'level': 'DEBUG',
            'formatter': 'simple',
        }
        handler_names.append('file')

    logging_config = {
        'version': 1,
        'handlers': handlers,
        'formatters': {
            'simple': {
                'format': '[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S %z',
            },
        },
        'root': {
            'level': 'DEBUG',
            'handlers': handler_names,
        },
    }

    logging.config.dictConfig(logging_config)
    return logging.getLogger('Console')
