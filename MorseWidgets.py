#!/usr/bin/env python3
#
# Morse Control widget definitions
#
from datetime import datetime
from re import compile as reCompile

try:
    from PyQt5 import uic
    from PyQt5.QtCore import Qt, QMimeData, QObjectCleanupHandler, QTimer
    from PyQt5.QtGui import QFontMetrics, QTextCursor
    from PyQt5.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QScrollArea
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

class BitsGridLayout(QGridLayout):
    def __init__(self, parent):
        QGridLayout.__init__(self, parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

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
        super().__init__(parent, ''.join(self.BIT_CHARS[c] for c in bits) or ' ')
        self.setStyleSheet(self.STYLE_SHEET + ('; border-left: 1px solid' if first else '') + ('; border-right: 1px solid' if last else ''))
        font = self.font()
        font.setBold(True)
        font.setStretch(80)
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
        #or event.modifiers() & self.ALLOWED_MODIFIERS \
        if not text \
        or not event.modifiers() & self.ALLOWED_MODIFIERS \
            and (text in self.ALLOWED_CHARACTERS \
              or text.upper() in self.morse.encoding):
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
    def configure(cls, uiFile, parentWidget, sendCallback, printCallback):
        cls.uiFile = uiFile
        cls.parentWidget = parentWidget
        cls.parentLayout = parentWidget.layout()
        cls.sendCallback = sendCallback
        cls.printCallback = printCallback
        cls.isConnected = False
        cls.morse = Morse()
        MessageTextEdit.configure(cls.morse)

    @staticmethod
    def streamReader(stream): # generator
        for line in stream:
            line = line.strip()
            if not line.startswith('#'):
                yield line

    def __init__(self, arg = None):
        super().__init__(self.parentWidget)
        self.savedText = None
        if hasattr(arg, 'readline'):
            reader = self.streamReader(arg)
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
        elif arg:
            reader = None
            state = self.RECEIVED
            timeStamp = datetime.now()
            bits = arg
            text = None
        else:
            state = self.OUTGOING
            timeStamp = None
            text = ''
        if text is not None:
            text = text.replace('\\n', '\n')
        uic.loadUi(self.uiFile, self)
        self.textToUpdate = None
        self.textUpdateEventCounter = 0
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
        self.printButton.clicked.connect(self.printMessage)
        self.setState(state)
        self.setTimeStamp(timeStamp)
        self.messageTextEdit.callback = self.updateText
        self.messageTextEdit.setPlainText(text)
        if state is self.OUTGOING:
            index = self.HEAD_SIZE
        else:
            index = self.HEAD_SIZE + 1 if reader is None else self.parentLayout.count() - self.TAIL_SIZE
            self.bits = bits
            self.updateBits(self.morse.parseBits(bits), text is None)
        self.parentLayout.insertWidget(index, self)
        self.parentLayout.setStretch(index, 0)
        self.parentLayout.setStretch(self.parentLayout.count() - self.TAIL_SIZE, 1)
        if state is self.OUTGOING:
            self.messageTextEdit.setFocus()
            self.messageTextEdit.moveCursor(QTextCursor.End)

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
        self.bitsGridLayout.setColumnStretch(c, last)

    def updateBits(self, bits, saveText = False):
        for widget in self.bitsWidget.findChildren(QLabel):
            widget.setParent(None)
        QObjectCleanupHandler().add(self.bitsGridLayout) # pylint: disable=E0203
        self.bitsGridLayout = BitsGridLayout(self.bitsWidget)
        self.addToken(first = True)
        if saveText:
            text = []
        for (bits, code, char) in bits:
            self.addToken(bits, code, char)
            if saveText:
                text.append(char)
        self.addToken(last = True)
        self.bitsWidget.setLayout(self.bitsGridLayout)
        if saveText:
            self.messageTextEdit.setPlainText(''.join(text))

    def updateText(self, text):
        if self.state is self.OUTGOING:
            self.sendOutgoingButton.setDisabled(not text or not self.isConnected)
            self.resetOutgoingButton.setDisabled(not text)
            self.printButton.setDisabled(not text or not self.isConnected)
            self.textToUpdate = text
            self.textUpdateEventCounter += 1
            QTimer.singleShot(0, self.doUpdateText)
        else:
            self.printButton.setDisabled(not self.isConnected)
            if self.state is self.EDIT:
                self.saveReceivedButton.setDisabled(text == self.savedText)

    def doUpdateText(self):
        self.textUpdateEventCounter -= 1
        if self.textUpdateEventCounter == 0:
            bits = self.morse.parseMessage(self.SPACE_CUTTER.sub(' ', self.textToUpdate.strip().replace('\n', ' = ')))
            self.bits = ''.join(b[0] for b in bits)
            self.updateBits(bits)

    def dataStr(self):
        state = self.RECEIVED if self.state is self.EDIT else self.state
        text = '\\n'.join(self.messageTextEdit.toPlainText().splitlines())
        stateMark = self.STATE_MARKS[state]
        if state is self.OUTGOING:
            return ('\n%s\n%s\n' % (stateMark, text)) if text else ''
        else:
            return '\n%s\n%s\n%s\n' % (' '.join((stateMark, self.timeStamp.strftime(self.STORE_DATETIME_FORMAT))), text, self.bits)

    def textStr(self):
        stateText = self.stateTexts[self.state]
        text = self.messageTextEdit.toPlainText()
        if self.state is self.OUTGOING:
            return ('\n%s\n%s\n' % (stateText, text)) if text else ''
        else:
            return '\n%s\n%s\n' % (' '.join((stateText, self.timeStamp.strftime(self.DISPLAY_DATETIME_FORMAT))), text)

    @classmethod
    def setConnected(cls, isConnected):
        cls.isConnected = isConnected
        for widget in widgets(cls.parentLayout, cls.HEAD_SIZE, cls.TAIL_SIZE):
            widget.messageTextEdit.updateSize()

    @classmethod
    def writeData(cls, dataFile, textFile):
        dataFile.write('# MorseControl data file')
        textFile.write('# MorseControl text file')
        for widget in widgets(cls.parentLayout, cls.HEAD_SIZE, cls.TAIL_SIZE):
            dataFile.write(widget.dataStr())
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
        if cls.parentLayout.count() <= cls.HEAD_SIZE + cls.TAIL_SIZE or cls.parentLayout.itemAt(0).widget().state is not cls.OUTGOING:
            MessageFrame()

    def resetOutgoing(self):
        self.messageTextEdit.clear()
        self.messageTextEdit.setFocus()

    def sendOutgoing(self):
        self.sendCallback(self.morse.messageToBits(self.messageTextEdit.toPlainText(), True))
        self.setState(self.SENT)
        self.setTimeStamp(datetime.now())
        MessageFrame()

    def printMessage(self):
        self.printCallback(self.morse.messageToBits(self.messageTextEdit.toPlainText(), True))

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
