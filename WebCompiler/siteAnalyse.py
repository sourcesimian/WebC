#! /usr/bin/env python

"""\
WebCompiler :: Site Analyser  v1.0
- A utility to analyse various aspects of your web site and generate a report

USAGE: wc-analyse <projectDir> [<switches>]

Switches:
    --fixStrictRefs - Will attempt to correc the strict references
                      THIS IS  POTENTIALLY DESTRUCTIVE PROCESS
                      *** BACKUP YOUR 'src' DIRECTORY FIRST

This utility will work with all files found in: <projectDir>/src

The analysis log will be written to the current directory.
"""

import os
import sys
import hashlib
import re
import urllib


import os

srcDir = 'src'
dstDir = 'root'

outFile = 'analyseLog.tsv'
outFh = None

#===============================================================================
def out(line):
    global outFh

    if not outFh:
        outFh = open(outFile, 'wt')

    outFh.write(line+'\n')

#===============================================================================
def relpath(p1, p2):

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

    (common,l1,l2) = commonpath(pathsplit(p1), pathsplit(p2))
    p = []
    if len(l1) > 0:
        p = [ '../' * len(l1) ]
    p = p + l2
    return os.path.join( *p )


#===============================================================================
def writeErr(msg):
#    sys.stderr.write(msg)
    pass

#===============================================================================
def getImgTags(fileName):

    src = open(fileName, 'rt').read()
    aTag = re.compile('<\s*img.*?>', re.IGNORECASE | re.MULTILINE | re.DOTALL)

    res = aTag.findall(src)

    return res

#===============================================================================
def getATags(fileName):

    src = open(fileName, 'rt').read()
    aTag = re.compile('<\s*a.*?>.*?<\s*\/a\s*>', re.IGNORECASE | re.MULTILINE | re.DOTALL)

    res = aTag.findall(src)

    return res

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
            writeErr('SKIP %s\n' % tag)
            pass

    return res

#===============================================================================
def getLinks(fileName):
    tags = getATags(fileName)

    tags = getATags(fileName)
    res = {}
    for tag in tags:
        attrib = getAttrib(tag, 'href')
        if attrib:
            attrib = attrib.strip()
            if not attrib: continue
            res[attrib] = {'tag':tag}
        else:
            writeErr('SKIP %s\n' % tag)
            pass

    return res

#===============================================================================
def getFileDict(basePath):

    fileDict = {} 
    dupList = {}
        
    for root, dirs, files in os.walk(basePath, topdown=False):
        for f in files:
            ref = f.lower()
            path = os.path.join(root, f)
            ext = os.path.splitext(f)[1]

            if ref in fileDict:
                out( 'DUP: [%s] %s : %s' % (ref, fileDict[ref]['path'], path) )
            else:
                fileDict[ref] = {'path': path, 'links':[], 'imgs':[], 'ext': ext}

    out( "- %d files found" % len(fileDict) )
    if dupList:
        for ref in dupList:
            out( 'DUP:\t[%s]\t%s\t&&\t%s' % (ref, dupList['path1'], dupList['path2']) )
        out( '! Currently can not proceed further with duplicate file names present' )
        sys.exit()

    return fileDict

#===============================================================================
def getExternalDeps(fileDict):
    for f in fileDict:
        if fileDict[f]['ext'] == '.html':
            fileDict[f]['imgs'] = getImgRefs(fileDict[f]['path'])
            fileDict[f]['links'] = getLinks(fileDict[f]['path'])

