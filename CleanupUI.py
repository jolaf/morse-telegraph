#!/usr/bin/env python3

from os import listdir
from re import compile as reCompile

PROCESSOR = reCompile('(?is)([\t ]*(?:<hints>.*?</hints>|<property name="sizeHint">.*?</property>|<property name="geometry">.*?</property>)[\n\r]*)')

def main():
    fileNames = tuple(fileName for fileName in listdir() if fileName.lower().endswith('.ui'))
    if not fileNames:
        print("No .ui files found")
        return
    for fileName in fileNames:
        print("%s: " % fileName, end = '', flush = True)
        with open(fileName) as f:
            content = f.read()
        print("%d bytes read" % len(content), end = '', flush = True)
        (processed, n) = PROCESSOR.subn('', content)
        if not n:
            print(", no matches found, not changing")
            continue
        print(", %d matches found" % n, end = '', flush = True)
        with open(fileName, 'w') as f:
            f.write(processed)
        print(", %d bytes written, %d bytes saved" % (len(processed), len(content) - len(processed)))

if __name__ == '__main__':
    main()
