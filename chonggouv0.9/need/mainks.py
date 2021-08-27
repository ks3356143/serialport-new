# -*- coding: utf-8 -*-
from PyQt5 import QtCore,QtWidgets,QtWebEngineWidgets
from PyQt5.QtWidgets import QMessageBox
import need.echarts
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
import json
import pandas as pd


class Mywin(QtWidgets.QWidget,need.echarts.Ui_Form):
    closesignal = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        super(Mywin,self).__init__()
        self.setupUi(self)
        self.initUI()
        self.setWindowTitle('测试平台遥测工具-子窗口')
        self.huitu = 1
        #获取主界面的变量表格(注意这里的self.df和以前不一样)
        self.df = pd.read_csv('varstatic.csv',encoding='gbk')

    def initUI(self):
        webSettings = QWebEngineSettings.globalSettings()
        webSettings.setAttribute(QWebEngineSettings.JavascriptEnabled,True)
        webSettings.setAttribute(QWebEngineSettings.PluginsEnabled,True)
        webSettings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows,True)
        
        self.webView = QtWebEngineWidgets.QWebEngineView()
        self.webView.load(QtCore.QUrl(QtCore.QFileInfo("ks001let.html").absoluteFilePath()))
        self.hLayout.addWidget(self.webView)
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.slotTimeout)
        self.pushButton.clicked.connect(self.slotBegin)
        self.pushButton_2.clicked.connect(self.slotPause)
        
    def slotTimeout(self,data_dict): #把这个当做槽函数，传来data_dict
        if self.huitu == 1:
            my_dict = data_dict
            lst_res = []
            keylist = []
            for key,value in my_dict.items():
                abuffer = {}
                #将改为中文名字
                CN_address = self.df.loc[self.df.address == key.lower(),'CN_name'].values[0]
                abuffer['name'] = CN_address
                abuffer['value'] = value
                keylist.append(CN_address)
                lst_res.append(abuffer)
                
            js  = "setValue({},{})".format(json.dumps(lst_res),keylist)
            self.webView.page().runJavaScript(js)
        
    def slotBegin(self):
        self.huitu = 1

    def slotPause(self):
        self.huitu = 0 #暂停绘图
    

    def closeEvent(self, event):
        reply = QMessageBox.question(self,'提示',"确认退出吗？",QMessageBox.Yes | QMessageBox.No,QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
        self.closesignal.emit()
        