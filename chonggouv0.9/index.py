# -*- coding: utf-8 -*-
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
import sys
from need.main import userMain
import qtmodern.styles
import qtmodern.windows


if __name__ == "__main__":
    #QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    win = userMain()

    qtmodern.styles.light(app) #还有dark可以选择
    mw = qtmodern.windows.ModernWindow(win)
    mw.show()
    '''
    #设置窗口有边框可拖动，但删除标题栏
    self.setWindowFlags(
    Qt.Window | Qt.CustomizeWindowHint | Qt.WindowSystemMenuHint)
    # win.show()
    '''
    sys.exit(app.exec_())

    '''
    lightPalette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Button, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.Light, QColor(0, 180, 180))
    lightPalette.setColor(QPalette.Midlight, QColor(21, 199, 240))
    lightPalette.setColor(QPalette.Dark, QColor(225, 225, 225))
    lightPalette.setColor(QPalette.Text, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.BrightText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Base, QColor(255, 255, 255))
    lightPalette.setColor(QPalette.Window, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.Shadow, QColor(20, 20, 20))
    lightPalette.setColor(QPalette.Highlight, QColor(76, 163, 224))
    lightPalette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    lightPalette.setColor(QPalette.Link, QColor(0, 162, 232))
    lightPalette.setColor(QPalette.AlternateBase, QColor(242, 247, 247))
    lightPalette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))
    lightPalette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    '''