#!/usr/bin/env python

"""\
WebC - A templated web site compiler based on Jinja2      by: SourceSimian

Usage: WebC <source root dir> <publish root dir> <input list file> [options]

Options:    --help    - full help screen 
            --rootRel - expand root variables for local browsing/testing
            --all     - reparse all files
"""

help = """
Eg: WebC source/ publish/ srcFiles.lst
    where :
    ---<srcFiles.lst>---
    # JavaScript
    js/sys.js

    # CSS
    css/skin.css
    css/main.css

    # Html
    index.html
    image.php
    --------------------

Builtin Variables:
    __rootAbs__     - abs path from site root. Using --rootRel same as below
    __rootRel__     - relative path from the site root
    __file__        - source file and path as from site root
    __fileName__    - source file name
"""
#    __fileTime__    - source file time in ISO 8601

import os
import sys
import shutil
import re

importError = False

try:
    import jinja2
except ImportError:
    print  "! Jinja2 not installed"
    importError = True

try:
    if 0:
        import clevercss
except ImportError:
    print  "! CleverCSS not installed"
    importError = True

installHelp = """\
    First install easy_install from:
        http://pypi.python.org/pypi/setuptools
    On Linux this can be done by:
        $ sudo apt-get install python-setuptools

    Then install the required modules:
        $ easy_install Jinja2
    Note: on Linux prefix with 'sudo' and on Windows use a Administrator shell
    """
#        $ easy_install CleverCSS
#        $ easy_install Pygments

#===============================================================================
def relativePath(fromPath, toPath):
    def pathsplit(p, rest=[]):
        (h,t) = os.path.split(p)
        if len(h) < 1: return [t]+rest
        if len(t) < 1: return [h]+rest
        return pathsplit(h,[t]+rest)

    def commonpath(l1, l2, common=[]):
        if len(l1) < 1: return (common, l1, l2)
        if len(l2) < 1: return (common, l1, l2)
        if l1[0] != l2[0]: return (common, l1, l2)
        return commonpath(l1[1:], l2[1:], common+[l1[0]])

    def relpath(p1, p2):
        (common,l1,l2) = commonpath(pathsplit(p1), pathsplit(p2))
        p = []
        if len(l1) > 0:
            p = [ '../' * len(l1) ]
        p = p + l2
        return os.path.join( *p )

    return ''
    return relpath(fromPath, toPath)

#===============================================================================
class Pygmenter:
    def __init__(self, linenos=False):
        self._linenos = linenos
        self._cssclass = "code"
        self._fileCount = 0

    fileCount = property(lambda self: self._fileCount)

    #---------------------------------------------------------------------------
    def formatFile(self, filename):
        try:
            import pygments
        except ImportError:
            print  "! Pygments not installed"
            print  installHelp
            exit(-1)

        if not os.path.isfile(filename):
            return None

        code = open(filename, 'rb').read()

        from pygments import highlight
        from pygments.lexers import get_lexer_for_filename 
        from pygments.formatters import HtmlFormatter

        lexer = get_lexer_for_filename(filename)
        formatter = HtmlFormatter(linenos=self._linenos, cssclass=self._cssclass)
        html = highlight(code, lexer, formatter)

        self._fileCount += 1
        return html

    #---------------------------------------------------------------------------
    def getCss(self):
        from pygments.formatters import HtmlFormatter

        style = HtmlFormatter().get_style_defs('.%s' % self._cssclass)
        #style += '.%s {width: %dpx; overflow:auto;}' % (self._cssclass, self._csswidth)
        return style
     

