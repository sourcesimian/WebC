#! /usr/bin/env python

"""\
WebCompiler :: Web Site Log Processor  v1.0

USAGE: wc-process-logs

The configuration is stored in 'siteProcessLogs_config.py'
The history is written to 'siteProcessLogs.history'

"""

from siteProcessLogs_config import filterRules, smtpCreds, ftpCreds, scriptAdmin

import os
import sys
import ftplib
import gzip
import getpass
import binascii
import re
import time

import smtplib
import mimetypes
from email import Encoders
#from email.Message import Message
#from email.MIMEAudio import MIMEAudio
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
#from email.MIMEImage import MIMEImage
from email.MIMEText import MIMEText

timeStampFormat = "%Y-%m-%d %H:%M:%S +0000"
historyFileName = 'siteProcessLogs.history'

#===============================================================================
class SMTPMailer:
    def __init__(self, host, user, pw, fromAddr, fromName=None, port=24, autoDisconnect=False):
        self._s = None
        self._sentCount = 0

        self._smtpHost = host
        self._smtpPort = port 
        self._smtpUser = user
        self._smtpPass = pw

        self._fromAddr = fromAddr
        self._fromName = fromName
        self._autoDisconnect = autoDisconnect

    #--------------------------------------------------------------------------
    def connect(self):
        if self._s:
            return

        self._s = smtplib.SMTP(self._smtpHost, self._smtpPort)

    #    s.set_debuglevel(1)

        self._s.ehlo(self._smtpUser)
        self._s.starttls()
        self._s.ehlo(self._smtpUser)
        self._s.login(self._smtpUser, self._smtpPass) 

    #--------------------------------------------------------------------------
    def disconnect(self):
        if self._s:
            self._s.quit()
        self._s = None

    #--------------------------------------------------------------------------
    def __del__(self):
        self.disconnect()

    #--------------------------------------------------------------------------
    def send(self, toAddr, toName, subject, body, atts):

        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg.preamble = 'This is a multi-part MIME message.\n'
        msg.epilogue = ''  # To guarantee the message ends with a newline

        msg['Subject'] = subject
        if self._fromName:  msg['From'] = '"%s" <%s>' % (self._fromName, self._fromAddr)
        else:               msg['From'] = '%s' % (self._fromName)
        msg['To'] = '"%s" <%s>' % (toName, toAddr)
        toAddrs = [toAddr]

        part = MIMEText(body.replace('\n', '<br>\n'), 'html')
        msg.attach(part)

        # Add attachments
        for attName,att in atts:
            if not att:
                att = open(attName, 'rb').read()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(att)
            part.add_header('Content-Disposition', 'attachment', filename=attName)
            Encoders.encode_base64(part)
            """
            part = MIMEText(att, 'text/plain')
            """
            msg.attach(part)

        self.connect()
        self._s.sendmail(self._fromAddr, toAddrs, msg.as_string())

        if self._autoDisconnect:
            self.disconnect()

        self._sentCount += 1

    #--------------------------------------------------------------------------
    def getSentCount(self):
        return self._sentCount

