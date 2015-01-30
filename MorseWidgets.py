#!/usr/bin/env python3
#
# Morse Control widget definitions
#
from datetime import datetime
from re import compile as reCompile

try:
    from PyQt5 import uic
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QScrollArea
except ImportError as ex:
    raise ImportError("%s: %s\n\nPlease install PyQt5 v5.2.1 or later: http://riverbankcomputing.com/software/pyqt/download5\n" % (ex.__class__.__name__, ex))

from Morse import Morse

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

class MorseLabel(QLabel):
    def __init__(self, parent, text = ''):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignHCenter)

class BitsLabel(MorseLabel):
    BIT_CHARS = {'0': ' ', '1': '-'}
    STYLE_SHEET = '''
        background-color: white;
        border-top: 1px solid;
        border-bottom: 1px solid;
        font-weight: bold;
        font-family: Courier New, Courier, monospace
    '''
    def __init__(self, parent, bits = '', first = False, last = False):
        super().__init__(parent, ''.join(self.BIT_CHARS[c] for c in bits))
        self.setStyleSheet(self.STYLE_SHEET + ('; border-left: 1px solid' if first else '') + ('; border-right: 1px solid' if last else ''))
        font = self.font()
        font.setBold(True)
        font.setStretch(30)
        font.setLetterSpacing(font.PercentageSpacing, 50)
        self.setFont(font)

class CodeLabel(MorseLabel):
    CODE_CHARS = {'.': '·', '-': '−'}
    def __init__(self, parent, code = ''):
        super().__init__(parent, ' '.join(self.CODE_CHARS.get(c, '') for c in code))
        self.setStyleSheet('font-weight: bold')

class CharLabel(MorseLabel):
    pass

class MessageTextLabel(QLabel):
    callback = None # Set by MessageFrame

    def keyPressEvent(self, event):
        QLabel.keyPressEvent(self, event)
        self.updateMessage()

    def mousePressEvent(self, event):
        QLabel.mousePressEvent(self, event)
        if event.button() == Qt.MiddleButton:
            self.updateMessage()

    def updateMessage(self):
        if self.callback:
            self.callback(self.text()) # pylint: disable=E1102
        self.updateGeometry()

