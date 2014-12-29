#!/usr/bin/env python3
#
# Morse Control widget definitions
#
from datetime import datetime

try:
    from PyQt5 import uic
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QTextDocument
    from PyQt5.QtWidgets import QFrame, QLineEdit, QPushButton, QScrollArea
except ImportError as ex:
    raise ImportError("%s: %s\n\nPlease install PyQt5 v5.2.1 or later: http://riverbankcomputing.com/software/pyqt/download5\n" % (ex.__class__.__name__, ex))

def fixWidgetSize(widget, adjustment = 1):
    widget.setFixedWidth(widget.fontMetrics().boundingRect(widget.text()).width() * adjustment) # This is a bad hack, but there's no better idea

def setTip(widget, tip):
    widget.setToolTip(tip)
    widget.setStatusTip(tip)

def widgets(layout, headerSize = 0, tailSize = 0): # generator
    for i in range(headerSize, layout.count() - tailSize):
        yield layout.itemAt(i).widget()

class ConsoleControlButton(QPushButton):
    def configure(self, consoleOpen = False, *args):
        self.consoleOpen = not consoleOpen
        self.args = args
        fixWidgetSize(self, 3)
        self.clicked.connect(self.processClick)
        self.processClick()

    def processClick(self, _checked = False):
        self.consoleOpen = not self.consoleOpen
        self.setText('>' if self.consoleOpen else '<')
        setTip(self, ("Закрыть" if self.consoleOpen else "Открыть") + " консоль управления")
        for arg in self.args:
            arg.setVisible(self.consoleOpen)

class ConsoleEdit(QLineEdit):
    def configure(self, callback):
        self.setStatusTip(self.placeholderText())
        self.returnPressed.connect(callback)

    def getInput(self):
        ret = self.text()
        self.clear()
        return ret

class VerticalScrollArea(QScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollBarSet = False

    def resizeEvent(self, event):
        if not self.scrollBarSet:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scrollBarSet = True
        self.setMinimumWidth(self.widget().sizeHint().width() + self.verticalScrollBar().width())
        QScrollArea.resizeEvent(self, event)

class MessageFrame(QFrame):
    STORE_DATETIME_FORMAT = '%Y%m%d-%H%M%S'
    DISPLAY_TIME_FORMAT = '%d %b %Y, %H:%M:%S'
    DIRECTIONS = ("Входящее", "Исходящее")

    @classmethod
    def configure(cls, uiFile, parentWidget):
        cls.uiFile = uiFile
        cls.parentWidget = parentWidget
        cls.parentLayout = parentWidget.layout()

    @staticmethod
    def streamReader(stream): # generator
        for line in stream:
            line = line.strip()
            if line and not line.startswith('#'):
                yield line

    def __init__(self, stream = None):
        super().__init__(self.parentWidget)
        if stream:
            reader = self.streamReader(stream)
            (typ, timeStamp, bits) = reader.readline().split()
            self.isOutgoing = (typ == b'>')
            self.timeStamp = datetime.strptime(timeStamp, self.STORE_DATETIME_FORMAT)
            self.bits = bits
            self.text = reader.readline()
        else:
            self.isOutgoing = True
            self.timeStamp = None
            self.bits = b''
            self.text = ''
        uic.loadUi(self.uiFile, self)
        # self.textEdit.setPlaceholderText("Вводите текст сообщения для отправки здесь") # ToDo: Add in Designer after moving to Qt 5.3+
        self.directionStackedWidget.setCurrentIndex(self.isOutgoing)
        self.controlStackedWidget.setCurrentIndex(self.isOutgoing if stream else self.controlStackedWidget.indexOf(self.editOutgoingControlPage))
        if self.text:
            self.textEdit.setDocument(QTextDocument(self.text))
        self.setTime()
        if not stream:
            self.textEdit.setFocus()

    def setTime(self):
        self.timeLabel.setText(self.timeStamp.strftime(self.DISPLAY_TIME_FORMAT) if self.timeStamp else '')

    def dataStr(self):
        return '%s\n%s\n' % (b' '.join(('>' if self.outgoing else '<', self.timeStamp.strftime(self.STORE_DATETIME_FORMAT), self.bits)), self.text)

    def textStr(self):
        return '%s\n%s\n' % (b' '.join(('>' if self.outgoing else '<', self.timeStamp.strftime(self.STORE_DATETIME_FORMAT))), self.text)

    @classmethod
    def writeData(cls, dataFile, textFile):
        for widget in widgets(cls.parentLayout, 0, 1):
            dataFile.write(widget.dataStr())
            textFile.write(widget.textStr())

    @classmethod
    def readData(cls, dataFile):
        for widget in widgets(cls.parentLayout, 0, 1):
            widget.setParent(None)
        MessageFrame()
        if dataFile:
            try:
                while True:
                    MessageFrame(dataFile)
            except StopIteration:
                pass
