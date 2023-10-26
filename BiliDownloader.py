from tkinter import SEL
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QFileDialog
from PyQt5.QtGui import QRegExpValidator, QValidator, QPixmap
from PyQt5.QtCore import QRegExp, pyqtSignal, QObject

from Ui_MainWindow import Ui_MainWindow
from Ui_Progress import Ui_Progress
from bilibili_api import video

import asyncio
import json
import requests
import os
import threading
from itertools import zip_longest



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
    
    progress_window = QWidget()
    progress_window_ui = Ui_Progress()
    
#signals:
    received_video_info = pyqtSignal()
    event_occured = pyqtSignal(str,str)
#public method:
    def __init__(self):
        super().__init__()
        self.__loop =  asyncio.get_event_loop()

        self.ui.setupUi(self.main_window)
        self.progress_window_ui.setupUi(self.progress_window)

        self.ui.downloadButton.clicked.connect(self.on_downloadButton_clicked)
        self.ui.downloadSaveAsButton.clicked.connect(self.on_downloadSaveAsButton_clicked)
        self.ui.showInfoButton.clicked.connect(self.on_showVideoInfoButton_Clicked)

        self.received_video_info.connect(self.__showVideoInfo)
        self.event_occured.connect(self.__log)

        self.ui.BVAVInput.setValidator(self.vid_validator)

    def run(self) -> int:
        self.main_window.show()
        return self.app.exec_()

    def debug(self):
        self.progress_window.show()

 #private method:       
    def __log(self, msg:str, error_level:str = None):
        if error_level == "error":
            self.ui.logBox.append("<font color=red>%s</font>"%msg)
        elif error_level == "warning":
            self.ui.logBox.append("<font color=#DB9724>%s</font>"%msg)
        elif error_level == "success":
            self.ui.logBox.append("<font color=#1F9104>%s</font>"%msg)
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
                self.video.set_bvid(vid)
            elif vid.startswith("av"):
                self.video.set_aid(int(vid[2:]))

        return True


    def __getVideoInfo(self):
        try:
           self.video_info = asyncio.run(self.video.get_info())
        except Exception as e:
            QMessageBox.critical(None , '错误', '出现错误，无法完成请求，请重试', QMessageBox.Yes)
            self.event_occured.emit("获取视频信息失败", "error")
            self.ui.showInfoButton.setEnabled(True)
            return
        self.event_occured.emit("获取视频信息成功", "success")
        self.received_video_info.emit()
    
    def __showVideoInfo(self):
        self.ui.VideoInfoBox.clear()
        self.ui.VideoInfoBox.append("<b>标题</b><br>%s"%(self.video_info["title"]))
        self.ui.VideoInfoBox.append("<b>UP主</b><br>%s"%(self.video_info["owner"]["name"]))
        self.ui.VideoInfoBox.append("<b>视频简介</b><br>%s"%(self.video_info["desc"]))

        self.ui.showInfoButton.setEnabled(True)
        self.ui.downloadButton.setEnabled(True)
        self.ui.downloadSaveAsButton.setEnabled(True)

    def __downloadVideo(self, save_path = os.getcwd() + "/downloads"):
        try:
            self.progress_window_ui.statusLabel.setText("正在获取下载链接...")
            url_data = asyncio.run(self.video.get_download_url(page_index=0))
            
            detecter = video.VideoDownloadURLDataDetecter(data=url_data)
            streams = detecter.detect_best_streams()
                
            
            self.progress_window_ui.statusLabel.setText("正在连接...")                       
                    
            
            video_response = requests.get(url=streams[0].url, headers=self.__http_headers, stream=True)
            audio_response = requests.get(url=streams[1].url, headers=self.__http_headers, stream=True)
            video_response.raise_for_status()
            audio_response.raise_for_status()
            
            video_total_size = int(video_response.headers.get("Content-Length", -1))
            video_downloaded_size = 0
            
            audio_total_size = int(audio_response.headers.get("Content-Length", -1))
            audio_downloaded_size = 0

            if not os.path.exists(save_path):
                os.mkdir(save_path)
                
            if os.path.exists(save_path + str(self.video.get_aid()) + "mp4"):
                self.event_occured.emit("文件已存在", "error")
                return False
            
            self.progress_window_ui.statusLabel.setText("正在下载...")
            
            video_file = open(save_path + "/%s_video.mps"%str(self.video.get_aid()), 'wb')
            audio_file = open(save_path + "/%s_audio.mps"%str(self.video.get_aid()), 'wb')
            for video_chunk,audio_chunk in zip_longest(video_response.iter_content(chunk_size=1024),audio_response.iter_content(chunk_size=1024)):
                if video_chunk:    
                    video_file.write(video_chunk)
                    video_downloaded_size += len(video_chunk)
                    progress = (video_downloaded_size // video_total_size) * 100
                    self.progress_window_ui.videoProgressBar.setValue(progress)
                if audio_chunk:
                    audio_file.write(audio_chunk)
                    audio_downloaded_size += len(audio_chunk)
                    progress = (audio_downloaded_size // audio_total_size) * 100
                    self.progress_window_ui.audioProgressBar.setValue(progress)
            
        except requests.exceptions.RequestException as e:
            self.event_occured.emit("下载失败，错误%s"%str(e), "error")
            video_file.close()
            audio_file.close()
            self.progress_window.close()
            return False
            
        self.progress_window.close()
        video_file.close()
        audio_file.close()
        self.event_occured.emit("下载完成", "success")
        return True

#slots:
    def on_showVideoInfoButton_Clicked(self):
        if not self.__setVideo():
            return
        
        self.ui.showInfoButton.setEnabled(False)
        self.__log("正在获取视频信息...")
        req_thread = threading.Thread(target=self.__getVideoInfo)
        req_thread.setDaemon(True)
        req_thread.start()
        
        
    def on_downloadButton_clicked(self):
        thread = threading.Thread(target=self.__downloadVideo)
        thread.setDaemon(True)
        thread.start()
        self.progress_window.show()
        self.__log("正在下载视频...")


    def on_downloadSaveAsButton_clicked(self):
        save_dir = QFileDialog.getExistingDirectory(None, "选择保存目录", os.getcwd())
        thread = threading.Thread(target=self.__downloadVideo,args=[save_dir])
        thread.setDaemon(True)
        thread.start()
        self.progress_window.show()
        self.__log("正在下载视频...")


    def on_actionAbout_triggered():
        pass


def main():
   bd = BiliDownloader()
   # bd.debug()
   return bd.run()

if __name__ == "__main__":
    exit(main())