class MessageFrame(QFrame):
    HEAD_SIZE = 0
    TAIL_SIZE = 1
    STORE_DATETIME_FORMAT = '%Y%m%d-%H%M%S'
    DISPLAY_DATETIME_FORMAT = '%A %d %B %Y, %H:%M:%S'
    OUTGOING = 0
    SENT = 1
    RECEIVED = 2
    CORRECT = 3
    STATE_MARKS = '!><$'
    SPLITTER = reCompile(r'\s*\n\s*')
    stateTexts = []

    @classmethod
    def configure(cls, uiFile, parentWidget, sendCallback):
        cls.uiFile = uiFile
        cls.parentWidget = parentWidget
        cls.parentLayout = parentWidget.layout()
        cls.sendCallback = sendCallback
        cls.morse = Morse()

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
            tokens = next(reader).split()
            state = self.STATE_MARKS.index(tokens[0])
            if state == self.OUTGOING:
                assert len(tokens) == 1
                self.timeStamp = None
                text = next(reader).replace('\\n', '\n')
                self.bits = self.morse.messageToBits(self.SPLITTER.sub(' = ', text))
            else:
                assert len(tokens) == 2
                self.timeStamp = datetime.strptime(tokens[1], self.STORE_DATETIME_FORMAT)
                self.bits = next(reader)
                text = next(reader)
        else:
            state = self.OUTGOING
            self.timeStamp = None
            self.bits = b''
            text = ''
        uic.loadUi(self.uiFile, self)
        if not self.stateTexts:
            self.stateTexts.extend(label.text() for label in (self.outgoingLabel, self.sentLabel, self.receivedLabel, self.receivedLabel))
            self.textInteractionFlags = self.textEditLabel.textInteractionFlags()
        # self.textEdit.setPlaceholderText("Вводите текст сообщения для отправки здесь") # ToDo: Add in Designer after moving to QPlainTextEdit and Qt 5.3+
        self.setTime()
        self.textEditLabel.setText(text)
        self.setBits()
        self.resetOutgoingButton.clicked.connect(self.resetOutgoing)
        self.sendOutgoingButton.clicked.connect(self.sendOutgoing)
        self.textEditLabel.callback = self.textUpdatedCallback
        self.setState(state)
        self.parentLayout.insertWidget(self.parentLayout.count() - self.TAIL_SIZE, self)
        self.parentLayout.setStretch(self.parentLayout.count() - self.TAIL_SIZE - 1, 0)
        self.parentLayout.setStretch(self.parentLayout.count() - self.TAIL_SIZE, 1)
        if not stream:
            self.textEditLabel.setFocus()

    def setState(self, state):
        self.state = state
        self.stateStackedWidget.setCurrentIndex(state)
        self.controlStackedWidget.setCurrentIndex(state)
        self.textEditLabel.updateMessage()

    def setTime(self):
        self.timeLabel.setText('в ' + self.timeStamp.strftime(self.DISPLAY_DATETIME_FORMAT) if self.timeStamp else '')

    def addToken(self, bits = '', code = '', char = '', first = False, last = False):
        c = self.bitsGridLayout.columnCount()
        self.bitsGridLayout.addWidget(BitsLabel(self, bits, first, last), 0, c)
        self.bitsGridLayout.addWidget(CodeLabel(self, code), 1, c)
        self.bitsGridLayout.addWidget(CharLabel(self, char), 2, c)

    def setBits(self):
        for widget in self.bitsWidget.findChildren(QLabel):
            widget.setParent(None)
        self.addToken(first = True)
        allBits = []
        for (bits, code, char) in self.morse.parseBits(self.bits):
            self.addToken(bits, code, char)
            allBits.append(bits)
        self.addToken(last = True)
        self.bits = ''.join(allBits)

    def dataStr(self):
        state = self.STATE_MARKS[self.state]
        if self.state is self.OUTGOING:
            return '%s\n%s\n' % (state, '\\n'.join(self.textEditLabel.text().splitlines()))
        else:
            return '%s\n%s\n%s\n' % (' '.join((state, self.timeStamp.strftime(self.STORE_DATETIME_FORMAT))), '\\n'.join(self.textEditLabel.text().splitlines()), self.bits)

    def textStr(self):
        state = self.stateTexts[self.state]
        if self.state is self.OUTGOING:
            return '%s\n%s\n' % (state, self.textEditLabel.text())
        else:
            return '%s\n%s\n' % (' '.join((state, self.timeStamp.strftime(self.DISPLAY_DATETIME_FORMAT))), self.textEditLabel.text())

    @classmethod
    def writeData(cls, dataFile, textFile):
        dataFile.write('# MorseControl data file')
        textFile.write('# MorseControl text file')
        for widget in widgets(cls.parentLayout, cls.HEAD_SIZE, cls.TAIL_SIZE):
            dataFile.write('\n')
            dataFile.write(widget.dataStr())
            textFile.write('\n')
            textFile.write(widget.textStr())

    @classmethod
    def readData(cls, dataFile):
        for widget in widgets(cls.parentLayout, cls.HEAD_SIZE, cls.TAIL_SIZE):
            widget.setParent(None)
        if dataFile:
            try:
                while True:
                    MessageFrame(dataFile)
            except StopIteration:
                pass
        if cls.parentLayout.count() <= cls.HEAD_SIZE + cls.TAIL_SIZE:
            MessageFrame()

    def textUpdatedCallback(self, text):
        if self.state == self.OUTGOING:
            text = self.textEditLabel.text()
            self.sendOutgoingButton.setDisabled(not text)
            self.resetOutgoingButton.setDisabled(not text)

    def resetOutgoing(self):
        self.textEditLabel.clear()
        self.textEditLabel.setFocus()

    def sendOutgoing(self):
        self.sendCallback(self.bits)
        self.textEditLabel.setTextInteractionFlags(self.textInteractionFlags ^ Qt.TextEditable)
        self.timeStamp = datetime.now()
        self.setState(self.SENT)
        self.setTime()
        MessageFrame()
