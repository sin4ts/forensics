import datetime
import logging
import sys
import os

__version__='1.0'

class CliFormatter(logging.Formatter):
    colors = {}
    colors['debug'] = '\033[90m[*] %(message)s\033[0m'
    colors['info']  ='[*] %(message)s'
    colors['warning'] = '\033[33m[!] %(message)s\033[0m'
    colors['error'] = '\033[31m[!] %(message)s\033[0m'
    colors['critical'] = '\033[1m\033[31m[X] %(message)s\033[0m'

    nocolors = {}
    nocolors['debug']     = 'DEBUG : %(message)s'
    nocolors['info']      = 'INFO  : %(message)s'
    nocolors['warning']   = 'WARN  : %(message)s'
    nocolors['error']     = 'ERROR : %(message)s'
    nocolors['critical']  = 'CRITIC: %(message)s'

    def __init__(self, fmt='%(levelno)s: %(message)s', color=True):
        logging.Formatter.__init__(self, fmt)
        self.colors=color
        self.formats = CliFormatter.colors
        if color == False:
            self.formats = CliFormatter.nocolors

    def format(self, record):
        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt
        # Replace the original format with one customized by logging level
        if record.levelno <= logging.DEBUG:
            self._style._fmt = self.formats['debug']
        elif record.levelno <= logging.INFO:
            self._style._fmt = self.formats['info']
        elif record.levelno <= logging.WARNING:
            self._style._fmt = self.formats['warning']
        elif record.levelno <= logging.ERROR:
            self._style._fmt = self.formats['error']
        elif record.levelno > logging.ERROR: #eg : CRITICAL
            self._style._fmt = self.formats['critical']

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)
        # Restore the original format configured by the user
        self._style._fmt = format_orig
        return result

class FileFormatter(logging.Formatter):
    colors = {}
    colors['debug'] = '\033[90m[*] %(message)s\033[0m'
    colors['info']  ='[*] %(message)s'
    colors['warning'] = '\033[33m[!] %(message)s\033[0m'
    colors['error'] = '\033[31m[!] %(message)s\033[0m'
    colors['critical'] = '\033[1m\033[31m[X] %(message)s\033[0m'

    nocolors = {}
    nocolors['debug']     = 'DEBUG : %(asctime)s %(message)s'
    nocolors['info']      = 'INFO  : %(asctime)s %(message)s'
    nocolors['warning']   = 'WARN  : %(asctime)s %(message)s'
    nocolors['error']     = 'ERROR : %(asctime)s %(message)s'
    nocolors['critical']  = 'CRITIC: %(asctime)s %(message)s'

    def __init__(self, fmt='%(levelno)s: %(message)s', color=True):
        logging.Formatter.__init__(self, fmt)
        self.colors=color
        self.formats = FileFormatter.colors
        if color == False:
            self.formats = FileFormatter.nocolors

    def format(self, record):
        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt
        # Replace the original format with one customized by logging level
        if record.levelno <= logging.DEBUG:
            self._style._fmt = self.formats['debug']
        elif record.levelno <= logging.INFO:
            self._style._fmt = self.formats['info']
        elif record.levelno <= logging.WARNING:
            self._style._fmt = self.formats['warning']
        elif record.levelno <= logging.ERROR:
            self._style._fmt = self.formats['error']
        elif record.levelno > logging.ERROR: #eg : CRITICAL
            self._style._fmt = self.formats['critical']

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)
        # Restore the original format configured by the user
        self._style._fmt = format_orig
        return result


def init_logging(log_dir, level=logging.INFO, color=True):
    if os.name == 'nt':
        color = False
    cli_fmt = CliFormatter(color=color)
    file_fmt = FileFormatter(color=False)
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    cli_handler = logging.StreamHandler(sys.stdout)
    cli_handler.setFormatter(cli_fmt)
    cli_handler.setLevel(level)

    log_path = os.path.join(log_dir, '{}.log'.format(datetime.datetime.now().strftime('%Y%m%d')))
    file_handler = logging.FileHandler(log_path , 'a')
    file_handler.setFormatter(file_fmt)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(cli_handler)
    root_logger.setLevel(logging.DEBUG)

    # muting peewee if used
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.ERROR)

    logging.debug('Custom logging handler added')
