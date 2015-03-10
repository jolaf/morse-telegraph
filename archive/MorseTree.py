#!/usr/bin/env python3
try:
    from pygame import init as pyGameInit
    from pygame import Surface
    from pygame import NOFRAME
    from pygame.display import set_mode
    from pygame.draw import aaline
    from pygame.font import SysFont
    from pygame.image import load as imageLoad, save as imageSave, get_extended
except ImportError as ex:
    raise ImportError("%s: %s\n\nPlease install PyGame v1.9.1 or later: http://pygame.org\n" % (ex.__class__.__name__, ex))

assert get_extended()

from Morse import Morse, DOT, DASH, ERROR

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

FONT_NAME = 'Old Standard'

FONT_SIZE = 20

ICON_IMAGE = 'Circle.png'

IN_PAIR_SPACING = 0
INTER_PAIR_SPACING = 0
VERTICAL_SPACING = 0

HORIZONTAL_FIELD = 0
VERTICAL_FIELD = 0

class MorseTree(Morse):
    def __init__(self, *args, **kwargs):
        Morse.__init__(self, *args, **kwargs)
        self.tree = self._createTree()

    def _createTree(self, prefix = b''):
        if prefix:
            ret = self.decoding.get(prefix)
            if ret == ERROR:
                ret = None
        else:
            ret = '?'
        children = (self._createTree(prefix + DOT), self._createTree(prefix + DASH)) if len(prefix) < self.maxCodeLength else (None, None)
        return (ret, children) if ret or children != (None, None) else None

    def drawTree(self, x0, y0, tree, maxLen):
        (v, (a, b)) = tree
        if a or b:
            # 2 ^ (maxLen - 3) * 2 if maxLen > 1 else 0.5
            xStep = (2 ** (maxLen - 3) * (2 + IN_PAIR_SPACING + INTER_PAIR_SPACING) if maxLen > 1 else (1 + IN_PAIR_SPACING) / 2) * self.iconWidth
            print(maxLen, x0, y0, xStep, self.yStep)
            x1 = x0 - xStep
            x2 = x0 + xStep
            y12 = y0 + self.yStep
            if a:
                aaline(self.surface, BLACK, (x0, y0), (x1, y12))
            if b:
                aaline(self.surface, BLACK, (x0, y0), (x2, y12))
        self.surface.blit(self.icon, (x0 - self.iconWidth / 2, y0 - self.iconHeight / 2))
        if v:
            text = self.font.render(v, True, BLACK, WHITE)
            (tw, th) = text.get_size()
            self.surface.blit(text, (x0 - tw / 2, y0 - th / 2))
        if a:
            self.drawTree(x1, y12, a, maxLen - 1)
        if b:
            self.drawTree(x2, y12, b, maxLen - 1)

    def saveTree(self, fileName):
        pyGameInit()
        set_mode((1, 1), NOFRAME)
        self.icon = imageLoad(ICON_IMAGE)
        (self.iconWidth, self.iconHeight) = self.icon.get_size()
        self.yStep = (VERTICAL_SPACING + 1) * self.iconHeight
        self.font = SysFont(FONT_NAME, FONT_SIZE)
        nIcons = 1 << self.maxCodeLength
        nPairs = nIcons // 2
        surfaceWidth = (nIcons + nPairs * IN_PAIR_SPACING + (nPairs - 1) * INTER_PAIR_SPACING + 2 * HORIZONTAL_FIELD) * self.iconWidth
        surfaceHeight = (self.maxCodeLength + 1 + self.maxCodeLength * VERTICAL_SPACING + 2 * VERTICAL_FIELD) * self.iconHeight
        print(surfaceWidth, surfaceHeight)
        self.surface = Surface((surfaceWidth, surfaceHeight)) # pylint: disable=E1121
        self.surface.fill(WHITE)
        self.drawTree(surfaceWidth / 2, (VERTICAL_FIELD + 0.5) * self.iconHeight, self.tree, self.maxCodeLength)
        imageSave(self.surface, fileName)

def main():
    MorseTree().saveTree('MorseTree.png')

if __name__ == '__main__':
    main()
