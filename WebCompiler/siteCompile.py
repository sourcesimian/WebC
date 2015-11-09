#!/usr/bin/env python

"""\
WebCompiler :: Site Compiler  v1.0
- A utility to compile your web site to a suitable form for publication.
  Including aspects such as templating, image watermarking and resizing.
 
USAGE: wc-compile <projectDir> [<switches>]

Switches:
    --clean     Delete entire root directory first.
    --all       Force all
    --allHtml   Force all HTML files

This utility will work with all files found in: <projectDir>/src
And will output the new rendered site to: <projectDir>/root
"""

#===============================================================================
import os
import sys
import shutil
import hashlib
import pickle
from PIL import Image

import time

try:
    import jinja2
except ImportError:
    print  """\

    You will need to first install Jinja2 for this tool to work:

    * Install on Linux by running the following in a Terminal:
      $ sudo apt-get install python-jinja2

    * Install on Windows by fetching the installer from:
      http://jinja.pocoo.org/2/
    """
    sys.exit(-1)

srcDir = 'src'
dstDir = 'root'

#===============================================================================
def printUnicodeErrors(content):
    while content:
        try:
            content.encode('ascii')
            content = None
        except (UnicodeDecodeError, UnicodeEncodeError), e:
            maxLen = len(content)
            snip = content[max(e.start-30, 0): min(e.end+30, maxLen)]
            print ' - %s' % repr(snip)[2:-1]
            content = content[e.end:]

#===============================================================================
def printUnicodeEncodeErrors(content):
    while content:
        try:
            content.encode('ascii')
            content = None
        except UnicodeDecodeError, e:
            maxLen = len(content)
            snip = content[max(e.start-30, 0): min(e.end+30, maxLen)]
            print ' - %s' % repr(snip)[2:-1]
            content = content[e.end:]

#===============================================================================
def getFileMD5Hash(filename):
    if not os.path.isfile(filename):
        return None
        
    try:
        f = open(filename, 'rb')
    except:
        error('can\'t open: %s' % (filename))
        return None
    m = hashlib.md5()

    while 1:
        data = f.read(4096)
        if not data:
            break
        m.update(data)
   
    f.close()
    return m.hexdigest()
    
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

    (common,l1,l2) = commonpath(pathsplit(fromPath), pathsplit(toPath))
    p = []
    if len(l1) > 0:
        p = [ '../' * len(l1) ]
    p = p + l2
    if not p:
        return ''
    return os.path.join( *p )


