#!/usr/bin/env python3
#
# Morse Control widget definitions
#
try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLineEdit, QPushButton, QScrollArea, QWidget
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
        QScrollArea.__init__(self, parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollBarSet = False

    def resizeEvent(self, event):
        if not self.scrollBarSet:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scrollBarSet = True
        self.setMinimumWidth(self.widget().sizeHint().width() + self.verticalScrollBar().width())
        QScrollArea.resizeEvent(self, event)

class MessageWidget(QWidget):
    pass

class IncomingMessageWidget(MessageWidget):
    pass

class OutgoingMessageWidget(MessageWidget):
    pass