#===============================================================================
class Compiler:
    def __init__(self, srcRoot, dstRoot):
        self._srcRoot = srcRoot
        self._dstRoot = dstRoot
        self._errorCount = 0
        self._warningCount = 0
        self._optionRootRel = False;
        self._optionAll = False;
        self._fileMessages = 0
        self._currentFile = None
        self._pygmenter = Pygmenter()
        self._pygmentCSSFile = 'code.css'

    pygmenter = property(lambda self: self._pygmenter)
    pygmentCSSFile = property (lambda self: self._pygmentCSSFile)

    srcRoot = property(lambda self: self._srcRoot)
    dstRoot = property(lambda self: self._dstRoot)

    warnings = property(lambda self: self._warningCount)
    errors = property(lambda self: self._errorCount)

    optionRootRel = property(lambda self: self._optionRootRel, lambda self, v: self._setOption('_optionRootRel', v))
    optionAll = property(lambda self: self._optionAll, lambda self, v: self._setOption('_optionAll', v))

    def _setOption(self, name, value):
        self.__dict__[name] = value

    def _writeFileTitleLine(self):
        print '[%s]' % (self._currentFile)

    def startFile(self, src):
        self._fileMessages = 0
        self._currentFile = src

    def endFile(self):
        if self._fileMessages == 0:
            self._writeFileTitleLine()

    def info(self, src, line, msg):
        self._outline(src, line, 'info', msg)
    
    def warning(self, src, line, msg):
        self._warningCount += 1
        self._outline(src, line, 'warning', msg)

    def error(self, src, line, msg):
        self._errorCount += 1
        self._outline(src, line, 'error', msg)

    def _outline(self, src, line, cat, msg):
        if self._fileMessages == 0:
            self._writeFileTitleLine()

        self._fileMessages += 1
        print '%s(%d): %s: %s' % (src, line, cat, msg)

    def getFileStat(self, fileName):
        statinfo = os.stat(fileName)
        if not statinfo:
            return {}
        return {'mtime':statinfo.st_mtime, 'size':statinfo.st_size}

    def finalise(self):
        if self._pygmenter.fileCount:
            f = open(os.path.join(self._dstRoot, self._pygmentCSSFile), 'wb')
            f.write(self._pygmenter.getCss())
            f.close()
        
#===============================================================================
class ProcessTemplate():
    def __init__(self, compiler):
        self._compiler = compiler

        self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(self._compiler.srcRoot))
        #self._env.globals['__root__'] = self._compiler.srcRoot

        print 'Source Dir: %s'  % self._compiler.srcRoot
        print 'Publish Dir: %s' % self._compiler.dstRoot

        # {% extends "_base.html" %}
        # {% import "css/_colors.css" as colors %}
        self._reExtends = re.compile('{%\s*extends\s+"(.*?)"\s*?%}', re.MULTILINE)
        self._reImport = re.compile('{%\s*import\s+"(.*?)".*%}', re.MULTILINE)

    #---------------------------------------------------------------------------
    def __del__(self):
        pass

    #---------------------------------------------------------------------------
    def _isUptoDate(src, dst):
        srcInfo = self._getFileTimeAndSize(src)
        dstinfo = self._getFileTimeAndSize(dst)

        if not dstInfo or not srcInfo:
            return False
        if dstInfo['size'] == 0:
            return False

        if srcInfo['mtime'] > dstInfo['mtime']:
            return False
        return True


    #---------------------------------------------------------------------------
    def _getTemplateMTime(self, src, incFile='', lineNo=0):
        if src.startswith('/'):
            src = src[1:]

        srcFile = os.path.join(self._compiler.srcRoot, src)

        if not os.path.isfile(srcFile):
            self._compiler.error(incFile, lineNo, 'Not found: \'%s\'' % (src))
            return 0
            
        mtime = self._compiler.getFileStat(srcFile)['mtime']

        lineNo = 0
        for line in open(srcFile, 'rb'):
            lineNo += 1
            reObj = self._reExtends.findall(line) + self._reImport.findall(line)
            for res in reObj:
                if res.startswith('/'):
                    res = res[1:]
                resFile = os.path.join(self._compiler.srcRoot, res)
                mtime = max(mtime, self._getTemplateMTime(res, src, lineNo))
            
        return mtime
        
    #---------------------------------------------------------------------------
    def process(self, src):

        src = src.replace('\\', '/')
        if not src.startswith('/'):
            src = '/' + src

        srcPath = os.path.join(self._compiler.srcRoot, src[1:]).replace(os.sep, '/')
        dstPath = os.path.join(self._compiler.dstRoot, src[1:]).replace(os.sep, '/')

        self._compiler.startFile(src)

        if os.path.isfile(dstPath):
            if self._getTemplateMTime(src) <= self._compiler.getFileStat(dstPath)['mtime']:
                if not self._compiler.optionAll:
                    return True

        try:
            tmpl = self._env.get_template(src)
        except UnicodeDecodeError, e:
            self._compiler.error(src, 0, 'An error has occured reading "%s"' % (srcPath))
            return False
        except jinja2.exceptions.TemplateSyntaxError, e:
            self._compiler.error(src, 0, e)
            return False
        except jinja2.exceptions.TemplateNotFound, e:
            self._compiler.error(src, 0, 'Source file not found: %s' % e)
            return False

        renderDict = {}

        self._env.globals['__rootRel__'] = relativePath(os.path.split(srcPath)[0], self._compiler.srcRoot)

        if self._compiler.optionRootRel:
            self._env.globals['__rootAbs__'] = self._env.globals['__rootRel__']
        else:
            self._env.globals['__rootAbs__'] = os.path.split(src)[0]

        self._env.globals['__file__'] = src
        self._env.globals['__fileName__'] = os.path.split(src)[1]

        def pygmentInclude(filename):
            html = self._compiler.pygmenter.formatFile(os.path.join(self._compiler.srcRoot, filename))
            if not html:
                return '<b>{{ missing: %s }}</b>' % filename
            return html

        def pygmentCSSInclude():
            html = '<link rel="stylesheet" href="%s%s" type="text/css" />' % (self._env.globals['__rootAbs__'], self._compiler.pygmentCSSFile)
            return html
           
        self._env.globals['pygmentInclude'] = pygmentInclude
        self._env.globals['pygmentIncludeCSS'] = pygmentCSSInclude

