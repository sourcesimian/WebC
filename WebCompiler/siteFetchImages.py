#! /usr/bin/env python

"""\
WebCompiler :: Web Site Image Fetcher  v1.0
wc-fetch-images <projectDir> [<inputDir> [<inputDir> [...]]]

Will scan images within <projectDir>/src and then look within 
<inputDir>/* for similar images

--synchronize  - ONLY DO THIS ONCE YOU HAVE A COMPLETE COPY OF
                 YOUR 'src' FOLDER AND YOU ARE SATISFIED WITH
                 YOUR IMAGE SELECTIONS

                 *** If something breaks this is not my fault, OK ***
                 *** Using my tool is just one option ***
"""

import os
import re
import sys
import math
import time
import glob
import pickle
import shutil

import Image
import ImageEnhance

import time

#------------------------------------------------------------------------------
try:
    import ImageTk
except ImportError, e:
    print e
    print """\
    - Ubuntu: this can be done by running: $ sudo apt-get install python-imaging-tk
    - Windows: ... uhm, pehaps it will just work? Or perhaps try googling.
    """
    sys.exit(-1)

#------------------------------------------------------------------------------
try:
    import Tkinter as tk
    import tkMessageBox
except ImportError, e:
    print e
    print """\
    - Ubuntu: this can be done by running: $ sudo apt-get install python-tk
    - Windows: google the ActivePython distribution it contains these libraries
    """
    sys.exit(-1)

srcDir = 'src'
dstDir = 'root'

#==============================================================================
class TkImageDisplay(tk.Canvas):
    
    def __init__(self, master, *kw, **options):
        self._frame = tk.Frame(master, bd=5)

        self._label = tk.Label(self._frame)
        self._label.pack(side=tk.TOP)
        self._label1 = tk.Label(self._frame)
        self._label1.pack(side=tk.TOP)
        self._canvas = tk.Canvas(self._frame, bd=0)
        self._canvas.pack(side=tk.TOP)
#        self._canvas.config(outline='black')
        self._selected = 'lightblue'
        self._notSelected = 'grey'

        self._canvas.config(borderwidth=1)

        self._button1 = None
        self._button3 = None
        self._motion = None
        self._zoom = 1
        self._textMinZoom = 0.15
        self._ctx = None

        self._path = None
        
        keys = options.keys()
        for o in keys:
            if o == 'image':
                self._path = options[o]
                del options[o]
            if o == 'zoom':
                self._zoom = options[o]
                del options[o]
            if o == 'button1':
                self._button1 = options[o]
                del options[o]
            if o == 'button3':
                self._button3 = options[o]
                del options[o]
            if o == 'motion':
                self._motion = options[o]
                del options[o]
            if o == 'ctx':
                self._ctx = options[o]
                del options[o]
            if o == 'selected':
                self._selected = options[o]
                del options[o]
            if o == 'bg':
                self._notSelected = options[o]
                del options[o]

        self._canvas.bind("<Button-1>", self._onButton1)
        self._canvas.bind("<Button-3>", self._onButton3)
        self._canvas.bind("<Motion>", self._onMotion)


        sPath = self._path.split(os.sep)
        dispPathList = ['']
        tmp = ''
        for s in sPath:
            if len(dispPathList[-1]) > 40:
                dispPathList.append('')
            if not s:
                dispPathList[-1] += os.sep
            else:
                if dispPathList[-1] and dispPathList[-1][-1] != os.sep:
                    dispPathList[-1] += os.sep
                dispPathList[-1] += s
        dispPath = (os.sep+'...\n...'+os.sep).join(dispPathList)

        if not os.path.isfile(self._path):
            box = (0, 0, 100, 100)
            self._canvas.config(width=100, height=100)
            self._canvas.create_rectangle(box, fill='black', outline='black') 
            if self._zoom > self._textMinZoom:
                self._label.config(text='NOT FOUND: %s' % (dispPath))
        else:
            try:
                stat = os.stat(self._path)
                im = Image.open(self._path)
                imS = im.resize((int(im.size[0]*self._zoom), int(im.size[1]*self._zoom)), Image.ANTIALIAS)

                self._canvas.config(width=imS.size[0], height=imS.size[1])
                self._tkim = ImageTk.PhotoImage(imS)
                self._canvas.create_image(1,1, anchor=tk.NW, state=tk.NORMAL, image=self._tkim)

                timeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
                self._label.config(text='%s' % (dispPath))
                self._label1.config(text='(%d,%d) [%d] %s %s' % (im.size[0], im.size[1], stat.st_size, im.format, timeString))
            except IOError, e:
                box = (0, 0, 100, 100)
                self._canvas.config(width=100, height=100)
                self._canvas.create_rectangle(box, fill='red', outline='red') 
                if self._zoom > self._textMinZoom:
                    self._label.config(text='BAD IMAGE: %s' % (dispPath))
                

    #--------------------------------------------------------------------------
    def getPath(self):
        return self._path    

    #--------------------------------------------------------------------------