#===============================================================================
class LogFilter:
    def __init__(self, smtpMailer):
        self._rules = None
        self._smtpMailer = smtpMailer
    
    #---------------------------------------------------------------------------
    def _loadRules(self):
        if self._rules: return
        self._rules = {}

        for recip in filterRules:
            matchRules = []
            countRules = []

            for rule in filterRules[recip]['matchRules']:
                try:
                    matchRules.append(re.compile(rule))        
                except:
                    print '! Match rule for %s failed {%s}' % (recip, rule)
                    sys.exit(-1)

            for rule in filterRules[recip]['countRules']:
                try:
                    countRules.append(re.compile(rule))        
                except:
                    print '! Count rule for %s failed {%s}' % (recip, rule)
                    sys.exit(-2)

            self._rules[recip] = {
                'match': matchRules,
                'count': countRules,
                'name': filterRules[recip]['name']
            }

    #---------------------------------------------------------------------------
    def doFilter(self, fileName):
        self._loadRules()

        # Initialise
        logDict = {}
        for recip in self._rules:
            counts = {}
            for rule in self._rules[recip]['count']:
                counts[rule.pattern] = 0
            logDict[recip] = {'log':'', 'count':counts}


        # Scan file
        f = open(fileName, 'rt')
        for line in f:

            for recip in self._rules:
                match = False
                for ruleMatch in self._rules[recip]['match']:
                    if not ruleMatch.search(line): continue

                    match = True
                    for ruleCount in self._rules[recip]['count']:
                        if not ruleCount.search(line): continue
                        logDict[recip]['count'][ruleCount.pattern] += 1
                
                if match:                
                    logDict[recip]['log'] += line

        """
        for recip in logDict:
            print recip
            print 'Log len', len(logDict[recip]['log'])
            keys = logDict[recip]['count'].keys()
            keys.sort()
            for c in keys:
                print logDict[recip]['count'][c],c
            print
        """

        self._mailReports(fileName, logDict)

    #---------------------------------------------------------------------------
    def _mailReports(self, fileName, logDict):

        # Send Emails
        emailSubject = 'WebCompiler Log: %s' % fileName
        emailMsgSignature = '\n-- \nExampleDemo.com\n'

        for recip in logDict:
            # Send the filtered log to the others
            toAddr = recip
            toName = self._rules[recip]['name']

            emailMsg = 'Hello %s\n\n' % toName.split()[0]
            if logDict[recip]['log']:
                emailAtts = [(fileName, logDict[recip]['log'])]

                emailMsg += 'Your log file is attached: %s\n\n' % (fileName)

                if logDict[recip]['count']:
                    emailMsg += 'Your counters are as follows:\n'
                    keys = logDict[recip]['count'].keys()
                    keys.sort()
                    for c in keys:
                        emailMsg += ' - %d  :  {%s}\n' % (logDict[recip]['count'][c], c)
                    emailMsg += '\n'
            else:
                emailAtts = []
                emailMsg += 'No log entries were found for you in this log file: %s\n\n' % (fileName)

            if self._rules[recip]['match']:
                emailMsg += 'Your log match rules are as follows:\n'
                for rule in self._rules[recip]['match']:
                    emailMsg += ' - {%s}\n' % (rule.pattern)
                emailMsg += '\n'

            emailMsg += emailMsgSignature

            print ' - sending filtered log to: %s (size: %s) ...' % (toAddr, len(logDict[recip]['log']))
            self._smtpMailer.send(toAddr, toName, emailSubject, emailMsg, emailAtts)

#===============================================================================
class WriteBuf:
    def __init__(self):
        self._buf = []

    #---------------------------------------------------------------------------
    def __call__(self, data):
        self._buf.append(data)

    #---------------------------------------------------------------------------
    def __iter__(self):
        for line in self._buf:
            yield line

    #---------------------------------------------------------------------------
    def clear(self):
        self._buf = []

    #---------------------------------------------------------------------------
    def get(self):
        return self._buf

#===============================================================================
class LogFiles:
    def __init__(self, host, user, pw):
        self._ftp = None    
        self._buf = WriteBuf()

        try:
            self._ftp = ftplib.FTP()
            self._ftp.connect(host)
            welcome =  self._ftp.getwelcome()
            print ' '+welcome
            self._ftp.login(user, pw)
            self._ftp.cwd('/logs')
        except ftplib.error_perm,e:
            print ' '+str(e)
            sys.exit(-1)


    #---------------------------------------------------------------------------
    def __del__(self):
        if self._ftp:
            self._ftp.close()

    #---------------------------------------------------------------------------
    def listAll(self):
        files = []        

        self._buf.clear()
        cmd = 'LIST access.log.*.gz'
        print ' '+cmd
        self._ftp.retrlines(cmd, self._buf)

        reLog = re.compile('\s([0-9]+)\s([A-Z]{1}[a-z]{2}\s+[0-9]{1,2}\s+[0-9]{2}\:[0-9]{2})\s+(access\.log\.[0-9]{2}\.gz)')
        for line in self._buf:
            print ' '+line
            res = reLog.search(line)
            if not res: continue
            files.append([res.group(3), res.group(2), res.group(1)])
        print

        return files

    #---------------------------------------------------------------------------
    def fetch(self, fileName, diskFileName):
        self._ftp.retrbinary('RETR %s' % fileName, open(diskFileName, 'wb').write)
    

