
D = 0.7

def makeUncertain(bits):
    count1 = {}
    count3 = {}
    count7 = {}
    tokens = TOKENIZER.split(bits)
    counter = Counter(len(t) for t in tokens if t)
    lengths = tuple(k for (k, v) in sorted(counter.items(), key = lambda k_v: -k_v[1])[:3])
    (one, three, seven) = sorted(lengths) + [0,] * (3 - len(lengths))
    three = three or 3 * one
    seven = seven or three * 7 // 3
    maxDot = (one + three) // 2
    maxDash = (three + seven) // 2
    dOne = min(maxDot - one, one - 1)
    dThree = min(maxDash - three, three - maxDot - 1)
    dSeven = seven - maxDash - 1
    ret = []
    for token in tokens:
        if len(token) == one:
            token = token[0] * max(1, min(maxDot, one + int(gauss(0, D) * dOne)))
            count1[len(token)] = count1.get(len(token), 0) + 1
        elif len(token) == three:
            token = token[0] * max(maxDot + 1, min(maxDash, three + int(gauss(0, D) * dThree)))
            count3[len(token)] = count3.get(len(token), 0) + 1
        elif len(token) == seven:
            token = token[0] * max(maxDash + 1, seven + int(gauss(0, D) * dSeven))
            count7[len(token)] = count3.get(len(token), 0) + 1
        ret.append(token)
    return ''.join(ret)

from collections import OrderedDict
from random import gauss
def encodeUncertain(morseCode, rate = 2, d = 0.7):
    STAT = OrderedDict(((1, OrderedDict((('n', 0), ('sum', 0.0), ('stat', 0), ('tmin', 999), ('tmax', 0), ('min', 999), ('max', 0), ('mid', 0)))),
                        (3, OrderedDict((('n', 0), ('sum', 0.0), ('stat', 0), ('tmin', 999), ('tmax', 0), ('min', 999), ('max', 0), ('mid', 0)))),
                        (7, OrderedDict((('n', 0), ('sum', 0.0), ('stat', 0), ('tmin', 999), ('tmax', 0), ('min', 999), ('max', 0), ('mid', 0))))))
    def token(typ, mn, mx, n, r):
        g = int(round(rate * (n + r * gauss(0, d))))
        v = max(mn, min(mx, g))
        s = STAT[n]
        s['n'] += 1
        s['sum'] += v
        s['stat'] = s['sum'] / s['n']
        s['tmin'] = min(s['tmin'], g)
        s['tmax'] = max(s['tmax'], g)
        s['min'] = min(s['min'], v)
        s['max'] = max(s['max'], v)
        s['mid'] = (s['min'] + s['max']) / 2.0
        return (typ * v)
    maxDot = min(int(3 * rate) - 1, int(ceil(2 * rate)))
    maxDash = min(int(7 * rate) - 1, int(ceil(5 * rate)))
    maxPause = int(ceil(9 * rate))
    print rate, maxDot, 3 * rate, maxDash, 7 * rate, maxPause
    prev = ' '
    ret = []
    for c in morseCode.strip().replace('   ', '='):
        if c in '.-' and prev in '.-':
            ret.append(token('0', 1, maxDot, 1, 1))
        if c == '.':
            ret.append(token('1', 1, maxDot, 1, 1))
        elif c == '-':
            ret.append(token('1', maxDot + 1, maxDash, 3, 1))
        elif c == ' ':
            ret.append(token('0', maxDot + 1, maxDash, 3, 1))
        elif c == '=':
            ret.append(token('0', maxDash + 1, maxPause, 7, 2))
        else:
            assert False
        prev = c
    print STAT
    return ''.join(ret)