#    def ctx(self):
#        return self._ctx
#
#    #--------------------------------------------------------------------------
#    def setBorderColor(self, color):
#        self._frame.config(bg=color)
#
    #--------------------------------------------------------------------------
    def __del__(self):
        self._canvas.destroy()
        self._label.destroy()
        self._frame.destroy()

    #--------------------------------------------------------------------------
    def grid(self, *kw, **options):
        self._frame.grid(*kw, **options)

    #--------------------------------------------------------------------------
    def pack(self, *kw, **options):
        self._frame.pack(*kw, **options)

    #--------------------------------------------------------------------------
    def selected(self, yes):
        if yes:
            self._frame.config(bg=self._selected)
            self._label.config(bg=self._selected)
            self._label1.config(bg=self._selected)
        else:
            self._frame.config(bg=self._notSelected)
            self._label.config(bg=self._notSelected)
            self._label1.config(bg=self._notSelected)
            
    #--------------------------------------------------------------------------
#    def config(self, *kw, **options):
#        self._frame.config(*kw, **options)
#
    #--------------------------------------------------------------------------
    def destroy(self, *kw, **options):
        self._frame.destroy(*kw, **options)

    #---------------------------------------------------------------------------
    def _onButton1(self, event):
        if self._button1:
            self._button1(self, self._ctx, event)

    #--------------------------------------------------------------------------
    def _onButton3(self, event):
        if self._button3:
            self._button3(self, self._ctx, event)

    #--------------------------------------------------------------------------
    def _onMotion(self, event):
        if self._motion:
            self._motion(self, self._ctx, event)
       
#===============================================================================
def getAttrib(tag, attrib):

    srcAttr = re.compile('%s=([\'"]{0,1})(.*?)\\1' % attrib, re.IGNORECASE | re.MULTILINE | re.DOTALL)

    res = srcAttr.search(tag)

    if not res:
        writeErr('TAG %s %s\n' % (attrib,tag))
        return None

    attrib = res.group(2)
    attrib = attrib.strip()
    if not attrib:
        return None
    return attrib

#===============================================================================
def getImgTags(fileName):

    src = open(fileName, 'rt').read()
    aTag = re.compile('<\s*img.*?>', re.IGNORECASE | re.MULTILINE | re.DOTALL)

    res = aTag.findall(src)

    return res


#===============================================================================
def getImgRefs(fileName):

    tags = getImgTags(fileName)
    res = {}
    for tag in tags:
        attrib = getAttrib(tag, 'src')
        if attrib:
            attrib = attrib.strip()
            if not attrib: continue
            res[attrib] = {'tag': tag}
        else:
#            sys.stderr.write('SKIP %s\n' % tag)
            pass

    return res