#===============================================================================
def main(argv):
    global historyFileName
    
    pw = None
    logFilter = None

    try:
        import getopt
        optList, optRemainder = getopt.gnu_getopt(argv[1:], 'h', ['help'])
    except getopt.GetoptError, e:
        print __doc__
        print "! Syntax error: ",e
        return -1

    for n,v in optList:
        if n == '--help' or n == '-h':
            print __doc__
            return 0

    print
    historyList = {}
    if os.path.isfile(historyFileName):
        for line in open(historyFileName, 'rt'):
            line = line.strip()
            if not line: continue
            if line.startswith('#'): continue
            s = line.split('\t')
            key = s[0]+s[1]
            historyList[key] = s
    print 'Found %d history records in "%s"'% (len(historyList), historyFileName)

    print 'Connecting to FTP server ...'
    if not pw:
        pw = getpass.getpass('Enter password for [%s@%s]: ' % (ftpCreds['user'], ftpCreds['host']))
    logFiles = LogFiles(ftpCreds['host'], ftpCreds['user'], pw)
    logs = logFiles.listAll()
    smtpMailer = SMTPMailer(smtpCreds['host'], smtpCreds['user'], pw, smtpCreds['fromAddr'], smtpCreds['fromName'], smtpCreds['port'])

    fetchList = []
    for logName,logDate,logSize in logs:
        key = logName+logDate
        #print key
        if key not in historyList:
            fetchList.append([logName,logDate,logSize])

    if not fetchList:
        print 'Done: No new logs found'
        return

    print '%d new log(s) found' % len(fetchList)

    historyFile = open(historyFileName, 'at')
    for logName,logDate,logSize in fetchList:
        print 'Processing "%s" ...' % logName
        tmpFileName = '.fetchLogFiles.tmp'
        fileName = 'exampledemo.'+os.path.splitext(logName)[0]
        
        print ' - fetching (size: %s) ...' % (logSize)
        logFiles.fetch(logName, tmpFileName)
        if os.stat(tmpFileName).st_size != int(logSize):
            print '! File size mismatch, possibly corrupt'
            sys.exit(-3)

        print ' - unziping'
        f = gzip.open(tmpFileName, 'rb')
        content = f.read()
        f.close()
        open(fileName, 'wb').write(content)

        print ' - filtering (size: %d)' % (os.stat(fileName).st_size)
        if not logFilter:
            logFilter = LogFilter(smtpMailer)

        logFilter.doFilter(fileName)
    
        nowString = time.strftime(timeStampFormat, time.gmtime())
        historyFile.write('%s\t%s\t%s\t%s\n' % (logName, logDate, logSize, nowString))
        historyFile.flush()
        os.fsync(historyFile.fileno())

    historyFile.close()


    print 'Backing up script and configuration'
    scriptName = os.path.splitext(os.path.split(argv[0])[1])[0]
    toAddr = scriptAdmin['email']
    toName = scriptAdmin['name']
    emailSubject = 'BACKUP: "%s"' % (scriptName)
    emailMsg = 'Backup of %s script' % scriptName
    emailAtts = [
        ('%s.py' % scriptName, None),
        ('%s_config.py' % scriptName, None),
        ('%s.history' % scriptName, None),
    ]
    smtpMailer.send(toAddr, toName, emailSubject, emailMsg, emailAtts)

    print 'Done: Processed %d logs' % len(fetchList)
    

#===============================================================================
def cli():
    sys.exit(main(sys.argv))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

#===============================================================================
# end

