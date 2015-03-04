#!/usr/bin/env python3
#
# Morse Control GUI main module
#
from collections import deque
from functools import partial
from getopt import getopt
from locale import setlocale, LC_ALL
from logging import getLogger, getLoggerClass, setLoggerClass, FileHandler, Formatter, Handler, INFO, NOTSET
from sys import argv, exit # pylint: disable=W0622
from time import sleep, time
from traceback import format_exc

try:
    from PyQt5 import uic
    from PyQt5.QtCore import QByteArray, QCoreApplication, QDateTime, QObject, QSettings, QTranslator, pyqtSignal
    from PyQt5.QtWidgets import QApplication, QDesktopWidget, QDialog, QLabel, QMessageBox, QMainWindow
except ImportError as ex:
    raise ImportError("%s: %s\n\nPlease install PyQt5 v5.2.1 or later: http://riverbankcomputing.com/software/pyqt/download5\n" % (ex.__class__.__name__, ex))

from UARTTextProtocol import Command, COMMAND_MARKER
from UARTTextCommands import ackResponse, morseBeepCommand, morseTxCommand, morsePrintCommand, morseRxResponse
from SerialPort import SerialPort, DT, TIMEOUT
from MorseWidgets import MessageFrame

#
# ToDo
# Fix segmentation faults - do not hold references to Qt objects
# When decoding incoming message, add indication of СОЕД, НЧЛ, КНЦ, НПР, ОШК
# Adequately decode incoming message UART commands
# Verify operation on Windows
#

LONG_DATETIME_FORMAT = 'yyyy.MM.dd hh:mm:ss'

MAIN_UI_FILE_NAME = 'MorseControl.ui'
MESSAGE_UI_FILE_NAME = 'MorseMessage.ui'

ABOUT_UI_FILE_NAME = 'AboutMC.ui'

DATA_FILE_NAME = 'MorseControl.msg'
TEXT_FILE_NAME = 'MorseControl.txt'

LOG_FILE_NAME = 'MorseControl.log'

WINDOW_SIZE = 2.0 / 3
WINDOW_POSITION = (1 - WINDOW_SIZE) / 2

class CallableHandler(Handler):
    def __init__(self, emitCallable, level = NOTSET):
        super().__init__(level)
        self.emitCallable = emitCallable

    def emit(self, record):
        self.emitCallable(self.format(record))

class EventLogger(getLoggerClass(), QObject):
    logSignal = pyqtSignal(tuple, dict)

    def configure(self, parent = None):
        QObject.__init__(self, parent)
        self.logSignal.connect(self.doLog)

    def doLog(self, args, kwargs): # pylint: disable=R0201
        super()._log(*args, **kwargs)

    def _log(self, *args, **kwargs):
        self.logSignal.emit(args, kwargs)

class EmulatedSerial(object):
    def __init__(self):
        self.name = 'EMUL'
        self.interval = 20 # emulate receiving message every 20 seconds
        self.timeout = TIMEOUT
        self.buffer = deque()
        self.ready = False
        self.nextMessage = time() + self.interval

    def readline(self):
        while True:
            if self.buffer:
                return self.buffer.popleft()
            now = time()
            if self.ready and (self.nextMessage is None or now > self.nextMessage):
                self.nextMessage = now + self.interval
                return morseRxResponse.encode('1010101010101010101010101010000000111010111010111000000010111011101000111011101110001011101010001010111000111011101110100010001110100011101000101110001011101011100000001110001000101110101000100011101110100010111010001011100011101110001110111000101110001011101011101011100000001110001011101000101011100010111010100010111010111000101110101000101110101110000000000000001110001011101000101110001011101010001011101011100010111010100010111010111000111011101010111011100000001010111010111')
            sleep(DT)

    def write(self, data):
        ret = ''
        try:
            (tag, _args) = Command.decodeCommand(data)
            if tag:
                ret = ackResponse.encode(0)
            else:
                raise ValueError("Неизвестная команда")
        except ValueError as e:
            ret = str(e)
        self.buffer.append(ret)
        self.ready = True
        return len(data)

    def close(self):
        pass

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(ABOUT_UI_FILE_NAME, self)

