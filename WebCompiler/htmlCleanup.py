#! /usr/bin/env python

"""\
WebCompiler :: HTML CleanUp  v1.0

Usage: wc-html-cleanup <basePath> [--doIt]

Recursively scans for .html files and corrects the character set.
If you run it without the --doIt it demonstrates what it will do

TAKE CARE WITH THIS TOOL

"""

import os
import sys


# ref HTML encodings: 
#   http://www.chaos.org.uk/~eddy/bits/chars.html
#   http://www.danshort.com/HTMLentities/
#   http://www.w3schools.com/HTML/html_entities.as
#   http://ascii-table.com/unicode-chars.php?p=0

replaceList = [
#    ('{# <!-- #}\n{% extends "/_sadf.html" %}', '{# <!-- #}{% extends "/_sadf.html" %}'),
#    ('{# <!-- #}\n{% endblock %}\n{# --> #}', '{# <!-- #}{% endblock %}{# --> #}'),
#    ('{% block body %}\n{# --> #}', '{% block body %}{# --> #}'),
#    ('{# <!-- #}{% extends "/_sadf.html" %}\n{% block origTitle %}', '{#<!--#}{% extends "/_sadf.html" %}\n{% block origTitle %}{#-->#}'),
#    ('{% endblock %}\n{% block body %}{# --> #}', '{#<!--#}{% endblock %}\n{% block body %}{#-->#}'),
#    ('{# <!-- #}{% endblock %}{# --> #}', '{#<!--#}{% endblock %}{#-->#}'),

    ('\x85', '&hellip;'),

    ('\x91', '&lsquo;'),
    ('\x92', '&rsquo;'),
    ('\x93', '&ldquo;'),
    ('\x94', '&rdquo;'),
    ('\x95', '&bull;'),

    ('\x97', '&mdash;'),

    ('\xa0', '&nbsp;'),
    ('\xa3', '&pound;'),

    ('\xb1', '&plusmn;'),

    ('\xbc', '&frac14;'),
    ('\xbd', '&frac12;'),
    ('\xbe', '&frac34;'),

    ('{#<!--#}{% extends "/_sadf.html" %}', '{#<!--#}{% extends "/_template.html" %}'),
]

#===============================================================================
def main(argv):
    
    global replaceList
    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'h', ['help', 'doIt'])
    except getopt.GetoptError, e:
        print __doc__
        print "! Syntax error: ",e
        return -1

    doIt = False

    for n,v in optList:
        if n == '--help' or n == '-h':
            print __doc__
            return 0
        if n == '--doIt':
            doIt = True

    if len(optRemainder) != 1:
        print __doc__
        return 0
    basePath = optRemainder[0]    

    filesChanged = 0
    for root, dirs, files in os.walk(basePath, topdown=False):
        for f in files:
            if not f.endswith('.html'): continue

            fullName = os.path.join(root, f)

            sizeBefore = os.stat(fullName).st_size
            content = open(fullName, 'rt').read()
            changeList = []
            for before,after in replaceList:
                if doIt:
                    count = content.count(before)
                    if count:
                        content = content.replace(before, after)
                        changeList.append(' - Replaced %d "%s" with "%s"' % (count, before, after) )
                else:
                    maxLen = len(content)
                    pos = 0
                    snipSpan = 25
                    while True:
                        pos = content.find(before, pos)
                        if pos == -1:
                            break
                        snip = content[max(0, pos-snipSpan):min(maxLen, pos+len(before)+snipSpan)]
                        a = snipSpan
                        b = snipSpan+len(before)
                        snip = snip[:a] + '[' + snip[a:b] + ']' + snip[b:]
                        snip = snip.replace('\n', '').replace('\r', '')
                        changeList.append(' - "%s" --> "%s"' % (snip, after) )
                        pos += 1                        
                        

            if changeList:
                if doIt:
                    open(fullName, 'wt').write(content)
                sizeAfter = os.stat(fullName).st_size

                filesChanged += 1
                print '%s' % fullName
                for change in changeList:
                    print change
                if doIt:
                    if sizeBefore == sizeAfter:
                        print ' - No change in file size.'
                    elif sizeBefore > sizeAfter:
                        print ' - File is %d bytes smaller.' % (sizeBefore - sizeAfter)
                    elif sizeBefore < sizeAfter:
                        print ' - File is %d bytes bigger.' % (sizeAfter - sizeBefore)
                    else:
                        print ' - Something bad has happened! Oops.'

    print 'Done: %d files changed in "%s"' % (filesChanged, basePath)

#===============================================================================
def cli():
    sys.exit(main(sys.argv))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

#===============================================================================
# end