#        self._env.globals['__fileTime__'] = 

        try:
            html = tmpl.render(renderDict)
        except jinja2.TemplateNotFound, e:
            self._compiler.error(srcPath, 0, 'Template "%s" was not found' % e)
            return False
        except UnicodeDecodeError, e:
            self._compiler.error(srcPath, 0, 'An error has occured reading the template file: %s' % e)
            return False
        except jinja2.exceptions.TemplateSyntaxError, e:
            self._compiler.error(e.filename[len(self._compiler.srcRoot):], e.lineno, e.message)
            return False
        except jinja2.exceptions.UndefinedError, e:
            self._compiler.error(srcPath, 0, 'Undefined error: %s' % e)
            return False

        p = os.path.split(dstPath)[0]
        if not os.path.exists(p):
            os.makedirs(p)

        f = open(dstPath, 'wb')
        f.write(html)
        f.close()

        self._compiler.endFile()
        return True

#===============================================================================
def main(argv):

    optionRootRel = False
    optionAll = False
    
    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'h', ['help', 'rootRel', 'all'])
    except getopt.GetoptError, e:
        print "! Syntax error: %s" % e
        print __doc__
        return -1
    
    for n,v in optList:
        if n in ('--help','-h') :
            print __doc__ + help
            return 0
        if n in ('--rootRel',):
            optionRootRel = True;
        if n in ('--all',):
            optionAll = True;

    if len(optRemainder) != 3:
        print __doc__
        return -2

    srcRoot = optRemainder[0]
    dstRoot = optRemainder[1]
    srcListFile = optRemainder[2]

    if not os.path.isdir(srcRoot):
        print '! Not found: %s' % srcRoot
        return -3

    if not os.path.isfile(srcListFile):
        print '! Not found: %s' % srcListFile
        return -3

    srcList = open(srcListFile, 'rt').readlines()

    compiler = Compiler(srcRoot, dstRoot)
    compiler.optionAll = optionAll
    compiler.optionRootRel = optionRootRel
    processTemplate = ProcessTemplate(compiler)

    for src in srcList:
        src = src.strip()
        if not src: continue
        if src.startswith('#'): continue

        processTemplate.process(src)

    compiler.finalise()
    print '--- Done %d errors, %d warnings ---' % (compiler.errors, compiler.warnings)

    return compiler.errors


#===============================================================================
if __name__ == '__main__' or __name__ == sys.argv[0]:
    sys.exit(main(sys.argv))

#===============================================================================
# 
