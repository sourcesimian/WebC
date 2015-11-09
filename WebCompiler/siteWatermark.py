#! /usr/bin/env python

"""\
WebCompiler :: Web Site Watermarker  v1.0
- A utility to locate watermarks and resize images your web site
 
USAGE: wc-watermark <projectDir> [--start <imgPath>] [--index <imgNo>]

This utility will work with all images found in: <projectDir>/src
And will write a configuration file here: <projectDir>/src/_watermark/watermark.cfg

Watermark images can be added as an image (jpg, gif or png)with or without
a transaprency index. By placing new files here:  <projectDir>/src/_watermark
"""

import os
import sys
import glob
import pickle

from PIL import Image

import time

#------------------------------------------------------------------------------
helpText = """\
Help
1) Select a watermark image
2) Click in the image to position it
3) Right click to NOT watermark

Arrow buttons (next, previous):
 -->  next image
 -->0 next with no settings
 --># next with a setting

Check boxes:
 - Auto Next - automatically -->
 - New Only: - automatically -->0

Add watermark images here:
  <projectDir>/src/_watermark*

"""

#------------------------------------------------------------------------------
try:
    from PIL import ImageTk
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
class WaterMarker:
    def __init__(self, srcRoot):

        self._imageTypes = ['.jpg', '.gif', '.png']
        self._watermarks = []
        self._imageList = []
        self._imageIndex = -1

        self._tkimBox = None
        self._boundingBox = False
        self._boundingBoxSize = 600
        self._boundingBoxIncrement = 25
        
        if srcRoot[-1] == os.sep:
            srcRoot = srcRoot[:-1]

        self._srcRoot = srcRoot
        self._configFile = self._realPath('_watermark/watermark.cfg')

    #--------------------------------------------------------------------------
    def _realPath(self, src):
        return os.path.join(self._srcRoot, src)

    #--------------------------------------------------------------------------
    def run(self, startName=None, startIndex=0):

        print 'WaterMarker: %s' % self._srcRoot 
        self._loadConfig()

        # Load image list
        imageDict = {}
        for root, dirs, files in os.walk(self._srcRoot, topdown=False):
            for f in files:
                if f.startswith('_'):   continue
                if not os.path.splitext(f)[1].lower() in self._imageTypes: continue
                path = os.path.join(root, f)

                if f in imageDict:
                    print '! duplicate: %s <--> %s' % (path, self._realPath(imageDict[f]))
                else:
                    imageDict[f] = path[len(self._srcRoot)+1:]

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

        # Get watermark list
        self._watermarks = []
        globList = glob.glob(self._realPath('_watermark/*'))
        for path in globList:
            if not os.path.splitext(path)[1].lower() in self._imageTypes: continue
            if os.path.split(path)[1].startswith('_'): continue
            self._watermarks.append(path[len(self._srcRoot)+1:])
            print '- watermark: %s' % path[len(self._srcRoot)+1:]

        if not self._watermarks:
            print '! No Watermarks found'
            sys.exit()

        self._watermarks.sort()

        self._initGui()
        self._showImage()
        self._m.mainloop()

    #--------------------------------------------------------------------------
    def _getCurrentCfg(self):

        path = self._imageList[self._imageIndex]
        if not path in self._config:
            im = Image.open(self._realPath(path))
            self._config[path] = {'path': path,
                               'size': im.size,
                               'box': None,
                               'flag': None,
                               'format': im.format,
                               'save': False,
                               'wm': '',
                               'wmX': -1, 'wmY': -1, 'wmW': -1, 'wmH': -1,
                               'time': None}

        return self._config[path]

    #--------------------------------------------------------------------------
    def _initGui(self):

        self._m = tk.Tk()
        self._m.geometry('+%d+%d' % (50,50))
        self._m.protocol("WM_DELETE_WINDOW", self._onQuit)

        self._m.title('Image Watermarker')

        # Top button bar
        if True:
            frame = tk.Frame(self._m)
            frame.grid(row=0, column=0, columnspan=2, sticky=tk.N+tk.W+tk.S+tk.E)

            tk.Button(frame, text='Help', command=self._onHelp).pack(side=tk.LEFT)
            tk.Label(frame, text=' ').pack(side=tk.LEFT)
    #        tk.Button(frame, text='#<--', command=self._onPrevOld).pack(side=tk.LEFT)
    #        tk.Button(frame, text='0<--', command=self._onPrevNew).pack(side=tk.LEFT)
            tk.Button(frame, text='  |<--  ', command=self._onToStart).pack(side=tk.LEFT)
            tk.Button(frame, text='   <--   ', command=self._onPrev).pack(side=tk.LEFT)
            tk.Button(frame, text='   -->   ', command=self._onNext).pack(side=tk.LEFT)
            tk.Button(frame, text='  -->0  ', command=self._onNextNew).pack(side=tk.LEFT)
    #        tk.Button(frame, text='-->#', command=self._onNextOld).pack(side=tk.LEFT)
            tk.Label(frame, text=' ').pack(side=tk.LEFT)
            tk.Button(frame, text='Save', command=self._onSave).pack(side=tk.LEFT)
            tk.Label(frame, text=' ').pack(side=tk.LEFT)
            tk.Button(frame, text='Clear All', command=self._onClearAll).pack(side=tk.LEFT)
            tk.Label(frame, text=' ').pack(side=tk.LEFT)
            tk.Button(frame, text='Close', command=self._onQuit).pack(side=tk.LEFT)


        # Checks, flags, and Watermarks side bar
        if True:
            frame = tk.Frame(self._m)
            frame.grid(row=1, column=0, sticky=tk.N+tk.W+tk.S+tk.E)

            # Checks
            frameC = tk.Frame(frame)
            frameC.grid(row=0, column=0, sticky=tk.N+tk.W+tk.S+tk.E)

            self._labelNeedSave = tk.Label(frameC, text='CHANGED', bg='orange')
            self._labelNeedSave.pack(side=tk.LEFT)
            tk.Label(frameC, text=' ').pack(side=tk.LEFT)

            self._autoNext = tk.IntVar()
            self._autoNext.set(1)
            tk.Checkbutton(frameC, text="Auto Next", variable=self._autoNext).pack(side=tk.LEFT)

            self._autoNextNew = tk.IntVar()
            self._autoNextNew.set(0)
            tk.Checkbutton(frameC, text="New Only", variable=self._autoNextNew).pack(side=tk.LEFT)

            # Flagging Message
            self._labelFlag = tk.StringVar()
            self._labelFlag.trace('w', self._onFlagChange)
            tk.Entry(frame, textvariable=self._labelFlag).grid(row=1, column=0, sticky=tk.N+tk.W+tk.S+tk.E)

            # Box resize
            frameB = tk.Frame(frame)
            frameB.grid(row=2, column=0, sticky=tk.N+tk.W+tk.S+tk.E)
            tk.Label(frameB, text='Resize:').pack(side=tk.LEFT)
            tk.Button(frameB, text=' - ', command=self._onBoxSmaller).pack(side=tk.LEFT)
            tk.Button(frameB, text=' + ', command=self._onBoxBigger).pack(side=tk.LEFT)
            tk.Label(frameB, text=' ').pack(side=tk.LEFT)
            self._boxOnOffButton = tk.Button(frameB, text=' On  ', command=self._onBoxOff)
            self._boxOnOffButton.pack(side=tk.LEFT)

            # States Flags
            frameS = tk.Frame(frame)
            frameS.grid(row=3, column=0, sticky=tk.N+tk.W+tk.S+tk.E)

            self._labelWillSave = tk.Label(frameS, text='SET', bg='green')
            self._labelWillSave.pack(side=tk.LEFT)
            tk.Label(frameS, text=' ').pack(side=tk.LEFT)
            self._labelNoWatermark = tk.Label(frameS, text='NO WATERMARK', bg='red')
            self._labelNoWatermark.pack(side=tk.LEFT)
            tk.Label(frameS, text=' ').pack(side=tk.LEFT)
            self._labelResize = tk.Label(frameS, text='RESIZE', bg='lightblue')
            self._labelResize.pack(side=tk.LEFT)

            # Watermarks
            frameW = tk.Frame(frame)
            frameW.grid(row=4, column=0, sticky=tk.N+tk.W)
            self._watermarkCache = {}
            for path in self._watermarks:
                im = Image.open(self._realPath(path))
                #im.thumbnail((75, 75))
                ratio = 1
                imSmall = im.resize((im.size[0]*ratio, im.size[1]*ratio), Image.ANTIALIAS)
                tkim = ImageTk.PhotoImage(im)
                tkimSmall = ImageTk.PhotoImage(imSmall)
                widget = tk.Button(frameW, relief=tk.RAISED, text=path, image=tkimSmall, command=self._selectWatermark)
              #  widget.option_add('path', path)
                widget.pack(side=tk.TOP)
                self._watermarkCache[path] = {'tkimSmall': tkimSmall, 'tkim': tkim, 'w': im.size[0], 'h':im.size[1], 'widget':widget, 'im': im}

        self._wm = self._watermarks[0]
        self._selectWatermark()

        # Title and image
        if True:
            frame = tk.Frame(self._m)
            frame.grid(row=1, column=1, sticky=tk.N+tk.W+tk.S+tk.E)

            # Title text
            self._labelTitle = tk.StringVar()
            tk.Label(frame, text='Title', textvariable=self._labelTitle).grid(row=0, column=0, sticky=tk.N+tk.W)

            # Image view
            self._imageFrame = frame
            self._labelCanvas = tk.Label(frame, text='<image>', bg='red')
            self._labelCanvas.grid(row=1, column=0, sticky=tk.N+tk.W)

        # Status bar
        frame = tk.Frame(self._m)
        frame.grid(row=2, column=0, columnspan=2, sticky=tk.S+tk.W)
        self._labelStatus = tk.StringVar()
        tk.Label(frame, text='Status', textvariable=self._labelStatus).pack(side=tk.LEFT)


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
        if tkMessageBox.askyesno("Clear All", "This will clear ALL %d\nof your settings.\n\nIs this what you want to do?" % len(self._config), icon=tkMessageBox.WARNING):
            self._config = {}
            self._showImage()
            self._needSave = True
            self._updateFlags()

    #--------------------------------------------------------------------------
    def _onHelp(self):
        tkMessageBox.showinfo("WaterMarker: Help", helpText)

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
    def _onToStart(self):
        self._imageIndex = 0
        self._showImage()

    #--------------------------------------------------------------------------
    def _onPrev(self):
        self._goPrevImage()
        self._showImage()

    #--------------------------------------------------------------------------
    def _onNext(self):
        self._goNextImage()
        self._showImage()

    #--------------------------------------------------------------------------