#===============================================================================
def writeDotty(fileDict, fileHandle=sys.stdout):
    
    fileHandle.write('digraph G {\n')
    fileHandle.write('graph [splines=true overlap=false]\n')


    fileHandle.write('node [color=lightblue2, style=filled, shape=triangle];\n')
    for f in fileDict:                  
        if fileDict[f]['ext'] == '.html':
            fileHandle.write('"%s";\n' %f)
    fileHandle.write('\n')


    fileHandle.write('node [color=red, style=filled, shape=box];\n')
    for f in fileDict:                  
        if fileDict[f]['ext'] == '.jpg' or fileDict[f]['ext'] == '.gif':
            fileHandle.write('"%s";\n' %f)
    fileHandle.write('\n')


    x = 1
    for f in fileDict:
        fileDict[f]['dotty'] = x
        x += 1

    for f in fileDict:                  
        if fileDict[f]['ext'] == '.html':
            for img in fileDict[f]['imgs']:
                if img in fileDict:
                    fileHandle.write('    "%s" -> "%s [shape=box,color=lightblue]";\n' % (f, img))
            for link in fileDict[f]['links'].keys():
                if link in fileDict:
                    fileHandle.write('    "%s" -> "%s [shape=triangle,color=red]";\n' % (f, link))
                    
    fileHandle.write('}\n')


#===============================================================================
def searchAndReplaceInFile(fileName, search, replace):
    
    content = open(fileName, 'rt').read()
    content = content.replace(search, replace)
    open(fileName, 'wt').write(content)


#===============================================================================
def findWeakBadRefs(fileDict):
    badRefs = []
    extRefs = []
    mailRefs = []

    for f in fileDict:
        if fileDict[f]['ext'] != '.html': continue

        refDict = {}
        for x in fileDict[f]['links']:
            refDict[x] = fileDict[f]['links'][x]
        for x in fileDict[f]['imgs']:
            refDict[x] = fileDict[f]['imgs'][x]

        for ref in refDict:
            name = os.path.split(ref)[-1]
            if not name.lower() in fileDict:

                replaceList = {
                    'http://www.geocities.com/sadfbook/bgtoc.html': '../bgtoc.html',
                }
                exemptList = [
                    'http://www.opsmedic.co.za/okatopeplan.htm',
                    'http://www.netcentral.co.uk/~cobus/32BAT.htm',
                    'http://www.lenoury.net/beetlecrusher/beetlecrusher.htm',
                    'http://www.geocities.com/ebrunsdon/personal/diary.htm',
                    'http://www.adrians.iwarp.com/swa.htm',
                    'http://ourworld.compuserve.com/homepages/andrewbrooks1/marais.htm',
                    'http://dreklaw.bravepages.com/armymain.htm',
                    'http://www.opsmedic.co.za/okatopeplan.htm',
                    'http://www.adrians.iwarp.com/swa.htm',
                    'http://ourworld.compuserve.com/homepages/andrewbrooks1/marais.htm',
                    'http://dreklaw.bravepages.com/armymain.htm',
                    'http://www.opsmedic.co.za/okatopeplan.htm',
                ]
    
                if ref.endswith('.htm') and not ref in exemptList:
                    tagA = refDict[ref]['tag']
                    tagB = tagA.replace(ref, ref+'l')
                    searchAndReplaceInFile(fileDict[f]['path'], tagA, tagB)

                elif ref in replaceList:
                    tagA = refDict[ref]['tag']
                    tagB = tagA.replace(ref, replaceList[ref])
                    searchAndReplaceInFile(fileDict[f]['path'], tagA, tagB)

                elif ref == 'http://visit.geocities.com/counter.gif':
                    tagA = refDict[ref]['tag']
                    tagB = '<!-- '+tagA[1:-1]+' -->'
                    searchAndReplaceInFile(fileDict[f]['path'], tagA, tagB)

                elif ref.startswith('mailto:'):
                    mailRefs.append((fileDict[f]['path'], ref))
#                    tagA = refDict[ref]['tag']
#                    if tagA.lower().startswith('<a'):
#                        tagB = None
#                        if tagA.find(' HREF=') != -1:
#                            tagB = tagA.replace(' HREF=', ' class="email" href=')
#                        elif tagA.find(' HREF=') != -1:
#                            tagB = tagA.replace(' href=', ' class="email" href=')
#                        if tagB:
#                            print fileDict[f]['path'], tagB
#                            searchAndReplaceInFile(fileDict[f]['path'], tagA, tagB)

                elif ref.startswith('http:'):
                    extRefs.append((fileDict[f]['path'], ref))