#==============================================================================
class ImageFetcher:
    def __init__(self, srcRoot, inputRoots = []):

        self._imageTypes = ['.jpg', '.gif', '.png']
        self._imageZoom = 40
        self._imageZoomStep = 15
        self._siteTid = None
        self._inputTids = []

        if srcRoot[-1] == os.sep:
            srcRoot = srcRoot[:-1]

        self._srcRoot = srcRoot
        self._configFile = self._realPath('_imageFetcher.cfg')

        self._inputRoots = inputRoots

    #--------------------------------------------------------------------------
    def _realPath(self, src):
        return os.path.join(self._srcRoot, src)

    #--------------------------------------------------------------------------
    def synchronize(self, doIt=False):
        print 'ImageFetcher: %s' % self._srcRoot 
        
        warning = """\

  *** ARE YOU SURE YOU WANT TO DO THIS??? ***

  This process will modify images in your 'src' folder.
  It may or may not do this correctly!

  MAKE A COPY OF YOUR 'src' FOLDER BEFORE PROCEEDING

  I give you no guarantees. You are reminded that there are other ways,
  all be them slower, in which you could have done this process.

  You will need to use the --yes switch to actually make this tool run.
  Otherwise it will only simulate

  Please confirm your intentions to procees by typing: 'I do' below"""
        print warning
        if doIt: print "\n  !!!!!! THIS IS NOT A SIMULATION !!!!!\n"

#        answer = 'I do'
        answer = raw_input("> ")

        if answer != 'I do':
            print 'Ok, why don\'t you go %s too' % answer
            return
        print 
        self._loadConfig()

        for key in self._config:
            cfg = self._config[key]

            dst = cfg['path']

            if cfg['save'] != True: continue
            src = cfg['input']

            if not src: continue
            if src == 'KEEP': continue

            print '%s <- %s' % (dst, src)
            srcStat = os.stat(src)
            dstStat = os.stat(self._realPath(dst))

            if srcStat.st_size == dstStat.st_size and srcStat.st_mtime == dstStat.st_mtime:
                continue
            if doIt:
                shutil.copy(src, self._realPath(dst))

    #--------------------------------------------------------------------------
    def run(self, startName=None, startIndex=0):

        print 'ImageFetcher: %s' % self._srcRoot 

        # Scan HTML files and get all IMG refs
        imageRefDict = {}
        for root, dirs, files in os.walk(self._srcRoot, topdown=False):
            for f in files:
                if f.startswith('_'):   continue
                if not os.path.splitext(f)[1].lower() in ['.html']: continue
                path = os.path.join(root, f)

                key = f.lower()                
                #key = os.path.splitext(f)[0]

                if key.startswith('.'): continue
                refs = getImgRefs(path)
                
                if not key in imageRefDict:
                    imageRefDict[key] = {}
                for ref in refs:
                    if ref.startswith('.'): continue
                    if ref.startswith('http:'): continue
                    if ref.endswith('/'): continue
                    if not ref: continue
                    imageRefDict[key][ref] = 0


        # Load image list
        imageDict = {}
        for root, dirs, files in os.walk(self._srcRoot, topdown=False):
            for f in files:
                if f.startswith('_'):   continue
                if not os.path.splitext(f)[1].lower() in self._imageTypes: continue
                path = os.path.join(root, f)

                key = f.lower()                
                #key = os.path.splitext(f)[0]

                if key in imageDict:
                    print '! duplicate: %s <--> %s' % (path, self._realPath(imageDict[key]))
                else:
                    imageDict[key] = path[len(self._srcRoot)+1:]


        
#        imageDict = {}  ## debug


        # Add bad image refs from scanning HTML files        
        for html in imageRefDict:
            for path in imageRefDict[html]:
                key = os.path.split(path)[1].lower()
                if not key: continue
                if not key in imageDict:
                    print '- will search for unsatisfied img ref too: %s' % path
#                    value = path[len(self._srcRoot)+1:]
                    value = path    # debug
                    if value:
                        if value.startswith('.'): continue
                        imageDict[key] = value
