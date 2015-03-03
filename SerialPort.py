#!/usr/bin/env python3
#
# Morse Console
# Serial port operation routines
#
from collections import deque
from itertools import chain
from re import sub
from threading import Thread
from time import sleep, time

try:
    from serial import Serial, SerialTimeoutException
    from serial.tools.list_ports import comports
except ImportError as ex:
    raise ImportError("%s: %s\n\nPlease install pySerial v2.6 or later: http://pypi.python.org/pypi/pyserial\n" % (ex.__class__.__name__, ex))

BAUD_RATES = (512000, 256000, 230000, 115200, 57600, 38400, 28800, 19200, 14400, 9600, 4800, 2400, 1200, 300)
NUM_CONNECT_ATTEMPTS = 3
TIMEOUT = 1
DT = 0.1

class SerialPort(object):
    TRYING = 0
    CONNECTED = 1
    VERIFIED = 2
    ERROR = 3
    NONE = 4

    def __init__(self, logger, ping = None, pong = '', connectCallback = None, disconnectCallback = None, readCallback = None, portTryCallback = None, externalPort = None, baudRates = BAUD_RATES):
        self.logger = logger
        self.ping = ping
        self.pong = pong
        self.baudRates = baudRates
        self.baudRate = self.baudRates[0]
        self.connectCallback = connectCallback
        self.disconnectCallback = disconnectCallback
        self.readCallback = readCallback
        self.portTryCallback = portTryCallback
        self.externalPort = externalPort
        self.writeBuffer = deque(maxlen = 1)
        self.port = None
        self.ready = None
        self.expectTimeout = None
        self.expectPrefix = None
        self.expectResult = None
        self.startThread(self.reader, 'reader')
        self.startThread(self.writer, 'writer')
        self.startThread(self.connect, 'connect')

    def startThread(self, what, name):
        thread = Thread(target = what, name = '%s 0x%x %s' % (self.__class__.__name__, id(self), name))
        thread.setDaemon(True)
        thread.start()

    def statusUpdate(self, portName, portStatus):
        if self.portTryCallback:
            self.portTryCallback(portName, portStatus)

    def reader(self):
        while True:
            try:
                if self.port:
                    line = self.port.readline()
                    if line:
                        self.logger.info("< %s" % line.rstrip())
                        if self.expectTimeout and time() < self.expectTimeout and line.lower().startswith(self.expectPrefix.lower()):
                            self.expectResult = line
                        elif self.ready and self.readCallback:
                            self.readCallback(line)
            except Exception:
                #from traceback import format_exc
                #print(format_exc())
                self.logger.warning("Соединение разорвано")
                self.reset()
            sleep(DT)

    def writer(self):
        while True:
            if self.writeBuffer:
                data = self.writeBuffer.popleft() + '\n'
                while True:
                    while not self.port:
                        sleep(DT)
                    try:
                        if self.port.write(data) == len(data):
                            break
                    except SerialTimeoutException:
                        pass
                    self.reset()
            else:
                sleep(DT)

    def connect(self):
        first = True
        while True:
            while self.port:
                sleep(DT)
            if first:
                first = False
            else:
                if self.disconnectCallback:
                    self.disconnectCallback()
            self.statusUpdate("СКАН", self.TRYING)
            sleep(DT)
            portNames = (self.externalPort.name,) if self.externalPort else tuple(portName for (portName, _description, _address) in comports())
            if portNames:
                for portName in portNames:
                    for self.baudRate in chain((self.baudRate,), tuple(br for br in self.baudRates if br != self.baudRate)):
                        try:
                            displayPortName = sub('^/dev/', '', portName)
                            self.statusUpdate(displayPortName, self.TRYING)
                            self.port = self.externalPort or Serial(portName, baudrate = self.baudRate, timeout = TIMEOUT, writeTimeout = TIMEOUT)
                            self.statusUpdate(displayPortName, self.CONNECTED)
                            self.logger.info("Подключен порт %s на скорости %d бод" % (portName, self.baudRate))
                            if self.ping:
                                for _ in range(NUM_CONNECT_ATTEMPTS):
                                    pong = self.command(self.ping, self.pong, notReady = True)
                                    if pong is not None:
                                        if self.connectCallback:
                                            self.connectCallback(pong)
                                        self.ready = True
                                        break
                                else:
                                    continue
                                break
                            else:
                                self.ready = True
                                break
                        except Exception:
                            self.statusUpdate(displayPortName, self.ERROR)
                        self.reset()
                    else:
                        self.baudRate = self.baudRates[0]
                        continue
                    break
            else:
                self.statusUpdate("Нет COM", self.NONE)

    def reset(self):
        if self.port:
            self.port.close()
            self.port = None

    def write(self, data, notReady = False):
        data = str(data)
        if self.port and (self.ready or notReady):
            self.logger.info(" > %s" % data.rstrip())
            self.writeBuffer.append(data)
        else:
            self.logger.info(" >! %s" % data)

    def expect(self, prefix, idle = None, notReady = False):
        if self.port and (self.ready or notReady):
            self.expectPrefix = prefix
            self.expectResult = None
            self.expectTimeout = time() + self.port.timeout
            while self.expectResult is None and time() < self.expectTimeout:
                if idle:
                    idle()
                else:
                    sleep(DT)
            if idle:
                idle()
            else:
                sleep(0)
            self.expectTimeout = None
            return self.expectResult

    def command(self, command, expectPrefix = None, idle = None, notReady = False):
        self.write(command, notReady)
        return self.expect(expectPrefix, idle, notReady) if expectPrefix is not None else None
