import os

from libs.config import *

class ConfigDefinition:
    class General:
        log_directory = PathField(default='logs')

    class Bin:
        tar = TextField(default='/usr/bin/tar')
        zstd = TextField(default='/usr/bin/zstd')
        unzip = TextField(default='/usr/bin/unzip')
        sevenz = TextField(default='/usr/bin/7z')
        gzip = TextField(default='/usr/bin/gzip')
  
CONFIG = Config(ConfigDefinition)
CONFIG.PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG.DEFAULT_CONFIG_PATH = ['~/.config/forensic/forensic.conf', os.path.join(CONFIG.PROJECT_DIR, 'forensic.conf'), '/etc/forensic/forensic.conf', '/opt/forensic/forensic.conf']

if __name__ == '__main__':
    CONFIG.print_template()