#    def _onPrevNew(self):
#        while True:
#            if not self._goPrevImage():
#                break
#            cfg = self._getCurrentCfg()
#            if not cfg['save']:
#                break
#        self._showImage()

    #--------------------------------------------------------------------------
    def _onNextNew(self):
        while True:
            if not self._goNextImage():
                print '  -- Next New STOP: Beginnning of set'
                break
            cfg = self._getCurrentCfg()
            if not cfg['save']:
                print '  -- Next New STOP: Not saved'
                break
            if cfg['flag']:
                print '  -- Next New STOP: Flagged: %s' % cfg['flag']
                break
            if cfg['wm']:
                if not os.path.isfile(self._realPath(cfg['wm'])):
                    print '  -- Next New STOP: Watermark file "%s" does not exist' % self._realPath(cfg['wm'])
                    break
                w = cfg['size'][0]
                h = cfg['size'][1]
                if cfg['box']:
                    ratio = cfg['box']/float(max(w,h))
                    print w,h,ratio
                    w = int(ratio*w)
                    h = int(ratio*h)
                    print w,h
                if (cfg['wmX']+cfg['wmW']) > w:
                    print '  -- Next New STOP: Watermark overlaps on right edge'
                    break
                if (cfg['wmY']+cfg['wmH']) > h:
                    print '  -- Next New STOP: Watermark overlaps on bottom edge'
                    break

        self._showImage()

    #--------------------------------------------------------------------------
