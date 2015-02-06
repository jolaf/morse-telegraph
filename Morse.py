#!/usr/bin/env python3
from itertools import chain
from re import compile as reCompile
from unittest import main, TestCase

DOT = '.'
DASH = '-'
DOT_DASH = frozenset((DOT, DASH))
COMMA = ','
START = 'НЧЛ'
END = 'КНЦ'
ERROR = 'ОШК'

EXCEPTION = 'EXCEPTION'

SPACE = ' '
WORD_SPACE = 3 * SPACE

DIT = '1'
DAH = '111'
PAUSE = '0'
DIT_PAUSE = frozenset((DIT, PAUSE))
TOKENIZER = reCompile('(%s+)' % PAUSE)

BITS_PER_DIT = 3

CODE_TO_BITS = {
    DOT: DIT,
    DASH: DAH,
    SPACE: PAUSE
}

RUSSIAN_CODES = {
    'А': '.-',
    'Б': '-...',
    'В': '.--',
    'Г': '--.',
    'Д': '-..',
    'Е,Ё,Ѣ': '.',
    'Ж': '...-',
    'З': '--..',
    'И,I,Ѵ': '..',
    'Й': '.---',
    'К': '-.-',
    'Л': '.-..',
    'М': '--',
    'Н': '-.',
    'О': '---',
    'П': '.--.',
    'Р': '.-.',
    'С': '...',
    'Т': '-',
    'У': '..-',
    'Ф,Ѳ': '..-.',
    'Х,*': '....',
    'Ц': '-.-.',
    'Ч': '---.',
    'Ш': '----',
    'Щ': '--.-',
    'Ь,Ъ': '-..-,--.--,.--.-.',
    'Ы': '-.--',
    'Э': '..-..',
    'Ю': '..--',
    'Я': '.-.-',
    '0': '-----',
    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
    '.': '......',
    ',': '.-.-.-',
    ';': '-.-.-.',
    ':': '---...',
    '?': '..--..',
    '!': '--..--',
    "'": '.----.',
    '"': '.-..-.',
    '(,)': '-.--.-,-.--.',
    '-': '-....-',
    '+': '.-.-.',
    '/,\\': '-..-.',
    '=': '-...-',
    START: '-.-.-',
    END: '..-.-,...-.-'
}

class Morse(object):
    def __init__(self, codes = RUSSIAN_CODES, errorCode = '.', defaultChar = '', defaultCode = ''): # pylint: disable=W0102
        assert codes, "Empty code table"
        self.encoding = {}
        self.decoding = {}
        self.maxCodeLength = 0
        for (chars, codes) in codes.items():
            assert ' ' not in chars, "Space in chars: %r" % chars
            chars = (COMMA,) if chars == COMMA else chars.split(COMMA)
            assert codes, "Empty codes for chars: %r " % chars
            assert SPACE not in codes, "Space in codes for chars %r: %r" % (chars, codes)
            codes = codes.split(COMMA)
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
        assert SPACE not in code, "Space in code: %r" % code
        assert set(code) <= DOT_DASH, "Bad code: %r" % code
        return code

    def _validateDefaultChar(self, defaultChar):
        assert defaultChar == '' or defaultChar in self.encoding, "Unknown default character: %r" % defaultChar
        return defaultChar

    def _validateDefaultCode(self, defaultCode):
        assert defaultCode == '' or defaultCode in self.decoding, "Unknown default code: %r" % defaultCode
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
        ret = self.encodeSymbol(word, '')
        if ret:
            return ret
        return SPACE.join(self.encodeSymbol(char, defaultCode) for char in word)

    def decodeWord(self, codeWord, defaultChar = None):
        ret = []
        exception = None
        for code in codeWord.strip().split(SPACE) if isinstance(codeWord, str) else codeWord:
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
        return WORD_SPACE.join(self.encodeWord(word, defaultCode) for word in chain.from_iterable(p.strip().split() for p in ((phrase,) if isinstance(phrase, str) else phrase))) # pylint: disable=C0325

    def decodePhrase(self, codePhrase, defaultChar = None):
        ret = []
        for codeWord in (cw for cw in (cw.strip() for cw in (codePhrase.split(WORD_SPACE)) if cw)):
            if ret and self.isError(codeWord.split()[0]):
                ret.pop()
            ret.append(self.decodeWord(codeWord, defaultChar))
        return ' '.join(ret)

    def encodeMessage(self, message, defaultCode = None, wrapForTransmission = False):
        return self.encodePhrase((START, message, END) if wrapForTransmission else message, defaultCode)

    def decodeMessage(self, codePhrase, defaultChar = None):
        return self.decodePhrase(codePhrase, defaultChar)

    def codeToBits(self, codePhrase, bitsPerDit = BITS_PER_DIT, wrapForTransmission = False):
        ret = PAUSE.join(CODE_TO_BITS[c] for c in codePhrase)
        return ''.join(c * bitsPerDit for c in chain(2 * self.maxCodeLength * DIT, 7 * PAUSE, ret)) if wrapForTransmission else ret

    def parseBits(self, bits, zeros = frozenset('0._ '), ones = frozenset('1|-=+*^'), convertZerosTo = PAUSE, convertOnesTo = DIT):
        class Cluster(object):
            def __init__(self, center, weight, mn, mx):
                self.center = center
                self.weight = weight
                self.mn = mn
                self.mx = mx
            def __str__(self):
                return '%s(%s, %s, %s, %s)' % (self.__class__.__name__, self.center, self.weight, self.mn, self.mx)
        tokens = TOKENIZER.split(''.join(convertOnesTo if b in ones else convertZerosTo if b in zeros else None for b in bits).strip(convertZerosTo))
        lengths = sorted(len(token) for token in tokens[1:])
        if not lengths:
            lengths = [len(tokens[0])]
        (minLen, maxLen) = (lengths[0], lengths[-1])
        lenRange = float(maxLen - minLen)
        # Employ 3-means clustering
        clusters = tuple(Cluster(minLen + lenRange * x / 8, 0, maxLen, minLen) for x in (1, 3, 7))
        for sample in lengths:
            # Find the closest cluster for this sample
            cluster = min(clusters, key = lambda cluster: abs(sample - cluster.center))# pylint: disable=W0640
            # Adjust cluster: each sample has weight of 1, cluster center is adjusted, its weight increases
            cluster.center = (cluster.center * cluster.weight + sample) / (cluster.weight + 1)
            cluster.weight += 1
            if sample < cluster.mn:
                cluster.mn = sample
            if sample > cluster.mx:
                cluster.mx = sample
        # Fill the gaps if we really have less than 3 clusters
        clusters = [cluster for cluster in clusters if cluster.weight] # Filter out empty clusters
        if len(clusters) == 2:
            if float(clusters[1].mn) / clusters[0].mx >= 5: # If 1 and 7 are present while 3 is not, add a syntetic cluster for 3
                clusters.insert(1, Cluster((clusters[0].mx + clusters[1].mn) / 2.0, 0, clusters[0].mx + 1, clusters[1].mn - 1))
        if len(clusters) < 3: # If only 1 is present (or only 1 and 3 are), add syntetic clusters for 3 and 7 (or just 7)
            limit = clusters[-1].mx + 1
            clusters.extend(Cluster(limit, 0, limit, limit) for i in range(3 - len(clusters)))
        # Calculating edges between dots and dashes, and dashes and word pauses
        maxDit = (clusters[0].mx + clusters[1].mn) / 2.0
        maxDah = (clusters[1].mx + clusters[2].mn) / 2.0
        # Perform transcoding
        ret = []
        groupBits = []
        groupCode = []
        groupOK = True
        for token in chain(tokens, ('',)):
            length = len(token)
            if token and token[0] == convertOnesTo:
                groupBits.append(token)
                if groupOK and length <= maxDah:
                    groupCode.append(DOT if length <= maxDit else DASH)
                else:
                    groupOK = False
            elif length and length <= maxDit:
                groupBits.append(token)
            else:
                if groupBits:
                    code = ''.join(groupCode)
                    ret.append((''.join(groupBits), code, self.decodeSymbol(code) if groupOK else ''))
                    groupBits = []
                    groupCode = []
                    groupOK = True
                if length: # not the last token
                    ret.append((token, SPACE if length <= maxDah else WORD_SPACE, ''))
        return tuple(ret)

    def messageToBits(self, message, wrapForTransmission = False):
        return self.codeToBits(self.encodeMessage(message, wrapForTransmission = wrapForTransmission), wrapForTransmission = wrapForTransmission)

