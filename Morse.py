#!/usr/bin/env python3
from collections import Counter
from itertools import chain
from re import split
from unittest import main, TestCase

DOT = b'.'
DASH = b'-'
DOT_DASH = set(DOT + DASH)
COMMA = ','
bCOMMA = b','
START = '<<'
END = '>>'
ERROR = 'ERROR'

EXCEPTION = 'EXCEPTION'

SPACE = ' '
bSPACE = b' '
WORD_SPACE = 3 * bSPACE

DIT = '1'
DAH = '111'
PAUSE = '0'
DIT_PAUSE = set(DIT + PAUSE)

BITS_PER_DIT = 3

CODE_TO_BITS = {
    DOT: DIT,
    DASH: DAH,
    SPACE: PAUSE
}

RUSSIAN_CODES = {
    'A': b'.-',
    'Б': b'-...',
    'В': b'.--',
    'Г': b'--.',
    'Д': b'-..',
    'Е,Ё,Ѣ': b'.',
    'Ж': b'...-',
    'З': b'--..',
    'И,I,Ѵ': b'..',
    'Й': b'.---',
    'К': b'-.-',
    'Л': b'.-..',
    'М': b'--',
    'Н': b'-.',
    'О': b'---',
    'П': b'.--.',
    'Р': b'.-.',
    'С': b'...',
    'Т': b'-',
    'У': b'..-',
    'Ф,Ѳ': b'..-.',
    'Х,*': b'....',
    'Ц': b'-.-.',
    'Ч': b'---.',
    'Ш': b'----',
    'Щ': b'--.-',
    'Ь,Ъ': b'-..-,--.--,.--.-.',
    'Ы': b'-.--',
    'Э': b'..-..',
    'Ю': b'..--',
    'Я': b'.-.-',
    '0': b'-----',
    '1': b'.----',
    '2': b'..---',
    '3': b'...--',
    '4': b'....-',
    '5': b'.....',
    '6': b'-....',
    '7': b'--...',
    '8': b'---..',
    '9': b'----.',
    '.': b'......',
    ',': b'.-.-.-',
    ';': b'-.-.-.',
    ':': b'---...',
    '?': b'..--..',
    '!': b'--..--',
    "'": b'.----.',
    '"': b'.-..-.',
    '(,)': b'-.--.-,-.--.',
    '-': b'-....-',
    '+': b'.-.-.',
    '/,\\': b'-..-.',
    '=': b'-...-',
    START: b'-.-.-',
    END:   b'..-.-,...-.-',
}

