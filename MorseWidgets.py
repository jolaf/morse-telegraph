#!/usr/bin/env python3
#
# Morse Control widget definitions
#
from datetime import datetime
from re import compile as reCompile

try:
    from PyQt5 import uic
    from PyQt5.QtCore import Qt, QMimeData
    from PyQt5.QtGui import QFontMetrics
    from PyQt5.QtWidgets import QFrame, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QScrollArea
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

class MessageTextEdit(QPlainTextEdit):
    ALLOWED_CHARACTERS = ' \n\r\x08\x7f' # Space, Enter, Backspace, Del
    ALLOWED_MODIFIERS = Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier | Qt.GroupSwitchModifier
    HEIGHT_ADJUSTMENT = 7 # Hate this hack!

    callback = None # Set by MessageFrame

    @classmethod
    def configure(cls, morse):
        cls.morse = morse

    def __init__(self, parent):
        QPlainTextEdit.__init__(self, parent)
        self.document().contentsChanged.connect(self.updateSize)

    def keyPressEvent(self, event):
        text = event.text()
        if not text \
        or event.modifiers() & self.ALLOWED_MODIFIERS \
        or text in self.ALLOWED_CHARACTERS \
        or text.upper() in self.morse.encoding:
            super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        if source:
            text = ''.join(c for c in source.text() if c in self.ALLOWED_CHARACTERS or c.upper() in self.morse.encoding)
            if text:
                source = QMimeData() # Doesn't work without it
                source.setText(text)
                super().insertFromMimeData(source)

    def updateSize(self):
        self.setFixedHeight((self.document().size().height() + 1) * QFontMetrics(self.font()).height() \
                + self.contentsMargins().top() + self.contentsMargins().bottom() + self.HEIGHT_ADJUSTMENT) # ToDo: Remove +1 for extra line
        if self.callback:
            self.callback(self.toPlainText()) # pylint: disable=E1102