#    def _onPrevOld(self):
#        while True:
#            if not self._goPrevImage():
#                break
#            cfg = self._getCurrentCfg()
#            if cfg['save']:
#                break
#        self._showImage()

    #--------------------------------------------------------------------------
#    def _onNextOld(self):
#        while True:
#            if not self._goNextImage():
#                break
#            cfg = self._getCurrentCfg()
#            if cfg['save']:
#                break
#        self._showImage()

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
    def _updateFlags(self):
        self._labelNeedSave.config(bg='grey')
        self._labelNoWatermark.config(bg='grey')
        self._labelWillSave.config(bg='grey')
        self._labelResize.config(bg='grey')

        if self._needSave:
            self._labelNeedSave.config(bg='orange')

        cfg = self._getCurrentCfg()
        if cfg['save']:
            self._labelWillSave.config(bg='green')
            if not cfg['wm']:
                self._labelNoWatermark.config(bg='red')

        self._labelResize.config(text='Resize %d' % self._boundingBoxSize)
        if self._boundingBox:
            self._labelResize.config(bg='lightblue')

    #--------------------------------------------------------------------------
    def _showImage(self):

        cfg = self._getCurrentCfg()
        print '- show image: (%d) %s' % (self._imageIndex+1, cfg['path'])

        if cfg['flag']:
            self._labelFlag.set(cfg['flag'])
        else:
            self._labelFlag.set('')

        self._boundingBox = False
        if cfg['box']:
            self._boundingBox = True
            self._boundingBoxSize = cfg['box']

        gridInfo =  self._labelCanvas.grid_info()
        if self._labelCanvas:
            self._labelCanvas.destroy()

        fileStat = os.stat(self._realPath(cfg['path']))
        self._currentIm  = Image.open(self._realPath(cfg['path']))
        im = self._currentIm