#                    tagA = refDict[ref]['tag']
#                    if tagA.lower().startswith('<a'):
#                        tagB = None
#                        if tagA.find(' HREF=') != -1:
#                            tagB = tagA.replace(' HREF=', ' class="external" href=')
#                        elif tagA.find(' HREF=') != -1:
#                            tagB = tagA.replace(' href=', ' class="external" href=')
#                        if tagB:
#                            print fileDict[f]['path'], tagB
#                            searchAndReplaceInFile(fileDict[f]['path'], tagA, tagB)

                else:
                    badRefs.append((fileDict[f]['path'], ref))

    return {'bad': badRefs, 'ext': extRefs, 'mail': mailRefs}

#===============================================================================
def findStrictBadRefs(fileDict, fix=False):

    strictRef = []

    for f in fileDict:
        if fileDict[f]['ext'] != '.html': continue

        fPath,fName = os.path.split(fileDict[f]['path'])
        
        refDict = {}
        for x in fileDict[f]['links']:
            refDict[x] = fileDict[f]['links'][x]
        for x in fileDict[f]['imgs']:
            refDict[x] = fileDict[f]['imgs'][x]

        for ref in refDict:
            if ref.startswith('http:'): continue
            if ref.startswith('mailto:'): continue

            rPath,rName = os.path.split(ref)

            key = rName.lower()
            if key in fileDict:

                newRef = None                
                tmpRef = ref
                while True:
                    diskPathName = fileDict[key]['path']

                    if diskPathName == os.path.relpath(os.path.join(fPath, tmpRef)):
                        break
                    diskPath,diskName = os.path.split(diskPathName) 


                    tmpRef = tmpRef.replace(rName, diskName)
                    if diskPathName == os.path.relpath(os.path.join(fPath, tmpRef)):
                        newRef = tmpRef
                        break

                    if len(diskPathName) != len(os.path.join(fPath, tmpRef)):
                        tmpRef = os.path.relpath(os.path.join(relpath (fPath, diskPath), rName))
#                        print tmpRef
#                        print diskPathName
#                        print os.path.relpath(os.path.join(fPath, tmpRef))
                        if diskPathName == os.path.relpath(os.path.join(fPath, tmpRef)):
                            newRef = tmpRef
                            break

                    tmpPath = tmpRef.replace(rName, diskName)
#                    print tmpPath
                    if diskPathName == os.path.relpath(os.path.join(fPath, tmpPath)):
                        newRef = tmpPath
                        break

                    newRef = 'ERROR'
                    out( 'BADsREF\t%s\t{%s}\t->\t{%s}' % (fileDict[f]['path'], ref, newRef) )
                    break

                if newRef and newRef != 'ERROR':
                    strictRef.append({'file':fileDict[f]['path'], 'tag': refDict[ref]['tag'], 'oldRef':ref, 'newRef':newRef})

    if fix:
        for ref in strictRef:
            tagA = ref['tag']
            tagB = tagA.replace(ref['oldRef'], ref['newRef'])
            searchAndReplaceInFile(ref['file'], tagA, tagB)

    return strictRef

#===============================================================================
def printRelativeReferences(fileDict):

    for f in fileDict:
        if fileDict[f]['ext'] != '.html': continue

        refDict = {}
        for x in fileDict[f]['links']:
            refDict[x] = fileDict[f]['links'][x]
        for x in fileDict[f]['imgs']:
            refDict[x] = fileDict[f]['imgs'][x]

        for ref in refDict:
            if ref.startswith('http:'): continue
            if ref.startswith('mailto:'): continue

            rPath,rName = os.path.split(ref)
            if rPath:
                out( 'RELREF\t%s\t{%s}' % (fileDict[f]['path'], ref) )

