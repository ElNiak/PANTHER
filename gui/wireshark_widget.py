from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QLabel, QSizePolicy, QScrollArea, QMessageBox, QMainWindow, QMenu, QAction, \
    qApp, QFileDialog
from gui.graph_visualizer import *
from PyQt5.QtGui import QImage, QPixmap, QPalette, QPainter
from subprocess import call

class embeddedTerminal(QtWidgets.QWidget):

    def __init__(self,pcap_file):
        QtWidgets.QWidget.__init__(self)
        self._processes = []
        self.resize(800, 600)
        self.terminal = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.terminal)
        self._stop_process()
        
        self._start_process('wireshark',[pcap_file])

    def _start_process(self, prog, args):
        child = QProcess()
        self._processes.append(child)
        child.start(prog, args)
    
    @classmethod
    def _stop_process(self):
        call(["pkill", "wireshark"])