#===============================================================================
class Compiler:
    def __init__(self, srcBase, dstBase, doAll=False):
        self._srcBase = srcBase
        self._dstBase = dstBase
        self._doAll = doAll
        self._processCount = 0
        self._messages = {} 

    #---------------------------------------------------------------------------
    def getSrcRoot(self):
        return self._srcBase

    #---------------------------------------------------------------------------
    def getDstRoot(self):
        return self._dstBase

    #---------------------------------------------------------------------------
    def isAll(self):
        return self._doAll

    #---------------------------------------------------------------------------
    def cleanAll(self):
        print 'Erasing the entire: %s' % self._dstBase

        def deltree(dirname):
             if os.path.exists(dirname):
                for root,dirs,files in os.walk(dirname):
                        for dir in dirs:
                                deltree(os.path.join(root,dir))
                        for file in files:
                                os.remove(os.path.join(root,file))     
                os.rmdir(dirname)

        deltree(self._dstBase)
        print

    #---------------------------------------------------------------------------
    def isEquivalentDstOld(self, src):
        srcPath = self.getSrcFilePath(src)
        dstPath = self.getDstFilePath(src)

        if not self._doAll and os.path.exists(srcPath) and os.path.exists(dstPath):
            if os.stat(srcPath).st_mtime <= os.stat(dstPath).st_mtime:
                return False

        return True

    #---------------------------------------------------------------------------
    def getDstFilePath(self, dst):
        return os.path.join(self._dstBase, dst)

    #---------------------------------------------------------------------------
    def openDstFile(self, dst, mode='wt'):
        fullPath = self.getDstFilePath(dst)
        
        dstDir = os.path.split(fullPath)[0]
        if not os.path.isdir(dstDir):
            os.makedirs(dstDir)

        return open(fullPath, mode)

    #---------------------------------------------------------------------------
    def getSrcFilePath(self, src):
        return os.path.join(self._srcBase, src)

    #---------------------------------------------------------------------------
    def openSrcFile(self, src, mode='t'):
        fullPath = self.getSrcFilePath(src)
        
        return open(fullPath, 'r'+mode)

    #---------------------------------------------------------------------------
    def process(self, src, processor):

        self._currentSrc = src
        if processor._compile(self, src):
            self._processCount += 1
        self._currentSrc = None

    #---------------------------------------------------------------------------
    def error(self, msg, line=None):
        self._logMessage('error', msg, line)

    #---------------------------------------------------------------------------
    def warning(self, msg, line=None):
        self._logMessage('warning', msg, line)

    #---------------------------------------------------------------------------
    def info(self, msg, line=None):
        self._logMessage('info', msg, line)

    #---------------------------------------------------------------------------
    def _logMessage(self, logType, msg, line):
        if not self._currentSrc:
            raise 'error method called without a current src file'

        if not self._currentSrc in self._messages:
            self._messages[self._currentSrc] = []

        desc = {'type':logType, 'msg': msg, 'line':line}
        self._messages[self._currentSrc].append(desc)

    #---------------------------------------------------------------------------
    def getErrorCount(self):
        return self._countMessages('error')

    #---------------------------------------------------------------------------
    def getWarningCount(self):
        return self._countMessages('warning')

    #---------------------------------------------------------------------------
    def _countMessages(self, msgType):
        count = 0
        for src in self._messages:
            for desc in self._messages[src]:
                if desc['type'] == msgType:
                    count += 1
        return count

    #---------------------------------------------------------------------------
    def printMessages(self):
        keys = self._messages.keys()
        keys.sort()

        for src in keys:
            for desc in self._messages[src]:
                if desc['line']:
                    print '%s(%d) %s: %s' % (src, desc['line'], desc['type'], desc['msg'])
                else:
                    print '%s(#) %s: %s' % (src, desc['type'], desc['msg'])

    #---------------------------------------------------------------------------
    def getProcessCount(self):
        return self._processCount

#===============================================================================
class ProcessBase():
    def __init__(self, compiler):
        self._compiler = compiler

    #---------------------------------------------------------------------------
    def __call__(self, src):
        self._compiler._compile(self, src)


#===============================================================================
class CopyProcess(ProcessBase):
    def __init__(self, compiler):
        ProcessBase.__init__(self, compiler)

    #---------------------------------------------------------------------------
    def __del__(self):
        pass

    #---------------------------------------------------------------------------
    def _compile(self, compiler, src):

#        if not compiler.isAll():
        if not compiler.isEquivalentDstOld(src):
            return False

        srcPath = compiler.getSrcFilePath(src)
        dstPath = compiler.getDstFilePath(src)
        dstDir  = os.path.split(dstPath)[0]

        #      123456789012
        print ' Copy:      %s -> %s' % (srcPath, dstPath)

        if not os.path.isdir(dstDir):
            os.makedirs(dstDir)

        shutil.copy(srcPath, dstPath)
        return True

#===============================================================================
class WatermarkProcess(ProcessBase):
    def __init__(self, compiler):
        ProcessBase.__init__(self, compiler)

        srcRoot = compiler.getSrcRoot()
        fh = open(os.path.join(srcRoot, '_watermark/watermark.cfg'), 'rt')
        self._config = pickle.load(fh)

    #---------------------------------------------------------------------------
    def __del__(self):
        pass

    #---------------------------------------------------------------------------
    def _compile(self, compiler, src):

        srcPath = compiler.getSrcFilePath(src)
        dstPath = compiler.getDstFilePath(src)
        dstDir  = os.path.split(dstPath)[0]

        if not os.path.isdir(dstDir):
            os.makedirs(dstDir)

        if src in self._config and self._config[src]['wm']:
            cfg = self._config[src]

            markPath = compiler.getSrcFilePath(cfg['wm'])

            dstTime = 0
            if os.path.isfile(dstPath):
                dstTime = os.stat(dstPath).st_mtime
            srcTime = os.stat(srcPath).st_mtime

            if not os.path.isfile(markPath):
                compiler.error('Watermark image "%s" not found for "%s"' % (markPath, srcPath))
                return False

            markTime = os.stat(markPath).st_mtime
            if not compiler.isAll():
                if dstTime > self._config[src]['time'] and dstTime > srcTime and dstTime > markTime:
                    return False

            opacity = 1
            im = Image.open(srcPath)
            if im.size[0] != cfg['size'][0] or im.size[1] != cfg['size'][1]:
                compiler.error('Image size changed since watermarking %s %s' % (str(im.size), str(cfg['size'])))
                return False