class MessageFrame(QFrame):
    HEAD_SIZE = 0
    TAIL_SIZE = 1
    STORE_DATETIME_FORMAT = '%Y%m%d-%H%M%S'
    DISPLAY_DATETIME_FORMAT = '%A %d %B %Y, %H:%M:%S'
    OUTGOING = 0
    SENT = 1
    RECEIVED = 2
    EDIT = 3
    STATE_MARKS = '!><$'
    SPLITTER = reCompile(r'\s*\n\s*')
    SPACE_CUTTER = reCompile(r'\s+')
    stateTexts = []

    @classmethod
    def configure(cls, uiFile, parentWidget, sendCallback):
        cls.uiFile = uiFile
        cls.parentWidget = parentWidget
        cls.parentLayout = parentWidget.layout()
        cls.sendCallback = sendCallback
        cls.morse = Morse()
        MessageTextEdit.configure(cls.morse)

    @staticmethod
    def streamReader(stream): # generator
        for line in stream:
            line = line.strip()
            if not line.startswith('#'):
                yield line

    def __init__(self, stream = None):
        super().__init__(self.parentWidget)
        self.savedText = None
        if stream:
            reader = self.streamReader(stream)
            line = None
            while not line:
                line = next(reader)
            tokens = line.split()
            state = self.STATE_MARKS.index(tokens[0])
            if state is self.OUTGOING:
                assert len(tokens) == 1
                timeStamp = None
                text = next(reader)
            else:
                assert len(tokens) == 2
                timeStamp = datetime.strptime(tokens[1], self.STORE_DATETIME_FORMAT)
                text = next(reader)
                bits = next(reader)
        else:
            state = self.OUTGOING
            timeStamp = None
            text = ''
        text = text.replace('\\n', '\n')
        uic.loadUi(self.uiFile, self)
        if not self.stateTexts:
            self.stateTexts.extend(label.text() for label in (self.outgoingLabel, self.sentLabel, self.receivedLabel, self.receivedLabel))
        # self.textEdit.setPlaceholderText("Вводите текст сообщения здесь") # ToDo: Add in Designer after moving to Qt 5.3+
        self.resetOutgoingButton.clicked.connect(self.resetOutgoing)
        self.sendOutgoingButton.clicked.connect(self.sendOutgoing)
        self.deleteSentButton.clicked.connect(self.deleteSaved)
        self.deleteReceivedButton.clicked.connect(self.deleteSaved)
        self.editReceivedButton.clicked.connect(self.editReceived)
        self.cancelReceivedButton.clicked.connect(self.cancelEdit)
        self.saveReceivedButton.clicked.connect(self.saveEdit)
        self.setState(state)
        self.setTimeStamp(timeStamp)
        self.messageTextEdit.callback = self.updateText
        self.messageTextEdit.setPlainText(text)
        if state is self.OUTGOING:
            index = self.HEAD_SIZE
        else:
            index = self.parentLayout.count() - self.TAIL_SIZE
            self.updateBits(bits)
        self.parentLayout.insertWidget(index, self)
        self.parentLayout.setStretch(index, 0)
        self.parentLayout.setStretch(self.parentLayout.count() - self.TAIL_SIZE, 1)
        if not stream:
            self.messageTextEdit.setFocus()

    def setState(self, state):
        self.state = state
        self.stateStackedWidget.setCurrentIndex(state)
        self.controlStackedWidget.setCurrentIndex(state)
        self.messageTextEdit.setReadOnly(state in (self.SENT, self.RECEIVED))
        self.messageTextEdit.updateSize()

    def setTimeStamp(self, timeStamp):
        self.timeStamp = timeStamp
        self.timeLabel.setText(timeStamp.strftime(self.DISPLAY_DATETIME_FORMAT) if timeStamp else '')

    def addToken(self, bits = '', code = '', char = '', first = False, last = False):
        c = self.bitsGridLayout.columnCount()
        self.bitsGridLayout.addWidget(BitsLabel(self, bits, first, last), 0, c)
        self.bitsGridLayout.addWidget(CodeLabel(self, code), 1, c)
        self.bitsGridLayout.addWidget(CharLabel(self, char), 2, c)

    def updateBits(self, bits):
        self.bits = bits # ToDo?
        for widget in self.bitsWidget.findChildren(QLabel):
            widget.setParent(None)
        self.addToken(first = True)
        allBits = []
        for (bits, code, char) in self.morse.parseBits(bits):
            self.addToken(bits, code, char)
            allBits.append(bits)
        self.addToken(last = True)
        #self.bits = ''.join(allBits) # ToDo?

    def updateText(self, text):
        if self.state is self.OUTGOING:
            self.sendOutgoingButton.setDisabled(not text)
            self.resetOutgoingButton.setDisabled(not text)
            self.updateBits(self.morse.messageToBits(self.SPACE_CUTTER.sub(' ', text.strip().replace('\n', ' = '))))
        elif self.state is self.EDIT:
            self.saveReceivedButton.setDisabled(text == self.savedText)

    def dataStr(self):
        if self.state is self.EDIT:
            state = self.RECEIVED
            text = self.savedText
        else:
            state = self.state
            text = self.messageTextEdit.toPlainText()
        state = self.STATE_MARKS[state]
        if self.state is self.OUTGOING:
            return '%s\n%s\n' % (state, '\\n'.join(text.splitlines()))
        else:
            return '%s\n%s\n%s\n' % (' '.join((state, self.timeStamp.strftime(self.STORE_DATETIME_FORMAT))), '\\n'.join(text.splitlines()), self.bits)

    def textStr(self):
        state = self.stateTexts[self.state]
        if self.state is self.OUTGOING:
            return '%s\n%s\n' % (state, self.messageTextEdit.toPlainText())
        else:
            return '%s\n%s\n' % (' '.join((state, self.timeStamp.strftime(self.DISPLAY_DATETIME_FORMAT))), self.messageTextEdit.toPlainText())

    @classmethod
    def writeData(cls, dataFile, textFile):
        dataFile.write('# MorseControl data file')
        textFile.write('# MorseControl text file')
        for widget in widgets(cls.parentLayout, cls.HEAD_SIZE, cls.TAIL_SIZE):
            dataFile.write('\n')
            textFile.write(widget.textStr())
            if widget.state is not cls.OUTGOING:
                textFile.write('\n')
                dataFile.write(widget.dataStr())

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
        if cls.parentLayout.count() <= cls.HEAD_SIZE + cls.TAIL_SIZE or cls.parentLayout.itemAt(0).widget().state is not cls.OUTGOING:
            MessageFrame()

    def resetOutgoing(self):
        self.messageTextEdit.clear()
        self.messageTextEdit.setFocus()

    def sendOutgoing(self):
        self.sendCallback(self.bits)
        self.setState(self.SENT)
        self.setTimeStamp(datetime.now())
        MessageFrame()

    def deleteSaved(self):
        ret = QMessageBox.question(self, "Удалить телеграмму?", "Вы уверены, что хотите удалить данную телеграмму?")
        if ret == QMessageBox.Yes:
            self.setParent(None)

    def editReceived(self):
        self.savedText = self.messageTextEdit.toPlainText()
        self.setState(self.EDIT)
        self.messageTextEdit.setFocus()

    def cancelEdit(self):
        self.messageTextEdit.setPlainText(self.savedText)
        self.savedText = None
        self.setState(self.RECEIVED)

    def saveEdit(self):
        self.savedText = None
        self.setState(self.RECEIVED)
