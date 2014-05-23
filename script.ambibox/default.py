#Modules General
import os
import sys
import mmap
import time
import re
import threading
from xml.etree import ElementTree

# sys.path.append('C:\Program Files (x86)\JetBrains\PyCharm 3.1.3\pycharm-debug-py3k.egg')
# import pydevd
# pydevd.settrace('localhost', port=51234, stdoutToServer=True, stderrToServer=True)

# Modules XBMC
import xbmc
import xbmcgui
import xbmcaddon

# Modules AmbiBox
import AmbiBox

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = str(__addon__.getAddonInfo('version'))
__settings__ = xbmcaddon.Addon("script.ambibox")
__language__ = __settings__.getLocalizedString
__data__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'data'))
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))

sys.path.append(__resource__)
sys.path.append(__data__)

from Media import *
media = Media()

ambibox = AmbiBox.AmbiBox(__settings__.getSetting("host"), int(__settings__.getSetting("port")))


def notification(text):
    text = text.encode('utf-8')
    info(text)
    if __settings__.getSetting("notification") == 'true':
        icon = __settings__.getAddonInfo("icon")
        smallicon = icon.encode("utf-8")
        xbmc.executebuiltin('Notification(AmbiBox,' + text + ',1000,' + smallicon + ')')


def debug(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg,), level=xbmc.LOGDEBUG)


def info(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg,), level=xbmc.LOGNOTICE)


class CapturePlayer(xbmc.Player):

    def __init__(self):
        xbmc.Player.__init__(self)
        self.inDataMap = None
        self.re3D = re.compile("[-. _]3d[-. _]", re.IGNORECASE)
        self.reTAB = re.compile("[-. _]h?tab[-. _]", re.IGNORECASE)
        self.reSBS = re.compile("[-. _]h?sbs[-. _]", re.IGNORECASE)

    def setProfile(self, enable, profile):
        __settings = xbmcaddon.Addon("script.ambibox")
        __settings.setSetting("last_profile", profile)

        ambibox.lock()
        if enable == 'true':
            notification(__language__(32033) % profile)
            ambibox.turnOn()
            ambibox.setProfile(profile)
        else:
            notification(__language__(32032))
            ambibox.turnOff()
        ambibox.unlock()

    def showmenu(self):
        menu = ambibox.getProfiles()
        menu.append(__language__(32021))
        menu.append(__language__(32022))
        off = len(menu)-2
        on = len(menu)-1
        mquit = False
        time.sleep(1)
        selected = xbmcgui.Dialog().select(__language__(32020), menu)
        while not mquit:
            if selected != -1:
                ambibox.lock()
                if (off == int(selected)):
                    ambibox.turnOff()
                elif (on == int(selected)):
                    ambibox.turnOn()
                else:
                    ambibox.turnOn()
                    self.setProfile('true', menu[selected])
                ambibox.unlock()
            mquit = True

    def onPlayBackStarted(self):
        __settings = xbmcaddon.Addon("script.ambibox")
        ambibox.connect()
        xxx = self.getPlayingFile()
        infos = media.getInfos(xxx)
        if infos[0] == 0:
            infos[0] = int(__settings.getSetting("screen_x"))
        if infos[1] == 0:
            infos[1] = int(__settings.getSetting("screen_y"))
        if infos[2] == 0:
            infos[2] = 1
        if infos[3] == 0:
            infos[3] = float(infos[0])/float(infos[1])

        if self.isPlayingAudio():
            self.setProfile(__settings.getSetting("audio_enable"), __settings.getSetting("audio_profile"))

        if self.isPlayingVideo():
            m = self.re3D.search(xxx)
            vidfmt = ""
            if m:
                n = self.reTAB.search(xxx)
                if n:
                    vidfmt = "TAB"
                else:
                    n = self.reSBS.search(xxx)
                    if n:
                        vidfmt = "SBS"
                    else:
                        info("Error in 3D filename - using default settings")
                        self.setProfile('true', __settings.getSetting("video_profile"))
            else:
                vidfmt = "Normal"

            videomode = __settings.getSetting("video_choice")
            try:
                videomode = int(videomode)
            except:
                videomode = 2

            if videomode == 0:    #Use Default Video Profile
                self.setProfile('true', __settings.getSetting("video_profile"))
            elif videomode == 1:  #Autoswitch
                DAR = infos[3]
                if DAR != 0:
                    SetAbxProfile(DAR, vidfmt, self)
                else:
                    info("Error retrieving DAR from video file")
            elif videomode == 2:   #Show menu
                show_menu = __settings.getSetting("show_menu")
                if (show_menu == 'true'):
                    self.showmenu()
            elif videomode == 3:   #Turn off
                ambibox.lock()
                ambibox.turnOff()
                ambibox.unlock()

            if __settings.getSetting("directXBMC_enable") == 'true':   #Added
                xd = XBMCDirect(infos, self)
                xd.run()
                xd.close()

    def onPlayBackEnded(self):
        ambibox.connect()
        __settings = xbmcaddon.Addon("script.ambibox")
        self.setProfile(__settings.getSetting("default_enable"), __settings.getSetting("default_profile"))

    def onPlayBackStopped(self):
        ambibox.connect()
        __settings = xbmcaddon.Addon("script.ambibox")
        self.setProfile(__settings.getSetting("default_enable"), __settings.getSetting("default_profile"))

    def close(self):
        ambibox.connect()
        ambibox.lock()
        ambibox.turnOff()
        ambibox.unlock()
        ambibox.disconnect()
        __settings = None

class XbmcMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)

    def onScreensaverDeactivated(self):
        self.setScreensaver(False)

    def onScreensaverActivated(self):
        self.setScreensaver(True)

    def setScreensaver(self, enabled):
        __settings = xbmcaddon.Addon("script.ambibox")

        ambibox.lock()
        if __settings.getSetting("disable_on_screensaver") and enabled:
            notification(__language__(32032))
            ambibox.turnOff()
        else:
            profile = __settings.getSetting("last_profile")
            notification(__language__(32033) % profile)
            ambibox.turnOn()
            ambibox.setProfile(profile)
        ambibox.unlock()


class XBMCDirect (threading.Thread):

    def __init__(self, infos, player):
        threading.Thread.__init__(self, name="XBMCDirect")
        self.infos = infos
        self.player = player
        self.running = False

    def start(self):
        self.running = True
        threading.Thread.start(self)

    def stop(self):
        self.running = False
        self.join(0.5)
        self.close()

    def close(self):
        pass

    def run(self):
        capture = xbmc.RenderCapture()
        width = self.infos[0]
        height = self.infos[1]
        ratio = self.infos[2]
        tw = capture.getHeight()
        th = capture.getWidth()
        tar = capture.getAspectRatio()
        if (width != 0 and height != 0 and ratio != 0):
            inimap = []
            self.player.inDataMap = mmap.mmap(0, width * height * 4 + 11, 'AmbiBox_XBMC_SharedMemory', mmap.ACCESS_WRITE)
            # get one frame to get length
            aax = 0
            while not self.player.isPlayingVideo():
                xbmc.sleep(100)
                continue
            for idx in xrange(1, 10):
                xbmc.sleep(100)
                capture.capture(width, height, xbmc.CAPTURE_FLAG_CONTINUOUS)
                capture.waitForCaptureStateChangeEvent(1000)
                aax = 0
                aax = capture.getCaptureState()
                if aax == xbmc.CAPTURE_STATE_FAILED:
                    capture = None
                    capture = xbmc.RenderCapture()
                elif aax == xbmc.CAPTURE_STATE_DONE:
                    break

            if aax != xbmc.CAPTURE_STATE_FAILED:
                inimap.append(chr(0))
                inimap.append(chr(width & 0xff))
                inimap.append(chr((width >> 8) & 0xff))
                # height
                inimap.append(chr(height & 0xff))
                inimap.append(chr((height >> 8) & 0xff))
                # aspect ratio
                inimap.append(chr(int(ratio * 100)))
                # image format
                fmt = capture.getImageFormat()
                if fmt == 'RGBA':
                    inimap.append(chr(0))
                elif fmt == 'BGRA':
                    inimap.append(chr(1))
                else:
                    inimap.append(chr(2))
                image = capture.getImage()
                length = len(image)
                # datasize
                inimap.append(chr(length & 0xff))
                inimap.append(chr((length >> 8) & 0xff))
                inimap.append(chr((length >> 16) & 0xff))
                inimap.append(chr((length >> 24) & 0xff))
                inimapstr = "".join(inimap)
                notification(__language__(32034))
                info('XBMCDirect capture initiated')

                capture.capture(width, height, xbmc.CAPTURE_FLAG_CONTINUOUS)

                while self.player.isPlayingVideo():
                    capture.waitForCaptureStateChangeEvent(1000)
                    if capture.getCaptureState() == xbmc.CAPTURE_STATE_DONE:
                        image = capture.getImage()
                        newlen = len(image)
                        self.player.inDataMap.seek(0)
                        seeked = self.player.inDataMap.read_byte()
                        if ord(seeked) == 248:  #check that XBMC Direct is running
                            if newlen != length:
                                length = newlen
                                inimapnew = inimap[0:6]
                                inimapnew.append(chr(length & 0xff))
                                inimapnew.append(chr((length >> 8) & 0xff))
                                inimapnew.append(chr((length >> 16) & 0xff))
                                inimapnew.append(chr((length >> 24) & 0xff))
                                inimapstr = "".join(inimapnew)
                            self.player.inDataMap[1:10] = inimapstr[1:10]
                            self.player.inDataMap[11:(11 + length)] = str(image)
                            # write first byte to indicate we finished writing the data
                            self.player.inDataMap[0] = (chr(240))
                self.player.inDataMap.close()
                self.player.inDataMap = None
            else:
                info('Capture failed')
                notification(__language__(32035))
        else:
            info("Error retrieving video file dimensions")


