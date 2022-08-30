from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QLabel, QSizePolicy, QScrollArea, QMessageBox, QMainWindow, QMenu, QAction, \
    qApp, QFileDialog
from gui.graph_visualizer import *
from PyQt5.QtGui import QImage, QPixmap, QPalette, QPainter
from subprocess import call


# /usr/bin/python3 /home/user/Documents/QUIC-RFC9000/run_experiments.py --mode client --categories global_test --update_include_tls  --timeout 90   --implementations picoquic --iter 1 --compile  --initial_version 29 --alpn hq-29
class embeddedTerminal(QtWidgets.QWidget):

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self._processes = []
        self.resize(800, 600)
        self.terminal = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.terminal)
        self._stop_process()
        self._start_process(
            'xterm',
            ['-into', str(self.terminal.winId()),
             '-e', 'tmux', 'new', '-s', 'my_session']
        )
        button = QtWidgets.QPushButton('List files')
        layout.addWidget(button)
        button.clicked.connect(self._list_files)

    def _start_process(self, prog, args):
        child = QProcess()
        self._processes.append(child)
        child.start(prog, args)

    def _list_files(self):
        self._start_process(
            'tmux', ['send-keys', '-t', 'my_session:0', 'ls', 'Enter'])

    @classmethod
    def _stop_process(self):
        call(["tmux", "kill-session", "-t", "my_session"])