#        print 'DEBUG %s' % dir(im)
#        print 'DEBUG %s' % im.info
        self._labelTitle.set('%d of %d: %s [%d, %d] {%d}' % (self._imageIndex+1, len(self._imageList), self._realPath(cfg['path']), im.size[0], im.size[1], fileStat.st_size))

        self._labelCanvas = tk.Canvas(self._imageFrame, borderwidth=1, relief=tk.SUNKEN, width=im.size[0], height=im.size[1])
        self._labelCanvas.grid(row=gridInfo['row'], column=gridInfo['column'], rowspan=gridInfo['rowspan'], columnspan=gridInfo['columnspan'], sticky=tk.N+tk.W)
        self._labelCanvas.bind("<Button-1>", self._onImageClick)
        self._labelCanvas.bind("<Button-3>", self._onNoWatermark)
        self._labelCanvas.bind("<Motion>", self._onImageMove)
        self._labelCanvas.bind("<Leave>", self._onImageLeave)

        self._tkim = ImageTk.PhotoImage(im)
        self._labelCanvas.create_image(1,1, anchor=tk.NW, state=tk.NORMAL, image=self._tkim, tag=('image'))

        if cfg['wm']:
            self._selectWatermark(cfg['wm'])

        self._showBoundingBox()
        self._showWatermark()
        self._updateFlags()

    #--------------------------------------------------------------------------
    def _selectWatermark(self, path=''):

        for f in self._watermarkCache:
            self._watermarkCache[f]['widget'].config(relief=tk.RAISED)
 
        if not path:
            for f in self._watermarkCache:
                if self._watermarkCache[f]['widget'].cget('state') == 'active':
                    path = f

        if not path in self._watermarkCache:
            print '- watermark not found: %s' % path
            self._wm = ''
            self._wmH = -1
            self._wmW = -1
            return

        print '- select watermark: %s' % path
        self._watermarkCache[path]['widget'].config(relief=tk.SUNKEN)
        self._wm = path
        self._wmH = self._watermarkCache[path]['h']
        self._wmW = self._watermarkCache[path]['w']

    #--------------------------------------------------------------------------
    def _showBoundingBox(self):

        self._labelCanvas.delete(('boundingBox'))
        self._labelCanvas.delete(('boundingImage'))
        self._labelCanvas.delete(('boundingBase'))
        self._tkimBox = None

        x = 1
        y = 1
        if self._boundingBox:

            cfg = self._getCurrentCfg()

            # Grey Transparency
            grey = Image.new('RGBA', cfg['size'], (96,96,96, 1))
            self._tkimBoxGreyCache = ImageTk.PhotoImage(grey)
            self._labelCanvas.create_image(x, y, anchor=tk.NW, state=tk.NORMAL, image=self._tkimBoxGreyCache, tag=('boundingBase'))

            # Resized image
            im = Image.open(self._realPath(cfg['path']))
            w = im.size[0]
            h = im.size[1]
            ratio = float(self._boundingBoxSize) / float(max(w, h))
            w = int(w*ratio)
            h = int(h*ratio)

            self._tkimBox = im.resize((w, h), Image.ANTIALIAS)
            self._tkimBoxCache = ImageTk.PhotoImage(self._tkimBox)
            self._labelCanvas.create_image(x, y, anchor=tk.NW, state=tk.NORMAL, image=self._tkimBoxCache, tag=('boundingImage'))
            self._labelCanvas.tag_raise('boundingImage')

        # Bounding box
        w = self._boundingBoxSize+1
        h = self._boundingBoxSize+1
        box = (x, y, x+w, y+h)
        self._labelCanvas.create_rectangle(box, tags=('boundingBox'), outline='blue') 

    #--------------------------------------------------------------------------
    def _showWatermark(self):
        cfg = self._getCurrentCfg()
        self._labelCanvas.delete(('watermark'))

        if cfg['wm'] in self._watermarkCache:
            im = self._watermarkCache[cfg['wm']]['im']
            self._tkim2 = ImageTk.PhotoImage(im)
            self._labelCanvas.create_image(cfg['wmX'], cfg['wmY'], anchor=tk.NW, state=tk.NORMAL, image=self._tkim2, tag=('watermark'))
        else:
            if cfg['wm']:
                x = cfg['wmX']
                y = cfg['wmY']
                w = cfg['wmW']
                h = cfg['wmH']
                if x < 1: x = 2
                if y < 1: y = 2
                if w < 20: w = 40
                if h < 20: h = 40
                box = (x, y, x+w, y+h)
                self._labelCanvas.create_rectangle(box, tags=('watermark'), fill='orange', outline='red') 

    #--------------------------------------------------------------------------
    def _onBoxOff(self):
        cfg = self._getCurrentCfg()

        self._boundingBox = not self._boundingBox

        if self._boundingBox:
            self._boxOnOffButton.config(text=' Off  ')
            while self._boundingBoxSize > max(cfg['size'][0], cfg['size'][1]):
                self._boundingBoxSize -= self._boundingBoxIncrement
            cfg['box'] = self._boundingBoxSize
        else:
            self._boxOnOffButton.config(text=' On ')
            cfg['box'] = None

        cfg['time'] = time.time()
        cfg['save'] = True
        self._needSave = True
        self._saveConfig(backup=True)

        self._showBoundingBox()
        self._showWatermark()
        self._updateFlags()

    #--------------------------------------------------------------------------
    def _onBoxBigger(self):
        cfg = self._getCurrentCfg()

        self._boundingBoxSize += self._boundingBoxIncrement

        self._showBoundingBox()
        self._showWatermark()
        self._updateFlags()

    #--------------------------------------------------------------------------
    def _onBoxSmaller(self):
        cfg = self._getCurrentCfg()

        if self._boundingBoxSize > self._boundingBoxIncrement:
            self._boundingBoxSize -= self._boundingBoxIncrement

        if self._boundingBox:
            while self._boundingBoxSize > max(cfg['size'][0], cfg['size'][1]):
                self._boundingBoxSize -= self._boundingBoxIncrement

        self._showBoundingBox()
        self._showWatermark()
        self._updateFlags()

    #--------------------------------------------------------------------------
    def _onFlagChange(self, a, b, c):

        flag = self._labelFlag.get()
        if not flag:
            flag = None

        cfg = self._getCurrentCfg()
     
        if flag == cfg['flag']:
            return

        cfg['save'] = True
        cfg['flag'] = flag

        self._needSave = True
        self._updateFlags()
