# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect,
                            QSize)
from PySide6.QtGui import (QAction)
from PySide6.QtWidgets import (QGridLayout, QMenuBar,
                               QSizePolicy, QStatusBar, QWidget)

from app.labeller.widgets.label_editor import LabelEditor

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(844, 581)
        MainWindow.setWindowOpacity(1.000000000000000)
        self.actionFrom_Folder = QAction(MainWindow)
        self.actionFrom_Folder.setObjectName(u"actionFrom_Folder")
        self.action_export_yolo_dataset = QAction(MainWindow)
        self.action_export_yolo_dataset.setObjectName(u"action_export_yolo_dataset")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label_editor = LabelEditor(self.centralwidget)
        self.label_editor.setObjectName(u"label_editor")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.label_editor.sizePolicy().hasHeightForWidth())
        self.label_editor.setSizePolicy(sizePolicy)
        self.label_editor.setMinimumSize(QSize(0, 0))
        self.label_editor.setStyleSheet(u"")

        self.gridLayout.addWidget(self.label_editor, 1, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 844, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Labell3R", None))
#if QT_CONFIG(statustip)
        MainWindow.setStatusTip("")
#endif // QT_CONFIG(statustip)
        self.actionFrom_Folder.setText(QCoreApplication.translate("MainWindow", u"From Folder", None))
        self.action_export_yolo_dataset.setText(QCoreApplication.translate("MainWindow", u"YOLO Dataset", None))
    # retranslateUi