class MorseTest(TestCase):
    def setUp(self):
        self.morse = Morse()

    def testEncode(self):
        chars = ['1', 'Д', '9', '?', 'Ч', 'Б', 'Ш', '.', 'Г', '4', 'Ь', 'Ъ', 'Й', 'О', ';', 'К', 'Ы', 'С', ':', 'A', 'М', '5', '(', ')', 'Ф', 'Ѳ', 'Л', '+', '3', 'И', 'I', 'Ѵ', 'END', 'У', 'START', '-', '8', '!', 'Э', '7', '2', 'Е', 'Ё', 'Ѣ', 'Ж', 'Ю', 'Ц', "'", 'Н', '=', 'Щ', 'Х', '*', '6', 'П', '0', 'В', '/', '\\', 'Р', 'Я', 'Т', '"', 'З']
        codes = '.---- -.. ----. ..--.. ---. -... ---- ...... --. ....- -..- -..- .--- --- -.-.-. -.- -.-- ... ---... .- -- ..... -.--.- -.--.- ..-. ..-. .-.. .-.-. ...-- .. .. .. ..-.- ..- -.-.- -....- ---.. --..-- ..-.. --... ..--- . . . ...- ..-- -.-. .----. -. -...- --.- .... .... -.... .--. ----- .-- -..-. -..-. .-. .-.- - .-..-. --..'
        self.assertEqual(self.morse.encodeWord(chars), codes)

    def testDecode(self):
        codes = '.---- -.. ----. ..--.. ---. -... ---- ...... --. ....- -..- --.-- .--.-. .--- --- -.-.-. -.- -.-- ... ---... .- -- ..... -.--.- -.--. ..-. .-.. .-.-. ...-- .. ..-.- ...-.- ..- -.-.- -....- ---.. --..-- ..-.. --... .-.-.- ..--- . ...- ..-- -.-. .----. -. -...- --.- .... -.... .--. ----- .-- -..-. .-. .-.- - .-..-. --..'
        chars = '1Д9?ЧБШ.Г4ЬЬЬЙО;КЫС:AМ5((ФЛ+3ИENDENDУSTART-8!Э7,2ЕЖЮЦ\'Н=ЩХ6П0В/РЯТ"З'
        self.assertEqual(self.morse.decodeWord(codes), chars)

    # ToDo: Create more tests

if __name__ == '__main__':
    main()