#        self._saveConfig(backup=True)

    #--------------------------------------------------------------------------
    def _onImageClick(self, event):

        cfg = self._getCurrentCfg()

        if not self._wm:
            print '- no watermark selected'
            return

        print 'Mark: %s [%d,%d] {%s}' % (cfg['path'], event.x, event.y, self._wm)

        cfg['wm'] = self._wm
        cfg['wmX'] = event.x
        cfg['wmY'] = event.y
        cfg['wmW'] = self._wmW
        cfg['wmH'] = self._wmH
        cfg['time'] = time.time()
        cfg['save'] = True
        self._needSave = True

        self._updateFlags()
        self._showWatermark()
        self._saveConfig(backup=True)

        if self._autoNext.get():
            if self._autoNextNew.get():
                self._onNextNew()
            else:
                self._onNext()
        
    #--------------------------------------------------------------------------
    def _onNoWatermark(self, *args):

        cfg = self._getCurrentCfg()

        print 'Do not mark: %s' % (cfg['path'])

        cfg['wm'] = ''
        cfg['wmX'] = -1
        cfg['wmY'] = -1
        cfg['wmW'] = -1
        cfg['wmH'] = -1
        cfg['time'] = time.time()
        cfg['save'] = True
        self._needSave = True
        self._saveConfig(backup=True)

        self._updateFlags()
        self._labelCanvas.delete(('watermark'))

        if self._autoNext.get():
            if self._autoNextNew.get():
                self._onNextNew()
            else:
                self._onNext()

    #--------------------------------------------------------------------------
    def _onImageLeave(self, event):
        self._labelCanvas.delete(('locate'))

    #--------------------------------------------------------------------------
    def _onImageMove(self, event):
        self._labelStatus.set('[%d,%d]' % (event.x, event.y))

        self._labelCanvas.delete(('locate'))

        if self._tkimBox:
            if event.x > self._tkimBox.size[0] or  event.y > self._tkimBox.size[1]:
                return
        
        if self._currentIm:
            cfg = self._getCurrentCfg()
