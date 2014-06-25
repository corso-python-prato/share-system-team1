from ui_rawbox import Ui_Dialog
from datetime import datetime
from PyQt4 import QtCore
from PyQt4 import QtGui
import json
import sys
import os

sys.path.insert(0, '../')
from client_cmdmanager import *


def get_dir_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def load_config():
    with open('../config.json', 'r') as config_file:
        config = json.load(config_file)
    return config

class Main(QtGui.QDialog, Ui_Dialog):
    def __init__(self, executer, config , parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.dir_path = config['dir_path']
        self.max_size = 2000000000 #bytes
        self.ui.lineEdit_5.setText(self.dir_path)
        self.ui.progressBar.setValue((get_dir_size(self.dir_path) / float(self.max_size)) * 100)
        self.ui.label_5.setText("of: " + str(self.max_size/1000000000) + " GB")
        self.executer = executer
        self.load_status(config['snapshot_file_path'])
    
    def __del__ (self):
        self.ui = None

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    conf = load_config()
    comm_sock = CmdMessageClient(conf['cmd_host'], int(conf['cmd_port']))
    executer = RawBoxExecuter(comm_sock)
    window = Main(executer, load_config())
    window.show()
    sys.exit(app.exec_())