#            print im.info

            #      123456789012
            print ' Watermark: %s -> %s' % (srcPath, dstPath)

            # Resize if bounding box
            if cfg['box']:
                w = im.size[0]
                h = im.size[1]
                ratio = float(cfg['box']) / float(max(w, h))
                w = int(w*ratio)
                h = int(h*ratio)
                im = im.resize((w, h), Image.ANTIALIAS)

            mark = Image.open(markPath)
            imMark = self._watermark(im, mark, (cfg['wmX'], cfg['wmY']), opacity)

            option = {
                'progression':True,
                'quality':95,
                'optimize':True,
            }
            for key in im.info:
                option[key] = im.info[key]
        
            if 'transparency' in im.info:
                imMark.save(dstPath, format=im.format, option=option, transparency=im.info['transparency'])
            else:
                imMark.save(dstPath, format=im.format, option=option)

        else:
            if not compiler.isEquivalentDstOld(src):
                return False

            #      123456789012
            print ' Copy (w):  %s -> %s' % (srcPath, dstPath)
            shutil.copy(srcPath, dstPath)
        
        return True

    #---------------------------------------------------------------------------
    def _watermark(self, im, mark, position, opacity=1):
        """Adds a watermark to an image."""
        if opacity < 1:
            mark = self._reduce_opacity(mark, opacity)
        if im.mode != 'RGBA':
            im = im.convert('RGBA', palette=Image.ADAPTIVE)
#        if mark.mode != 'RGBA':
#            mark = mark.convert('RGBA')

        # create a transparent layer the size of the image and draw the
        # watermark in that layer.
        layer = Image.new('RGBA', im.size, (0,0,0,0))
        if position == 'tile':
            for y in range(0, im.size[1], mark.size[1]):
                for x in range(0, im.size[0], mark.size[0]):
                    layer.paste(mark, (x, y))
        elif position == 'scale':
            # scale, but preserve the aspect ratio
            ratio = min(
                float(im.size[0]) / mark.size[0], float(im.size[1]) / mark.size[1])
            w = int(mark.size[0] * ratio)
            h = int(mark.size[1] * ratio)
            mark = mark.resize((w, h))
            layer.paste(mark, ((im.size[0] - w) / 2, (im.size[1] - h) / 2))
        else:
            layer.paste(mark, position)
        # composite the watermark with the layer
        return Image.composite(layer, im, layer)


    #---------------------------------------------------------------------------
    def _reduce_opacity(self, im, opacity):
        """Returns an image with reduced opacity."""
        assert opacity >= 0 and opacity <= 1
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        else:
            im = im.copy()
        alpha = im.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        im.putalpha(alpha)
        return im

    #---------------------------------------------------------------------------
    def _imprint(self, im, inputtext, font=None, color=None, opacity=.6, margin=(30,30)):
        """
        imprints a PIL image with the indicated text in lower-right corner
        """
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        textlayer = Image.new("RGBA", im.size, (0,0,0,0))
        textdraw = ImageDraw.Draw(textlayer)
        textsize = textdraw.textsize(inputtext, font=font)
        textpos = [im.size[i]-textsize[i]-margin[i] for i in [0,1]]
        textdraw.text(textpos, inputtext, font=font, fill=color)
        if opacity != 1:
            textlayer = reduce_opacity(textlayer,opacity)
        return Image.composite(textlayer, im, textlayer)

    #---------------------------------------------------------------------------
    def _getFileDate(self, file):
        """
        Returns the date associated with a file.
        For JPEG files, it will use the EXIF data, if available
        """
        try:
            import EXIF
            # EXIF.py from http://home.cfl.rr.com/genecash/digital_camera.html
            f = open(file, "rb")
            tags = EXIF.process_file(f)
            f.close()
            return str(tags['Image DateTime'])
        except (KeyError, ImportError):
            # EXIF.py not installed or no EXIF date available
            import os.path, time
            return time.ctime(os.path.getmtime(file))