def SetAbxProfile(dar, vidfmt, player):
    __settings = xbmcaddon.Addon("script.ambibox")
    ambibox = AmbiBox.AmbiBox(__settings.getSetting("host"), int(__settings.getSetting("port")))
    ret = ""
    if ambibox.connect() == 0:
        pfls = ambibox.getProfiles()
        pname = GetProfileName(pfls, dar, vidfmt)
        player.setProfile('true', pname)
    return ret


def GetProfileName(pfls, DisplayAspectRatio, vidfmt):
    __settings = xbmcaddon.Addon("script.ambibox")
    fname = __data__ + '\\dardata.xml'
    if os.path.isfile(fname):
        try:
            doc = ElementTree.parse(fname)
        except:
            ret = __settings.getSetting("default_profile")
            return ret
        root = doc.getroot()
        apfls = root.findall('profile')
        ret = ""
        for apfl in apfls:
            aname = apfl.find('AmbiboxName').text
            strll = apfl.find('LowerLmt').text
            strul = apfl.find('UpperLmt').text
            try:
                strfmt = apfl.find('Format').text
            except:
                strfmt = "Normal"
            if strfmt != "SBS" and strfmt != "TAB":
                strfmt = "Normal"

            ll = float(strll)
            ul = float(strul)
            if (DisplayAspectRatio >= ll) and (DisplayAspectRatio <= ul) and (strfmt == vidfmt):
                ret = aname
                break
        if ret in pfls:
            return ret
        else:
            info("profile in xml not found by Ambibox")
            ret = __settings.getSetting("default_profile")
            return ret
    else:
        info("dardata.xml is missing")
        ret = __settings.getSetting("default_profile")
        return ret


def main():
    if ambibox.connect() == 0:
        notification(__language__(32030))
        info('Started - ver %s' % __version__)
        player = CapturePlayer()
        monitor = XbmcMonitor()
    else:
        notification(__language__(32031))
        player = None
        monitor = None

    while not xbmc.abortRequested:
        if player is None:
            xbmc.sleep(1000)
            if ambibox.connect() == 0:
                notification(__language__(32030))
                info('Started - ver %s' % __version__)
                player = CapturePlayer()
                monitor = XbmcMonitor()
        else:
            xbmc.sleep(100)

    if player is not None:
        # set off
        notification(__language__(32032))
        player.close()
        player = None
        monitor = None

main()