class PortLabel(QLabel):
    STATUS_COLORS = {
        SerialPort.TRYING: 'black',
        SerialPort.CONNECTED: 'brown',
        SerialPort.VERIFIED: 'green',
        SerialPort.ERROR: 'red'
    }

    setPortStatus = pyqtSignal(str, int)

    def configure(self):
        self.savedStyleSheet = str(self.styleSheet())
        self.setPortStatus.connect(self.setValue)

    def setValue(self, portName, portStatus):
        self.setText(portName)
        self.setStyleSheet(self.savedStyleSheet + '; color: %s' % self.STATUS_COLORS.get(portStatus, 'gray'))

class MorseControl(QMainWindow):
    comConnect = pyqtSignal(str)
    comDisconnect = pyqtSignal()
    comInput = pyqtSignal(str)

    def __init__(self, args):
        super().__init__()
        uic.loadUi(MAIN_UI_FILE_NAME, self)
        # Processing command line options
        self.advanced = False
        self.emulated = False
        self.needLoadSettings = True
        (options, _parameters) = getopt(args, 'aer', ('advanced', 'emulated', 'reset'))
        for (option, _value) in options:
            if option in ('-a', '--advanced'):
                self.advanced = True
            elif option in ('-e', '--emulated'):
                self.emulated = True
            elif option in ('-r', '--reset'):
                self.needLoadSettings = False
        # Setting variables
        self.port = None
        # Setting window size
        resolution = QDesktopWidget().screenGeometry()
        width = resolution.width()
        height = resolution.height()
        self.setGeometry(width * WINDOW_POSITION, height * WINDOW_POSITION, width * WINDOW_SIZE, height * WINDOW_SIZE)
        # Configuring widgets
        self.setCentralWidget(self.splitter)
        self.rightWidget.setVisible(self.advanced)
        self.portLabel.configure()
        self.resetButton.clicked.connect(self.reset)
        self.consoleEdit.configure(self.consoleEnter)
        self.aboutDialog = AboutDialog()
        self.aboutAction.triggered.connect(self.aboutDialog.exec_)
        self.aboutQtAction.triggered.connect(partial(QMessageBox.aboutQt, self, "About Qt"))
        # Setup logging
        formatter = Formatter('%(asctime)s %(levelname)s\t%(message)s', '%Y-%m-%d %H:%M:%S')
        handlers = (FileHandler(LOG_FILE_NAME), CallableHandler(self.logTextEdit.appendPlainText))
        rootLogger = getLogger('')
        for handler in handlers:
            handler.setFormatter(formatter)
            rootLogger.addHandler(handler)
        rootLogger.setLevel(INFO)
        setLoggerClass(EventLogger)
        self.logger = getLogger('MorseControl')
        self.logger.configure(self) # pylint: disable=E1103
        self.logger.info("старт")
        # Loading messages
        MessageFrame.configure(MESSAGE_UI_FILE_NAME, self.messageHistoryWidget, self.sendMessage, self.printMessage)
        # Starting up!
        self.loadSettings()
        self.loadData()
        self.comConnect.connect(self.processConnect)
        self.comDisconnect.connect(self.processDisconnect)
        self.comInput.connect(self.processInput)
        self.port = SerialPort(self.logger, morseBeepCommand.prefix, ackResponse.prefix,
                               self.comConnect.emit, self.comDisconnect.emit, self.comInput.emit, self.portLabel.setPortStatus.emit,
                               EmulatedSerial() if self.emulated else None, (230400,))
        if self.savedMaximized:
            self.showMaximized()
        else:
            self.show()

    def askForExit(self):
        if True: # ToDo: Make a proper check for unsent message
            return True
        messageBox = QMessageBox(QMessageBox.Question, "Редактируемая телеграмма не была отправлена.",
                "Вы уверены, что хотите выйти?", QMessageBox.Yes | QMessageBox.No, self)
        return messageBox.exec_() == QMessageBox.Yes

    def processConnect(self, pong):
        (code,) = ackResponse.decode(pong) # pylint: disable=W0633
        if code:
            self.logger.warning("Ошибка подключения устройства: %d", code)
        else:
            self.logger.info("Обнаружено подключенное устройство")
            MessageFrame.setConnected(True)

    def processDisconnect(self):
        self.logger.warning("Устройство отключено")
        MessageFrame.setConnected(False)

    def processCommand(self, command, expect = COMMAND_MARKER):
        if not self.port:
            return
        data = self.port.command(command, expect, QApplication.processEvents)
        if data:
            data = str(data).strip()
            (tag, args) = Command.decodeCommand(data)
            if tag:
                self.logger.info("OK")
                return args
            else:
                self.logger.warning("Неожиданные данные: %s", data)
        else:
            self.logger.warning("истекло время ожидания выполнения команды")

    def processInput(self, data):
        data = data.strip()
        (tag, args) = Command.decodeCommand(data)
        if tag == morseRxResponse.tag:
            MessageFrame(args[0])
        elif args is not None: # unexpected valid command
            self.logger.warning("Неожиданная команда: %s %s", tag, ' '.join(str(arg) for arg in args))
        elif tag: # unknown command
            self.logger.warning("Неизвестная команда %s: %s", tag, data)
        else: # not a command
            self.logger.warning("Неожиданные данные: %s", data)

    def consoleEnter(self):
        data = self.consoleEdit.getInput()
        if data:
            self.port.write(data)

    def sendMessage(self, message):
        self.processCommand(morseTxCommand.encode(message), ackResponse.prefix)

    def printMessage(self, message):
        self.processCommand(morsePrintCommand.encode(message), ackResponse.prefix)

    def closeEvent(self, event):
        if self.askForExit():
            self.saveData()
            self.saveSettings()
            self.logger.info("завершение")
        else:
            event.ignore()

    def reset(self):
        self.logger.info("сброс")
        self.port.reset()

    @staticmethod
    def saveData():
        with open(DATA_FILE_NAME, 'w', newline = '\r\n') as dataFile, open(TEXT_FILE_NAME, 'w', newline = '\r\n') as textFile:
            MessageFrame.writeData(dataFile, textFile)

    @staticmethod
    def loadData():
        try:
            dataFile = open(DATA_FILE_NAME)
        except OSError:
            dataFile = None
        MessageFrame.readData(dataFile)
        if dataFile:
            dataFile.close()

    def saveSettings(self):
        settings = QSettings()
        try:
            settings.setValue('timeStamp', QDateTime.currentDateTime().toString(LONG_DATETIME_FORMAT))
            settings.beginGroup('window')
            settings.setValue('width', self.size().width())
            settings.setValue('height', self.size().height())
            settings.setValue('x', max(0, self.pos().x()))
            settings.setValue('y', max(0, self.pos().y()))
            settings.setValue('maximized', self.isMaximized())
            settings.setValue('windowState', self.saveState())
            settings.setValue('splitterState', self.splitter.saveState())
            settings.endGroup()
        except:
            self.logger.exception("Error saving settings")
            settings.clear()
        settings.sync()

    def loadSettings(self):
        QCoreApplication.setOrganizationName('Ostranna')
        QCoreApplication.setOrganizationDomain('ostranna.ru')
        QCoreApplication.setApplicationName('Morse Control')
        settings = QSettings()
        self.savedMaximized = False
        if self.needLoadSettings:
            self.logger.info("Загрузка настроек из %s", settings.fileName())
            try:
                try:
                    timeStamp = settings.value('timeStamp', type = str)
                except TypeError:
                    timeStamp = None
                if timeStamp:
                    settings.beginGroup('window')
                    self.resize(settings.value('width', type = int), settings.value('height', type = int))
                    self.move(settings.value('x', type = int), settings.value('y', type = int))
                    self.savedMaximized = settings.value('maximized', False, type = bool)
                    self.restoreState(settings.value('windowState', type = QByteArray))
                    self.splitter.restoreState(settings.value('splitterState', type = QByteArray))
                    settings.endGroup()
                    self.logger.info("Загружены настройки датированные %s", timeStamp)
                    return
                else:
                    self.logger.info("Сохраненные настройки не найдены")
            except:
                self.logger.exception("Ошибка загрузки настроек")

    def error(self, message):
        print("ERROR:", message)
        self.logger.error(message)
        exit(-1)

if __name__ == '__main__': # Not using main() function per recommendation for PyQt5:
    try:                   # http://pyqt.sourceforge.net/Docs/PyQt5/pyqt4_differences.html#object-destruction-on-exit
        application = QApplication(argv)
        setlocale(LC_ALL, ('ru_RU', 'UTF-8')) # doesn't work on Ubuntu if performed earlier
        translator = QTranslator()
        if translator.load('qt_ru'):
            application.installTranslator(translator)
        morseControl = MorseControl(argv[1:]) # retain reference
        retCode = application.exec_()
        application.deleteLater()
        exit(retCode)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except BaseException:
        print(format_exc())
        exit(-1)