class Morse(object):
    def __init__(self, codes = RUSSIAN_CODES, errorCode = b'.', defaultChar = '', defaultCode = b''): # pylint: disable=W0102
        assert codes, "Empty code table"
        self.encoding = {}
        self.decoding = {}
        self.maxCodeLength = 0
        for (chars, codes) in codes.items():
            assert ' ' not in chars, "Space in chars: %r" % chars
            chars = (COMMA,) if chars == COMMA else chars.split(COMMA)
            assert codes, "Empty codes for chars: %r " % chars
            assert bSPACE not in codes, "Space in codes for chars %r: %r" % (chars, codes)
            codes = codes.split(bCOMMA)
            for char in chars:
                assert char not in self.encoding, "Duplicate character: %r" % char
                self.encoding[char] = codes[0]
            for code in codes:
                assert code, "Empty code for chars: %r " % chars
                assert set(code) <= DOT_DASH, "Bad code for chars %r: %r" % (chars, code)
                assert code not in self.decoding, "Duplicate code: %s" % code
                self.decoding[code] = chars[0]
                self.maxCodeLength = max(self.maxCodeLength, len(code))
        assert self.maxCodeLength
        self.errorCode = errorCode
        self.defaultChar = self._validateDefaultChar(defaultChar)
        self.defaultCode = self._validateDefaultCode(defaultCode)

    @staticmethod
    def _validateCode(code):
        assert code, "Empty code"
        assert bSPACE not in code, "Space in code: %r" % code
        assert set(code) <= DOT_DASH, "Bad code: %r" % code
        return code

    def _validateDefaultChar(self, defaultChar):
        assert defaultChar == '' or defaultChar in self.encoding, "Unknown default character: %r" % defaultChar
        return defaultChar

    def _validateDefaultCode(self, defaultCode):
        assert defaultCode == b'' or defaultCode in self.decoding, "Unknown default code: %r" % defaultCode
        return defaultCode

    def isError(self, code):
        return self.errorCode and len(code) > self.maxCodeLength and code == self.errorCode * (len(code) // len(self.errorCode))

    def encodeSymbol(self, char, defaultCode = None):
        assert ' ' not in char, "Encoding spaces is not allowed: %r" % char
        if defaultCode is None:
            defaultCode = self.defaultCode
        else:
            self._validateDefaultCode(defaultCode)
        return self.encoding[char.upper()] if defaultCode == EXCEPTION else self.encoding.get(char.upper(), defaultCode)

    def decodeSymbol(self, code, defaultChar = None):
        self._validateCode(code)
        if self.isError(code):
            return ERROR
        if defaultChar is None:
            defaultChar = self.defaultChar
        else:
            self._validateDefaultChar(defaultChar)
        return self.decoding[code] if defaultChar == EXCEPTION else self.decoding.get(code, defaultChar)

    def encodeWord(self, word, defaultCode = None):
        assert ' ' not in word, "Encoding spaces in word is not allowed: %r" % word
        return bSPACE.join(self.encodeSymbol(char, defaultCode) for char in word)

    def decodeWord(self, codeWord, defaultChar = None):
        ret = []
        exception = None
        for code in codeWord.strip().split(bSPACE) if type(codeWord) is bytes else codeWord:
            try:
                char = self.decodeSymbol(code, defaultChar)
            except KeyError as e:
                if exception:
                    raise exception # pylint: disable=E0702
                exception = e
                continue
            if char == ERROR:
                exception = None
                ret.clear()
            elif exception:
                raise exception # pylint: disable=E0702
            else:
                ret.append(char)
        if exception:
            raise exception # pylint: disable=E0702
        return ''.join(ret)

    def encodePhrase(self, phrase, defaultCode = None):
        return WORD_SPACE.join(self.encodeWord(word, defaultCode) for word in phrase.strip().split())

    def decodePhrase(self, codePhrase, defaultChar = None):
        ret = []
        for codeWord in (cw for cw in (cw.strip() for cw in (codePhrase.split(WORD_SPACE)) if cw)):
            if ret and self.isError(codeWord.split()[0]):
                ret.pop()
            ret.append(self.decodeWord(codeWord, defaultChar))
        return ' '.join(ret)

    def encodeMessage(self, message, defaultCode = None):
        return self.encodePhrase(chain((START,), message, (END,)), defaultCode)

    def decodeMessage(self, codePhrase, defaultChar = None):
        return self.decodePhrase(codePhrase, defaultChar)

    def codeToBits(self, codePhrase, bitsPerDit = BITS_PER_DIT):
        return DIT * (2 * self.maxCodeLength) + PAUSE.join(CODE_TO_BITS[c] * bitsPerDit for c in codePhrase)

    @staticmethod
    def bitsToCode(bits):
        def nMax(tokens, typ, number):
            counter = Counter(len(t) for t in tokens if t and t[0] == typ)
            lengths = tuple(k for (k, v) in sorted(counter.items(), key = lambda k_v: -k_v[1])[:number])
            return sorted(lengths) + [0,] * (number - len(lengths))
        assert set(bits) == DIT_PAUSE
        tokens = split('(%s+)' % DIT, bits)
        if not tokens:
            return b''
        (zero1, zero3, zero7) = nMax(tokens, PAUSE, 3)
        zero3 = zero3 or 3 * zero1
        zero7 = zero7 or zero3 * 7 // 3
        (one1, one3) = nMax(tokens, DIT, 2)
        one3 = one3 or one1 * 3
        maxDit = (one1 + zero1 + one3 + zero3) // 4
        maxDash = (one3 + zero3 + 2 * zero7) // 4
        ret = []
        for token in tokens:
            length = len(token)
            if token[0] == DIT:
                ret.append(DOT if length <= maxDit else DASH)
            elif len(token) > maxDit:
                ret.append(bSPACE if len(token) <= maxDash else WORD_SPACE)
        return b''.join(ret)

    def messageToBits(self, message):
        return self.codeToBits(self.encodeMessage(message))

class MorseTest(TestCase):
    def setUp(self):
        self.morse = Morse()

    def testEncode(self):
        chars = ['1', 'Д', '9', '?', 'Ч', 'Б', 'Ш', '.', 'Г', '4', 'Ь', 'Ъ', 'Й', 'О', ';', 'К', 'Ы', 'С', ':', 'A', 'М', '5', '(', ')', 'Ф', 'Ѳ', 'Л', '+', '3', 'И', 'I', 'Ѵ', 'END', 'У', 'START', '-', '8', '!', 'Э', '7', '2', 'Е', 'Ё', 'Ѣ', 'Ж', 'Ю', 'Ц', "'", 'Н', '=', 'Щ', 'Х', '*', '6', 'П', '0', 'В', '/', '\\', 'Р', 'Я', 'Т', '"', 'З']
        codes = b'.---- -.. ----. ..--.. ---. -... ---- ...... --. ....- -..- -..- .--- --- -.-.-. -.- -.-- ... ---... .- -- ..... -.--.- -.--.- ..-. ..-. .-.. .-.-. ...-- .. .. .. ..-.- ..- -.-.- -....- ---.. --..-- ..-.. --... ..--- . . . ...- ..-- -.-. .----. -. -...- --.- .... .... -.... .--. ----- .-- -..-. -..-. .-. .-.- - .-..-. --..'
        self.assertEqual(self.morse.encodeWord(chars), codes)

    def testDecode(self):
        codes = b'.---- -.. ----. ..--.. ---. -... ---- ...... --. ....- -..- --.-- .--.-. .--- --- -.-.-. -.- -.-- ... ---... .- -- ..... -.--.- -.--. ..-. .-.. .-.-. ...-- .. ..-.- ...-.- ..- -.-.- -....- ---.. --..-- ..-.. --... .-.-.- ..--- . ...- ..-- -.-. .----. -. -...- --.- .... -.... .--. ----- .-- -..-. .-. .-.- - .-..-. --..'
        chars = '1Д9?ЧБШ.Г4ЬЬЬЙО;КЫС:AМ5((ФЛ+3ИENDENDУSTART-8!Э7,2ЕЖЮЦ\'Н=ЩХ6П0В/РЯТ"З'
        self.assertEqual(self.morse.decodeWord(codes), chars)

    # ToDo: Create more tests

if __name__ == '__main__':
    main()
