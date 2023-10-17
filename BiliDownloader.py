from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtGui import QRegExpValidator, QValidator, QPixmap
from PyQt5.QtCore import QRegExp, pyqtSignal, QObject

from Ui_MainWindow import Ui_MainWindow
from bilibili_api import video

import asyncio
import json
import requests
import os
import threading



class BiliDownloader(QObject):

#private variable:    
    __http_headers = {
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0"
    }
#public variable:    
    video = None
    video_info = None
    app = QApplication([])
    main_window = QMainWindow()
    vid_validator = QRegExpValidator(QRegExp(r'(av\d+)|(BV1[0-9a-zA-Z]{9})'))
    ui = Ui_MainWindow()

#signals:
    received_video_info = pyqtSignal()
#public method:
    def __init__(self):
        super().__init__()
        self.__loop =  asyncio.get_event_loop()

        self.ui.setupUi(self.main_window)

        self.ui.downloadButton.clicked.connect(self.on_downloadButton_clicked)
        self.ui.downloadSaveAsButton.clicked.connect(self.on_downloadSaveAsButton_clicked)
        self.ui.showInfoButton.clicked.connect(self.on_showVideoInfoButton_Clicked)

        self.received_video_info.connect(self.__showVideoInfo)

        self.ui.BVAVInput.setValidator(self.vid_validator)

    def run(self) -> int:
        self.main_window.show()
        return self.app.exec_()

    def debug(self):
        print("Hello")
        self.__log("123321")
        print(self.video.get_bvid())

 #private method:       
    def __log(self, msg:str, error_level:str = None):
        if error_level == "error":
            self.ui.logBox.append("<font color=red>%s</font>"%msg)
        elif error_level == "warning":
            self.ui.logBox.append("<font color=#DB9724>%s</font>"%msg)
        else:
            self.ui.logBox.append(msg)


    def __vidVaildate(self, vid:str) -> bool:
        return self.vid_validator.validate(vid, 0)[0] == QValidator.State.Acceptable

    def __setVideo(self) -> bool:
        vid = self.ui.BVAVInput.text()

        if not self.__vidVaildate(vid):
            QMessageBox.critical(self.main_window, '错误', '输入的av/BV号格式不正确', QMessageBox.Yes)
            return False

        if self.video is None:
            if vid.startswith("BV"):
                self.video = video.Video(bvid=vid)
            elif vid.startswith("av"):
                 self.video = video.Video(aid=int(vid[2:]))
        else:
            if vid.startswith("BV"):
                self.video.set_bvid(vid.text())
            elif vid.startswith("av"):
                self.video.set_aid(int(vid[2:]))

        return True


    def __getVideoInfo(self):
        try:
           self.video_info = asyncio.run(self.video.get_info())
        except Exception as e:
            QMessageBox.critical(self.main_window , '错误', '出现错误，无法完成请求，请重试', QMessageBox.Yes)
            self.__log(e, "error")
            self.ui.showInfoButton.setEnabled(True)
        self.received_video_info.emit()
    
    def __showVideoInfo(self):
        self.ui.VideoInfoBox.clear()
        self.ui.VideoInfoBox.append("<b>标题</b><br>%s"%(self.video_info["title"]))
        self.ui.VideoInfoBox.append("<b>UP主</b><br>%s"%(self.video_info["owner"]["name"]))
        self.ui.VideoInfoBox.append("<b>视频简介</b><br>%s"%(self.video_info["desc"]))

        self.ui.showInfoButton.setEnabled(True)
        self.ui.downloadButton.setEnabled(True)
        self.ui.downloadSaveAsButton.setEnabled(True)

#slots:
    def on_showVideoInfoButton_Clicked(self):
        if not self.__setVideo():
            return
        
        self.ui.showInfoButton.setEnabled(False)
        self.__log("正在获取视频信息...")
        req_thread = threading.Thread(target=self.__getVideoInfo)
        req_thread.setDaemon(True)
        req_thread.start()
        
        
    def on_downloadButton_clicked():
        pass


    def on_downloadSaveAsButton_clicked():
        pass


    def on_actionAbout_triggered():
        pass


def main():
   bd = BiliDownloader()
   return bd.run()

if __name__ == "__main__":
    exit(main())