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
UNKNOWN = 'НПН'
ERROR = 'ОШК'
CONNECT = 'СОЕД'

EXCEPTION = 'EXCEPTION'

SPACE = ' '
WORD_SPACE = 3 * SPACE
WORD_SPACE_RE = reCompile(r' {2,}')

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
    def __init__(self, codes = RUSSIAN_CODES, errorCode = '.', defaultChar = UNKNOWN, defaultCode = EXCEPTION): # pylint: disable=W0102
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
        self.sendErrorCode = self.errorCode * ((self.maxCodeLength + len(self.errorCode)) // len(self.errorCode))
        self.defaultChar = self._validateDefaultChar(defaultChar)
        self.defaultCode = self._validateDefaultCode(defaultCode)

    @staticmethod
    def _validateCode(code):
        assert code, "Empty code"
        assert SPACE not in code, "Space in code: %r" % code
        assert set(code) <= DOT_DASH, "Bad code: %r" % code
        return code

    def _validateDefaultChar(self, defaultChar):
        assert defaultChar in ('', UNKNOWN, EXCEPTION) or defaultChar in self.encoding, "Unknown default character: %r" % defaultChar
        return defaultChar

    def _validateDefaultCode(self, defaultCode):
        assert defaultCode in ('', EXCEPTION) or defaultCode in self.decoding, "Unknown default code: %r" % defaultCode
        return defaultCode

    def isError(self, code):
        return self.errorCode and len(code) > self.maxCodeLength and code == self.errorCode * (len(code) // len(self.errorCode))

    def encodeSymbol(self, char, defaultCode = None):
        assert char, "Empty symbol"
        assert ' ' not in char, "Encoding spaces is not allowed: %r" % char
        if char == ERROR:
            return self.sendErrorCode
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
        assert word, "Empty word"
        assert ' ' not in word, "Encoding spaces in word is not allowed: %r" % word
        if isinstance(word, str):
            ret = self.encodeSymbol(word, '')
            if ret:
                return ret
        return SPACE.join(c for c in (self.encodeSymbol(char, defaultCode) for char in word) if c)

    def decodeWord(self, codeWord, defaultChar = None, processErrors = False):
        ret = []
        exception = None
        for code in codeWord.strip().split(SPACE) if isinstance(codeWord, str) else codeWord:
            code = code.strip()
            if not code:
                continue
            try:
                char = self.decodeSymbol(code, defaultChar)
            except KeyError as e:
                if not processErrors:
                    raise
                if not exception:
                    exception = e
                continue
            if processErrors and char == ERROR:
                exception = None
                ret.clear()
            elif char:
                ret.append(char if len(char) == 1 else '%s%s ' % ('' if not ret or ret[-1][-1] == ' ' else ' ', char))
        if exception:
            raise exception # pylint: disable=E0702
        return ''.join(ret).strip()

    def encodePhrase(self, phrase, defaultCode = None):
        return WORD_SPACE.join(self.encodeWord(word.strip(), defaultCode) for word in (phrase.strip().split() if isinstance(phrase, str) else phrase)) # pylint: disable=C0325

    def decodePhrase(self, codePhrase, defaultChar = None, processErrors = False):
        ret = []
        for codeWord in (cw for cw in (cw.strip() for cw in WORD_SPACE_RE.split(codePhrase)) if cw):
            word = self.decodeWord(codeWord, defaultChar, processErrors)
            if word:
                ret.append(word)
        return ' '.join(ret)

    def encodeMessage(self, message, defaultCode = None, wrapForTransmission = False):
        return self.encodePhrase(chain((START,), message.strip().split() if isinstance(message, str) else message, (END,)) if wrapForTransmission else message, defaultCode)

    def decodeMessage(self, codePhrase, defaultChar = None, processErrors = False):
        return self.decodePhrase(codePhrase, defaultChar, processErrors)

    def codeToBits(self, codePhrase, bitsPerDit = BITS_PER_DIT, wrapForTransmission = False):
        ret = PAUSE.join(CODE_TO_BITS[c] for c in (chain(self.sendErrorCode * 2, '   ', codePhrase) if wrapForTransmission else codePhrase)) # pylint: disable=C0325
        return ''.join(c * bitsPerDit for c in ret)

    def parseMessage(self, message, bitsPerDit = BITS_PER_DIT):
        ret = []
        for char in message.strip():
            if char == SPACE:
                ret.append((self.codeToBits(WORD_SPACE + SPACE, bitsPerDit), WORD_SPACE, SPACE))
            else:
                if ret and ret[-1][-1] != SPACE:
                    ret.append((self.codeToBits(SPACE + SPACE, bitsPerDit), SPACE, ''))
                code = self.encodeSymbol(char)
                bits = self.codeToBits(code, bitsPerDit)
                ret.append((bits, code, self.decodeSymbol(code)))
        return tuple(ret)

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
        lengths = sorted(len(token) for token in tokens)
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
                    char = self.decodeSymbol(code) if groupOK else ''
                    if char == ERROR and not ret:
                        char = CONNECT
                    ret.append((''.join(groupBits), code, char))
                    groupBits = []
                    groupCode = []
                    groupOK = True
                if length: # not the last token
                    ret.append((token, SPACE if length <= maxDah else WORD_SPACE, '' if length <= maxDah else SPACE))
        return tuple(ret)

    @staticmethod
    def bitsToChars(bits):
        chars = tuple(b[-1] for b in bits)
        return ''.join((a + ' ' if len(a) > 1 and b != ' ' else a) for (a, b) in zip(chars, chain(chars[1:], [' '])))

    def messageToBits(self, message, bitsPerDit = BITS_PER_DIT, wrapForTransmission = False):
        return self.codeToBits(self.encodeMessage(message, wrapForTransmission = wrapForTransmission), bitsPerDit, wrapForTransmission)

class MorseTest(TestCase):
    def setUp(self):
        self.morse = Morse()

    def testEncodeSymbol(self, f = None):
        f = f or self.morse.encodeSymbol
        self.assertEqual(f('А'), '.-')
        self.assertEqual(f('ё'), '.')
        self.assertEqual(f('ь'), '-..-')
        self.assertEqual(f(')'), '-.--.-')
        self.assertEqual(f('НЧЛ'), '-.-.-')
        self.assertEqual(f('ОШК'), '.......')
        self.assertEqual(f('НПН', ''), '')
        self.assertEqual(f('НПН', '.-'), '.-')
        self.assertRaises(KeyError, f, 'НПН', EXCEPTION)
        self.assertRaises(AssertionError, f, '')
        self.assertRaises(KeyError, f, '.......')
        self.assertRaises(KeyError, f, 'НПН')
        self.assertRaises(AssertionError, f, 'АБ ')

    def testEncodeWord(self, f = None):
        f = f or self.morse.encodeWord
        self.assertEqual(f('А'), '.-')
        self.assertEqual(f('ё'), '.')
        self.assertEqual(f('ь'), '-..-')
        self.assertEqual(f(')'), '-.--.-')
        self.assertEqual(f('НЧЛ'), '-.-.-')
        self.assertEqual(f('ОШК'), '.......')
        self.assertRaises(AssertionError, f, '')
        self.assertRaises(AssertionError, f, 'АБ ')
        self.assertRaises(AssertionError, f, 'аб вг')
        self.assertRaises(AssertionError, f, 'абвг', '...-.')
        self.assertRaises(AssertionError, f, 'абвг', '. -')
        self.assertEqual(f('аБв'), '.- -... .--')
        self.assertEqual(f('АБВ', EXCEPTION), '.- -... .--')
        self.assertEqual(f(['а', 'Б', 'в']), '.- -... .--')
        self.assertEqual(f('НчЛ'), '-.-.-')
        self.assertRaises(KeyError, f, 'АБZ')
        self.assertEqual(f('АБZВ', ''), '.- -... .--')
        self.assertEqual(f('АБZВ', '.-.-.-'), '.- -... .-.-.- .--')
        chars = ['1', 'Д', '9', '?', 'Ч', 'Б', 'Ш', '.', 'Г', '4', 'Ь', 'Ъ', 'Й', 'О', ';', 'К', 'Ы', 'С', ':', 'А', 'М', '5', '(', ')', 'Ф', 'Ѳ', 'Л', '+', '3', 'И', 'I', 'Ѵ', 'КНЦ', 'У', 'НЧЛ', '-', '8', '!', 'Э', '7', '2', 'Е', 'Ё', 'Ѣ', 'Ж', 'Ю', 'Ц', "'", 'Н', '=', 'Щ', 'Х', '*', '6', 'П', '0', 'В', '/', '\\', 'Р', 'Я', 'Т', '"', 'З']
        codes = '.---- -.. ----. ..--.. ---. -... ---- ...... --. ....- -..- -..- .--- --- -.-.-. -.- -.-- ... ---... .- -- ..... -.--.- -.--.- ..-. ..-. .-.. .-.-. ...-- .. .. .. ..-.- ..- -.-.- -....- ---.. --..-- ..-.. --... ..--- . . . ...- ..-- -.-. .----. -. -...- --.- .... .... -.... .--. ----- .-- -..-. -..-. .-. .-.- - .-..-. --..'
        self.assertEqual(f(chars), codes)

    def testEncodePhrase(self, f = None):
        f = f or self.morse.encodePhrase
        self.assertEqual(f('А'), '.-')
        self.assertEqual(f('ё'), '.')
        self.assertEqual(f('ь'), '-..-')
        self.assertEqual(f(')'), '-.--.-')
        self.assertEqual(f('НЧЛ'), '-.-.-')
        self.assertEqual(f('ОШК'), '.......')
        self.assertRaises(AssertionError, f, 'абвг', '...-.')
        self.assertRaises(AssertionError, f, 'абвг', '. -')
        self.assertEqual(f('  аБв   '), '.- -... .--')
        self.assertEqual(f('АБВ', EXCEPTION), '.- -... .--')
        self.assertEqual(f(['а', 'Б', 'в']), '.-   -...   .--')
        self.assertEqual(f('НчЛ'), '-.-.-')
        self.assertRaises(KeyError, f, 'АБZ')
        self.assertEqual(f('АБZВ', ''), '.- -... .--')
        self.assertEqual(f('АБZВ', '.-.-.-'), '.- -... .-.-.- .--')
        self.assertEqual(f(()), '')
        self.assertRaises(AssertionError, f, ('',))
        chars = ['1', 'Д', '9', '?', 'Ч', 'Б', 'Ш', '.', 'Г', '4', 'Ь', 'Ъ', 'Й', 'О', ';', 'К', 'Ы', 'С', ':', 'А', 'М', '5', '(', ')', 'Ф', 'Ѳ', 'Л', '+', '3', 'И', 'I', 'Ѵ', 'КНЦ', 'У', 'НЧЛ', '-', '8', '!', 'Э', '7', '2', 'Е', 'Ё', 'Ѣ', 'Ж', 'Ю', 'Ц', "'", 'Н', '=', 'Щ', 'Х', '*', '6', 'П', '0', 'В', '/', '\\', 'Р', 'Я', 'Т', '"', 'З']
        codes = '.----   -..   ----.   ..--..   ---.   -...   ----   ......   --.   ....-   -..-   -..-   .---   ---   -.-.-.   -.-   -.--   ...   ---...   .-   --   .....   -.--.-   -.--.-   ..-.   ..-.   .-..   .-.-.   ...--   ..   ..   ..   ..-.-   ..-   -.-.-   -....-   ---..   --..--   ..-..   --...   ..---   .   .   .   ...-   ..--   -.-.   .----.   -.   -...-   --.-   ....   ....   -....   .--.   -----   .--   -..-.   -..-.   .-.   .-.-   -   .-..-.   --..'
        self.assertEqual(f(chars), codes)
        chars = 'ПОЛУЧЕННАЯ ТЕЛЕГРАММА, ТРУЛЯЛЯ-ТРАЛЯЛЯ!'
        codes = '.--. --- .-.. ..- ---. . -. -. .- .-.-   - . .-.. . --. .-. .- -- -- .- .-.-.-   - .-. ..- .-.. .-.- .-.. .-.- -....- - .-. .- .-.. .-.- .-.. .-.- --..--'
        self.assertEqual(f(chars), codes)

    def testEncodeMessage(self, f = None):
        f = f or self.morse.encodeMessage
        self.testEncodePhrase(f)
        self.assertEqual(f('ь', None, True), '-.-.-   -..-   ..-.-')
        self.assertEqual(f('аБвГ', None, True), '-.-.-   .- -... .-- --.   ..-.-')
        self.assertEqual(f('   аБ в Г ', None, True), '-.-.-   .- -...   .--   --.   ..-.-')
        self.assertEqual(f(('аБ', 'в', 'Г'), None, True), '-.-.-   .- -...   .--   --.   ..-.-')

    def testDecodeSymbol(self, f = None):
        f = f or self.morse.decodeSymbol
        self.assertRaises(AssertionError, f, '. -')
        self.assertRaises(AssertionError, f, '.=')
        self.assertRaises(AssertionError, f, '.-', 'АБВ')
        self.assertRaises(AssertionError, f, '.-', 'Z')
        self.assertEqual(f('.-'), 'А')
        self.assertEqual(f('.-', ''), 'А')
        self.assertEqual(f('.-', 'НПН'), 'А')
        self.assertEqual(f('.-', EXCEPTION), 'А')
        self.assertEqual(f('...-.', ''), '')
        self.assertEqual(f('...-.', 'НПН'), 'НПН')
        self.assertRaises(KeyError, f, '...-.', EXCEPTION)
        self.assertEqual(f('......'), '.')
        self.assertEqual(f('.......'), 'ОШК')
        self.assertEqual(f('........'), 'ОШК')
        self.assertEqual(f('..............................'), 'ОШК')
        self.assertEqual(f('..............-...............'), 'НПН')
        self.assertEqual(f('...-.'), 'НПН')
        self.assertEqual(f('..-.'), 'Ф')
        self.assertEqual(f('.--.-.'), 'Ь')

    def testDecodeWord(self, f = None):
        f = f or self.morse.decodeWord
        self.assertRaises(AssertionError, f, '.=')
        self.assertRaises(AssertionError, f, '.-', 'АБВ')
        self.assertRaises(AssertionError, f, '.-', 'Z')
        self.assertEqual(f('.-'), 'А')
        self.assertEqual(f('  .-   ', ''), 'А')
        self.assertEqual(f('  .- ', 'НПН'), 'А')
        self.assertEqual(f('.-', EXCEPTION), 'А')
        self.assertEqual(f('...-.', ''), '')
        self.assertEqual(f('...-.', 'НПН'), 'НПН')
        self.assertRaises(KeyError, f, '...-.', EXCEPTION)
        self.assertEqual(f('......'), '.')
        self.assertEqual(f('.......'), 'ОШК')
        self.assertEqual(f('........'), 'ОШК')
        self.assertEqual(f('..............................'), 'ОШК')
        self.assertEqual(f('..............-...............'), 'НПН')
        self.assertEqual(f('........', None, True), '')
        self.assertEqual(f('...-. .- ........', None, True), '')
        self.assertEqual(f('...-.'), 'НПН')
        self.assertEqual(f('..-.'), 'Ф')
        self.assertEqual(f('.--.-.'), 'Ь')
        self.assertEqual(f('.-     -...' if f is self.morse.decodeWord else '.- -...'), 'АБ')
        self.assertRaises(KeyError, f, '.- ...-.', EXCEPTION)
        self.assertEqual(f('.- ...-. -...'), 'А НПН Б')
        self.assertEqual(f('.- ...-. ...-. -...'), 'А НПН НПН Б')
        self.assertEqual(f('.- ...-. ............... ...-. -...'), 'А НПН ОШК НПН Б')
        self.assertEqual(f('.- ...-. ............... ...-. -...', processErrors = True), 'НПН Б')
        self.assertEqual(f('.- ...-. ............... ...-. -...', processErrors = True), 'НПН Б')
        self.assertEqual(f('.- ...-. ............... ...-. -...', ''), 'А ОШК Б')
        self.assertRaises(KeyError, f, '.- ...-. ............... ...-. -...', EXCEPTION)
        self.assertRaises(KeyError, f, '.- ...-. ....... ...-. -...', EXCEPTION, True)
        self.assertEqual(f('.- ...-. ........ -...', EXCEPTION, processErrors = True), 'Б')
        self.assertEqual(f('.- ...-. .- ...-. ........ -...', EXCEPTION, processErrors = True), 'Б')
        codes = '.---- -.. ----. ..--.. ---. -... ---- ...... --. ....- -..- --.-- .--.-. .--- --- -.-.-. -.- -.-- ... ---... .- -- ..... -.--.- -.--. ..-. .-.. .-.-. ...-- .. ..-.- ...-.- ..- -.-.- -....- ---.. --..-- ..-.. --... .-.-.- ..--- . ...- ..-- -.-. .----. -. -...- --.- .... -.... .--. ----- .-- -..-. .-. .-.- - .-..-. --..'
        chars = '1Д9?ЧБШ.Г4ЬЬЬЙО;КЫС:АМ5((ФЛ+3И КНЦ КНЦ У НЧЛ -8!Э7,2ЕЖЮЦ\'Н=ЩХ6П0В/РЯТ"З'
        self.assertEqual(f(codes), chars)

    def testDecodePhrase(self, f = None):
        f = f or self.morse.decodePhrase
        self.testDecodeWord(f)
        codes = '      .--. --- .-.. ..- ---. . -. -. .- .-.-   - . .-.. . --. .-. .- -- -- .- .-.-.-   - .-. ..- .-.. -..-- ---.- .......... - .-. ..- .-.. .-.- .-.. .-.- -....- - .-. .- .-.. .-.- .-.. .-.- --..--   '
        self.assertEqual(f(codes), 'ПОЛУЧЕННАЯ ТЕЛЕГРАММА, ТРУЛ НПН НПН ОШК ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertEqual(f(codes, ''), 'ПОЛУЧЕННАЯ ТЕЛЕГРАММА, ТРУЛ ОШК ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertEqual(f(codes, None, True), 'ПОЛУЧЕННАЯ ТЕЛЕГРАММА, ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertEqual(f(codes, EXCEPTION, True), 'ПОЛУЧЕННАЯ ТЕЛЕГРАММА, ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertRaises(KeyError, f, codes, EXCEPTION)
        codes = '  .--. --- .-.. ..- ---. . -. -. .- .-.-  - . .-.. . --. .-. ...-. -- -- .- .-.-.-  - .-. ..- .-.. -..-- ---.- .......... - .-. ..- .-.. .-.- .-.. .-.- -....- - .-. .- .-.. .-.- .-.. .-.- --..-- '
        self.assertEqual(f(codes), 'ПОЛУЧЕННАЯ ТЕЛЕГР НПН ММА, ТРУЛ НПН НПН ОШК ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertEqual(f(codes, ''), 'ПОЛУЧЕННАЯ ТЕЛЕГРММА, ТРУЛ ОШК ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertEqual(f(codes, None, True), 'ПОЛУЧЕННАЯ ТЕЛЕГР НПН ММА, ТРУЛЯЛЯ-ТРАЛЯЛЯ!')
        self.assertRaises(KeyError, f, codes, EXCEPTION, True)
        self.assertRaises(KeyError, f, codes, EXCEPTION)

    def testDecodeMessage(self, f = None):
        f = f or self.morse.decodeMessage
        self.testDecodePhrase(f)

    def testBits(self):
        bits = '1010101010101010101010101010000000111010111010111000000010111011101000111011101110001011101010001010111000111011101110100010001110100011101000101110001011101011100000001110001000101110101000100011101110100010111010001011100011101110001110111000101110001011101011101011100000001110001011101000101011100010111010100010111010111000101110101000101110101110001110101010101110001110001011101000101110001011101010001011101011100010111010100010111010111000111011101010111011100000001010111010111'
        chars = 'Полученная телеграмма, труляля-траляля!'
        self.assertEqual(self.morse.messageToBits(chars, 1, True), bits)
        self.assertEqual(self.morse.bitsToChars(self.morse.parseBits(bits)), ' '.join((CONNECT, START, chars.upper(), END)))

    def testErrors(self):
        bits = '1010101010101010101010101010000000111010111010111000000010111011101000111011101110001011101010001010111000111011101110100010001110100011101000101110001011101011100000001110001000101110101000100011101110100010111010001011100011101110001110111000101110001011101011101011100000001110001011101000101011100010111010100010111010111000101110101000101110101110001110101010101110001110001011101000101110001011101010001011101011100010111010100010111010111000111011101010111011100000001010111010111'
        chars = 'Полученная телеграмма, труляля-траляля!'
        self.assertEqual(self.morse.messageToBits(chars, 1, True), bits)
        self.assertEqual(self.morse.bitsToChars(self.morse.parseBits(bits)), ' '.join((CONNECT, START, chars.upper(), END)))

    # ToDo: Create more tests!

if __name__ == '__main__':
    main()