#                    else:
#                        print 'DEBUG %s' % key

        # Get completed list of images and sort 
        self._imageList = imageDict.values()
        self._imageList.sort()

        self._imageIndex = startIndex
        if self._imageIndex: self._imageIndex -= 1

        print '- image count: %d' % len(self._imageList)

        if startName:
            for i in xrange(len(self._imageList)):
                if os.path.split(self._imageList[i])[1] == os.path.split(startName)[1]:
                    self._imageIndex = i
                    break
        print '- starting with: %s' % self._imageList[self._imageIndex]

        # Load input lists
        self._inputDict = {}
        for inputRoot in self._inputRoots:
            print 'Scanning %s ...' % inputRoot
            for root, dirs, files in os.walk(inputRoot, topdown=False):
                if root.find('RECYCLER') != -1: continue

                for f in files:
                    if not os.path.splitext(f)[1].lower() in self._imageTypes: continue
                    path = os.path.join(root, f)

                    key = os.path.split(f)[1].lower()
                    #key = os.path.splitext(os.path.split(f)[1])[0].lower()

                    if not key in self._inputDict:
                        self._inputDict[key] = []

                    stat = os.stat(path)
                    desc = {'path':path, 'size': stat.st_size, 'time':stat.st_mtime}
                    self._inputDict[key].append(desc)

        self._loadConfig()

        self._initGui()
        self._showSiteImage()
        self._m.mainloop()

    #--------------------------------------------------------------------------
    def _getCurrentCfg(self):

        path = self._imageList[self._imageIndex]
#        print 'DEBUG "%s"' % path
        if not path in self._config:
#            im = Image.open(self._realPath(path))
            key = os.path.split(path)[1].lower()

            self._config[path] = {'path': path,
                                  'key':  key,
                                  'save': False,
                                  'input': None,
                                  'time': None}
        return self._config[path]

    #--------------------------------------------------------------------------
    def _initGui(self):

        self._m = tk.Tk()
        self._m.geometry('+%d+%d' % (50,50))
        self._m.protocol("WM_DELETE_WINDOW", self._onQuit)

        self._m.title('Image Fetcher')

        frame = tk.Frame(self._m)
        frame.grid(row=0, column=0, columnspan=2, sticky=tk.N+tk.W+tk.S+tk.E)
        tk.Button(frame, text='Help', command=self._onHelp).pack(side=tk.LEFT)
        tk.Label(frame, text=' ').pack(side=tk.LEFT)
        tk.Button(frame, text='   <--   ', command=self._onPrev).pack(side=tk.LEFT)
        tk.Button(frame, text='   -->   ', command=self._onNext).pack(side=tk.LEFT)
        tk.Button(frame, text='   -->0   ', command=self._onNextNew).pack(side=tk.LEFT)
        tk.Label(frame, text=' ').pack(side=tk.LEFT)
        tk.Button(frame, text='smaller', command=self._onSmaller).pack(side=tk.LEFT)
        tk.Button(frame, text='BIGGER', command=self._onBigger).pack(side=tk.LEFT)
        tk.Label(frame, text=' ').pack(side=tk.LEFT)
        tk.Button(frame, text='Save', command=self._onSave).pack(side=tk.LEFT)
        tk.Label(frame, text=' ').pack(side=tk.LEFT)
        tk.Button(frame, text='Clear All', command=self._onClearAll).pack(side=tk.LEFT)
        tk.Label(frame, text=' ').pack(side=tk.LEFT)
        tk.Button(frame, text='Close', command=self._onQuit).pack(side=tk.LEFT)

        # Checks
        frameC = tk.Frame(self._m)
        frameC.grid(row=1, column=0, columnspan=2, sticky=tk.N+tk.W+tk.S+tk.E)
        self._autoNext = tk.IntVar()
        self._autoNext.set(1)
        tk.Checkbutton(frameC, text="Auto Next", variable=self._autoNext).pack(side=tk.LEFT)

        self._autoNextNew = tk.IntVar()
        self._autoNextNew.set(0)
        tk.Checkbutton(frameC, text="New Only", variable=self._autoNextNew).pack(side=tk.LEFT)

        self._labelNeedSave = tk.Label(frameC, text='CHANGED', bg='grey')
        self._labelNeedSave.pack(side=tk.LEFT)

        tk.Label(self._m, text='Right click to inspect image. Press Esc to return.').grid(row=2, column=0, columnspan=2, sticky=tk.W)

        self._labelStatus = tk.StringVar()
        tk.Label(self._m, textvariable=self._labelStatus).grid(row=3, column=0, columnspan=2, sticky=tk.W)
        self._labelStatus.set('Status')

        self._imgRow = 4

    #--------------------------------------------------------------------------
    def _loadConfig(self):
        self._needSave = False

        if not os.path.isfile(self._configFile):
            self._config = {}
            return
        fh = open(self._configFile,'rt')
        self._config = pickle.load(fh)
        print '- loaded config file: %s' % (self._configFile)

    #--------------------------------------------------------------------------
    def _saveConfig(self, backup=False):
        config = {}

        for f in self._config:
            if self._config[f]['save'] == True:
                config[f] = self._config[f]

        fn = self._configFile
        if backup:
            fn += '.bak'

        fh = open(fn,'wt')
        pickle.dump(config, fh)
        if not backup:
            self._needSave = False
            print '- saved configfile: %s' % (fn)
        else:
            print '- backed-up config file: %s' % (fn)

        self._updateFlags()

    #--------------------------------------------------------------------------
    def _onClearAll(self):
        print 'Quit'
        count = 0
        for cfg in self._config:
            if self._config[cfg]['save']:
                count +=1

        if count==0 or tkMessageBox.askyesno("Clear All", "This will clear ALL %d\nof your settings.\n\nIs this what you want to do?" % count, icon=tkMessageBox.WARNING):
            self._config = {}
            self._showSiteImage()
            self._needSave = True
            self._updateFlags()

    #--------------------------------------------------------------------------
    def _onHelp(self):
        raise 'remove'
        tkMessageBox.showinfo("ImageFetcher: Help", helpText)

    #--------------------------------------------------------------------------
    def _onQuit(self):
        print 'Quit'
        if self._needSave:
            if tkMessageBox.askyesno("Quit", "You have made changes that\nhave not yet been saved.\n\nDo you wish to discard them?"):
                self._m.quit()
        else:
            self._m.quit()

    #--------------------------------------------------------------------------
    def _onSave(self):
        print 'Save'
        self._saveConfig()

    #--------------------------------------------------------------------------
    def _onPrev(self):
        self._goPrevImage()
        self._showSiteImage()

    #--------------------------------------------------------------------------
    def _onNext(self):
        self._goNextImage()
        self._showSiteImage()

    #--------------------------------------------------------------------------
    def _onNextNew(self):
        while True:
            if not self._goNextImage():
                break
            cfg = self._getCurrentCfg()
            if cfg['input'] == None:
                break

        self._showSiteImage()

    #--------------------------------------------------------------------------
    def _onSmaller(self):
        self._imageZoom -= self._imageZoomStep
        if self._imageZoom <= 4:
            self._imageZoom += self._imageZoomStep
        self._showSiteImage()

    #--------------------------------------------------------------------------
    def _onBigger(self):
        self._imageZoom += self._imageZoomStep
        self._showSiteImage()

    #--------------------------------------------------------------------------
    def _goPrevImage(self):
        if self._imageIndex >= 1:
            self._imageIndex -= 1
            return True
        self._imageIndex = len(self._imageList)-1
        return False

    #--------------------------------------------------------------------------
    def _goNextImage(self):
        if self._imageIndex < (len(self._imageList)-1):
            self._imageIndex += 1
            return True
        self._imageIndex = 0
        return False

    #--------------------------------------------------------------------------
    def _onSelectInput(self):
        raise 'remove'
        cfg = self._getCurrentCfg()

        if cfg['input'] != inp['path']:
            cfg['input'] = inp['path']
            cfg['save'] = True
            self._needSave = True

            self._updateFlags()

        self._autoNext()

    #--------------------------------------------------------------------------
    def _showSiteImage(self):

        for tid in self._inputTids:
            tid.destroy()
        if self._siteTid:
            self._siteTid.destroy()
        self._siteTid = None
        self._inputTids = []

        cfg = self._getCurrentCfg()
        print '- show image: %s' % cfg['path']

        ## Input Images
        frame = tk.Frame(self._m)
        frame.grid(row=self._imgRow, column=0, columnspan=2, sticky=tk.N+tk.W+tk.S+tk.E)

        self._siteTid = TkImageDisplay(frame, button1=self._keep, button3=self._viewImage, image=self._realPath(cfg['path']), zoom=self._imageZoom/100.0, selected='lightblue', bg='darkgrey') 
        self._siteTid.grid(row=0, column=0, sticky=tk.N+tk.W+tk.S+tk.E)


        inputList = self._inputDict[cfg['key']]
        inputList.sort(lambda a,b: cmp(a['time'], b['time']))

        row = 0
        column = 1
        rowMax = math.sqrt(len(inputList)+1)
        rowMax = math.ceil(rowMax)

        for i in xrange(len(inputList)):
            inp = inputList[i]
            print '  * alternative: %s' % (inp['path'])

            tid = TkImageDisplay(frame, button1=self._selectInput, button3=self._viewImage, image=inp['path'], zoom=self._imageZoom/100.0, selected='orange')
            tid.grid(row=row, column=column, sticky=tk.N+tk.W+tk.S+tk.E)
            self._inputTids.append(tid)

            column += 1
            if column == rowMax:
                row += 1
                column = 0

        cfg = self._getCurrentCfg()

        self._updateFlags()

    #--------------------------------------------------------------------------
    def _updateFlags(self):

        msg = '[%d of %d] {%d} Zoom: %d%%' % (self._imageIndex+1, len(self._imageList), len(self._inputTids), self._imageZoom)
        self._labelStatus.set(msg)        

        self._labelNeedSave.config(bg='grey')
        if self._needSave:
            self._labelNeedSave.config(bg='orange')

        cfg = self._getCurrentCfg()

        self._siteTid.selected(cfg['input'] == 'KEEP') 

        for x in self._inputTids:
            y = x.getPath() == cfg['input']
            x.selected(y)

    #--------------------------------------------------------------------------
    def _autoProgress(self):
        if self._autoNext.get():
            if self._autoNextNew.get():
                self._onNextNew()
                return
            self._onNext()

    #--------------------------------------------------------------------------
    def _keep(self, tid, ctx, event):

        cfg = self._getCurrentCfg()
        cfg['input'] = 'KEEP'
        cfg['save'] = True
        print '- selected: %s' % cfg['input']

        self._needSave = True
        self._saveConfig(backup=True)

        self._updateFlags()
        self._autoProgress()

    #--------------------------------------------------------------------------
    def _selectInput(self, tid, ctx, event):

        cfg = self._getCurrentCfg()
        cfg['input'] = tid.getPath()
        cfg['save'] = True
        print '- selected: %s' % cfg['input']

        self._needSave = True
        self._saveConfig(backup=True)

        self._updateFlags()
        self._autoProgress()

    #--------------------------------------------------------------------------
    def _viewImage(self, tid, ctx, event):
        path = tid.getPath()
        print '- view: %s' % path
        os.system('feh -F "%s" &' % path)

    #--------------------------------------------------------------------------
    def _onImageClick(self, event):
        raise 'remove'
        cfg = self._getCurrentCfg()

        cfg['save'] = True
        self._needSave = True
        
    #--------------------------------------------------------------------------
    def _onImageLeave(self, event):
        raise 'remove'
        self._labelCanvasSite.delete(('locate'))