#===============================================================================
def printBackReferences(fileDict):

    for f in fileDict:
        if fileDict[f]['ext'] != '.html': continue

        refDict = {}
        for x in fileDict[f]['links']:
            refDict[x] = fileDict[f]['links'][x]
        for x in fileDict[f]['imgs']:
            refDict[x] = fileDict[f]['imgs'][x]

        for ref in refDict:
            if ref.startswith('http:'): continue
            if ref.startswith('mailto:'): continue

            if ref.find('..') != -1 :
                if ref.endswith('index.html'): continue

                out( 'BACKREF\t%s\t{%s}' % (fileDict[f]['path'], ref) )

#===============================================================================
def findUnreferencedFiles(fileDict):

    unrefFiles = []
    
    yesDict = {}
    for f in fileDict:
        yesDict[f] = {'file':fileDict[f]['path'], 'seen':False}

    for f in fileDict:
        if fileDict[f]['ext'] != '.html': continue

        refDict = {}
        for x in fileDict[f]['links']:
            refDict[x] = fileDict[f]['links'][x]
        for x in fileDict[f]['imgs']:
            refDict[x] = fileDict[f]['imgs'][x]

        for ref in refDict:
            rPath,rName = os.path.split(ref)
            key = rName.lower()
            if key in yesDict:
                yesDict[key]['seen'] = True

    for f in yesDict:
        if not yesDict[f]['seen']:
            unrefFiles.append(yesDict[f]['file'])
    
    return unrefFiles

#===============================================================================
def testExtLinks(links):
    failedLinks = []

    for fileName,ref in links:
        print ' - Testing: %s' % ref
        try:
            data = urllib.urlretrieve(ref)
        except IOError:
            print ' - Fail'
            failedLinks.append([fileName,ref])

    return failedLinks

#===============================================================================
def main(argv):

    global outFile

    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'h', ['help', 'fixStrictRefs'])
    except getopt.GetoptError, e:
        print __doc__
        print "! Syntax error: ",e
        return -1

    fixStrictRefs = False

    for n,v in optList:
        if n == '--help' or n == '-h':
            print __doc__
            return 0

        if n == '--fixStrictRefs':
            fixStrictRefs = True
            return 0

    if len(optRemainder) != 1:
        print __doc__
        print "! Need to specify a project directory"
        return -1
    projectDir = optRemainder[0]
    
    s = os.path.split(projectDir)
    if len(s[-1]): s = s[-1]
    else:          s = s[-2] 
    outFile = s+'.'+outFile

    srcRoot = os.path.join(projectDir,srcDir)
    dstRoot = os.path.join(projectDir,dstDir)

    #---------------------------------------------------------------------------
    fileDict = getFileDict(srcRoot)

    getExternalDeps(fileDict)


    refs = findWeakBadRefs(fileDict)

    def printRefs(refs, prefix):
        tmp = refs
        tmp.sort(lambda a,b: cmp(a[0], b[0]))

        for a,b in tmp:
            out( '%s\t%s\t{%s}' % (prefix, a, b) )


    printRefs(refs['bad'],  'BADwREF')
    out('')
    printRefs(refs['ext'],  'EXTREF ')
    out('')
    printRefs(refs['mail'], 'MAILREF')
    out('')

#    badExtLinks = testExtLinks(refs['ext'])
#    printRefs(badExtLinks, 'BADEXTREF')
#    out('')

    strictRef = findStrictBadRefs(fileDict, fix=fixStrictRefs)
    for ref in strictRef:
        out( 'BADsREF\t%s\t{%s}\t->\t{%s}' % (ref['file'], ref['oldRef'], ref['newRef']) )

    out('')
#    printRelativeReferences(fileDict)
    printBackReferences(fileDict)

    out('')
    unrefFiles = findUnreferencedFiles(fileDict)
    unrefFiles.sort()
    for f in unrefFiles:
        out( 'UNREF\t%s' % f )

    print 'Output written to: %s' % outFile

#===============================================================================
def cli():
    sys.exit(main(sys.argv))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

#===============================================================================
# end