#            print event.x, cfg['wmW'], self._currentIm.size[0], ':', event.y, cfg['wmH'], self._currentIm.size[1]
            if event.x <= 1 or  event.y <= 1:
                return
            if event.x+cfg['wmW'] > self._currentIm.size[0] or  event.y+cfg['wmH'] > self._currentIm.size[1]:
                return

        if self._wm:
            if self._wm in self._watermarkCache:

                im = self._watermarkCache[self._wm]['im']

                box = (event.x-1, event.y-1, event.x+im.size[0]+1, event.y+im.size[1]+1)
                self._labelCanvas.create_rectangle(box, tags=('locate'), outline='red', dash=(4,4)) 

                self._tkim1 = ImageTk.PhotoImage(im)
                self._labelCanvas.create_image(event.x, event.y, anchor=tk.NW, state=tk.NORMAL, image=self._tkim1, tag=('locate'))


#==============================================================================
def main(argv):

## Move watermark configuration into _watermark directory
#    def duh():
#        fh = open('sadf/src/_watermark.cfg','rt')
#        inp = pickle.load(fh)
#        out = {}
#
#        for key in inp:
#            out[key] = {}
#            for f in inp[key]:
#                if f == 'wm':
#                    out[key][f] = inp[key][f].replace('_watermark', '_watermark/')
#                else:
#                    out[key][f] = inp[key][f]
#
#        fh = open('sadf/src/_watermark/watermark.cfg','wt')
#        pickle.dump(out, fh)
#        return

    if len(argv) == 1:
        print __doc__
        return -1

    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'h', ['help', 'start=', 'index='])
    except getopt.GetoptError, e:
        print __doc__
        print "! Syntax error: ",e
        return -1

    startName = None
    startIndex = 0

    for n,v in optList:
        if n == '--help' or n == '-h':
            print __doc__
            return 0
        if n == '--start':
            startName = v       
        if n == '--index':
            startIndex = int(v)

    if len(optRemainder) != 1:
        print __doc__
        print "! Need to specify a project directory"
        return -1
    projectDir = optRemainder[0]
    
    srcRoot = os.path.join(projectDir,srcDir)
    dstRoot = os.path.join(projectDir,dstDir)

    waterMarker = WaterMarker(srcRoot)
    waterMarker.run(startName=startName, startIndex=startIndex)

#==============================================================================
def cli():
    sys.exit(main(sys.argv))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

#==============================================================================
# end