#==============================================================================
def main(argv):
    if len(argv) == 1:
        print __doc__
        return -1

    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'h', ['help', 'start=', 'index=', 'synchronize', 'yes'])
    except getopt.GetoptError, e:
        print __doc__
        print "! Syntax error: ",e
        return -1

    startName = None
    startIndex = 0
    synchronize = False
    yes = False

    for n,v in optList:
        if n == '--help' or n == '-h':
            print __doc__
            return 0
        if n == '--start':
            startName = v       
        if n == '--index':
            startIndex = int(v)
        if n == '--synchronize':
            synchronize = True
        if n == '--yes':
            yes = True

    if len(optRemainder) < 1:
        print "! Need to specify a project directory"
        print __doc__
        return -1
    projectDir = optRemainder[0]

    srcRoot = os.path.join(projectDir,srcDir)
    dstRoot = os.path.join(projectDir,dstDir)

    if synchronize:
        imageFetcher = ImageFetcher(srcRoot)
        imageFetcher.synchronize(yes)
        return

    if len(optRemainder) < 2:
        print "! Need to specify an input source too"
        print __doc__
        return -1

    inputRoots = optRemainder[1:]
    
    imageFetcher = ImageFetcher(srcRoot, inputRoots)
    imageFetcher.run(startName=startName, startIndex=startIndex)

#==============================================================================
def cli():
    sys.exit(main(sys.argv))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

#==============================================================================
# end