#===============================================================================
class TemplateProcess(ProcessBase):
    def __init__(self, compiler):
        ProcessBase.__init__(self, compiler)

        self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(self._compiler.getSrcRoot()))
        self._env.globals['__root__'] = compiler.getSrcRoot()


    #---------------------------------------------------------------------------
    def __del__(self):
        pass

    #---------------------------------------------------------------------------
    def _compile(self, compiler, src):

#        if not compiler.isAll():
        if not compiler.isEquivalentDstOld(src):
            return False
        
        srcPath = compiler.getSrcFilePath(src)
        dstPath = compiler.getDstFilePath(src)

        #      123456789012
        print ' Template:  %s -> %s' % (srcPath, dstPath)

        try:
            tmpl = self._env.get_template(src.replace('\\', '/'))
        except UnicodeDecodeError, e:
            print '! Error reading: "%s"' % (srcPath)
            print '! %s' % e
            printUnicodeErrors(compiler.openSrcFile(src).read())
            sys.exit(-2)

        renderDict = {}

        self._env.globals['__file__'] = srcPath
        self._env.globals['__rootRel__'] = relativePath(os.path.split(srcPath)[0], compiler.getSrcRoot())

        try:        
            html = tmpl.render(renderDict)
        except jinja2.TemplateNotFound, e:
            print '! An error has occured reading "%s"' % (srcPath)
            print '  - Template "%s" was not found' % e
            print
            sys.exit(-3)
            

        f = compiler.openDstFile(src, 'wb')
        try:
            f.write(html)
        except UnicodeEncodeError, e:
            print '! Error writing "%s"' % (src)
            print '! %s' % e
            printUnicodeErrors(html)
            exit(-4)
        f.close()

        return True

#===============================================================================
def getFiles(basePath):

    fileDict = {}

    if basePath.endswith(os.sep):
        basePath = basePath[:-1]

    for root, dirs, files in os.walk(basePath, topdown=False):
        for f in files:
#            if f.startswith('_'):   continue
            if f.endswith('~'):     continue
            if f.endswith('.tmp'):  continue
            if f.endswith('.bak'):  continue

            fullName = os.path.join(root, f)
            fullName = fullName[len(basePath)+1:]

            skip = False
            for level in os.path.split(fullName):
                if level.startswith('_'):
                    skip = True
                    break
            if skip:
                #print 'DEBUG skipping %s' % fullName
                continue

            ext = os.path.splitext(f)[1]
            ext = ext.lower()
            if ext == '.htm': ext = '.html'

            fileDict[fullName] = {'type': ext}

    return fileDict

#===============================================================================
def main(argv):

    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'hca', ['help', 'clean', 'all', 'allHtml'])
    except getopt.GetoptError, e:
        print __doc__
        print "! Syntax error: ",e
        return -1

    doClean = False
    doAll = False
    doAllHtml = False

    for n,v in optList:
        if n == '--help' or n == '-h':
            print __doc__
            return 0
        if n == '--clean' or n == '-c':
            doClean = True
        if n == '--all' or n == '-a':
            doAll = True
        if n == '--allHtml':
            doAllHtml = True

    if len(optRemainder) != 1:
        print __doc__
        print "! Need to specify a project directory"
        return -1
    projectDir = optRemainder[0]

    srcRoot = os.path.join(projectDir,srcDir)
    dstRoot = os.path.join(projectDir,dstDir)

    fileDict = getFiles(srcRoot)

    if doAllHtml:
        doAll = True
    compiler = Compiler(srcRoot, dstRoot, doAll=doAll)

    if doClean:
        compiler.cleanAll()

    templateProcess = TemplateProcess(compiler)
    copyProcess = CopyProcess(compiler)
    watermarkProcess = WatermarkProcess(compiler)

    for f in fileDict:

        if fileDict[f]['type'] in ['.html', '.php']:
            compiler.process(f, templateProcess)

        if doAllHtml: continue

        if fileDict[f]['type'] in ['.gif', '.jpg', '.png']:
            compiler.process(f, watermarkProcess)
        else:
            compiler.process(f, copyProcess)

    print '%d files processed' % compiler.getProcessCount()

    print
    compiler.printMessages()
    print 'Done %d files processed (%d errors, %d warnings)' % (compiler.getProcessCount(), compiler.getErrorCount(), compiler.getWarningCount())

#===============================================================================
def cli():
    sys.exit(main(sys.argv))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

#===============================================================================
# end
