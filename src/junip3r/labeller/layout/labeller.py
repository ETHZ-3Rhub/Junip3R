# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Labeller.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget)

from junip3r.labeller.widgets.editor import Editor

class Ui_Labeller(object):
    def setupUi(self, Labeller):
        if not Labeller.objectName():
            Labeller.setObjectName(u"Labeller")
        Labeller.resize(839, 566)
        Labeller.setWindowOpacity(1.000000000000000)
        self.actionFrom_Folder = QAction(Labeller)
        self.actionFrom_Folder.setObjectName(u"actionFrom_Folder")
        self.action_export_yolo_dataset = QAction(Labeller)
        self.action_export_yolo_dataset.setObjectName(u"action_export_yolo_dataset")
        self.action_open_project_setup = QAction(Labeller)
        self.action_open_project_setup.setObjectName(u"action_open_project_setup")
        self.action_open_frame_extractor = QAction(Labeller)
        self.action_open_frame_extractor.setObjectName(u"action_open_frame_extractor")
        self.action_export_as_yolo_dataset = QAction(Labeller)
        self.action_export_as_yolo_dataset.setObjectName(u"action_export_as_yolo_dataset")
        self.centralwidget = QWidget(Labeller)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(9, 0, 9, 0)
        self.stk_content = QStackedWidget(self.centralwidget)
        self.stk_content.setObjectName(u"stk_content")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.verticalLayout = QVBoxLayout(self.page)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.editor = Editor(self.page)
        self.editor.setObjectName(u"editor")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.editor.sizePolicy().hasHeightForWidth())
        self.editor.setSizePolicy(sizePolicy)
        self.editor.setMinimumSize(QSize(0, 0))
        self.editor.setStyleSheet(u"")

        self.verticalLayout.addWidget(self.editor)

        self.stk_content.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.verticalLayout_2 = QVBoxLayout(self.page_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.frame = QFrame(self.page_2)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(285, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.frame_2 = QFrame(self.frame)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.label = QLabel(self.frame_2)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignCenter)

        self.verticalLayout_3.addWidget(self.label)

        self.btn_open_frame_extractor = QPushButton(self.frame_2)
        self.btn_open_frame_extractor.setObjectName(u"btn_open_frame_extractor")

        self.verticalLayout_3.addWidget(self.btn_open_frame_extractor)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_2)


        self.horizontalLayout.addWidget(self.frame_2)

        self.horizontalSpacer_2 = QSpacerItem(285, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.verticalLayout_2.addWidget(self.frame)

        self.stk_content.addWidget(self.page_2)

        self.gridLayout.addWidget(self.stk_content, 0, 0, 1, 1)

        Labeller.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(Labeller)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 839, 22))
        self.menuWindow = QMenu(self.menubar)
        self.menuWindow.setObjectName(u"menuWindow")
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuExport_as = QMenu(self.menuFile)
        self.menuExport_as.setObjectName(u"menuExport_as")
        Labeller.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(Labeller)
        self.statusbar.setObjectName(u"statusbar")
        Labeller.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuWindow.menuAction())
        self.menuWindow.addAction(self.action_open_project_setup)
        self.menuWindow.addAction(self.action_open_frame_extractor)
        self.menuFile.addAction(self.menuExport_as.menuAction())
        self.menuExport_as.addAction(self.action_export_as_yolo_dataset)

        self.retranslateUi(Labeller)

        QMetaObject.connectSlotsByName(Labeller)
    # setupUi

    def retranslateUi(self, Labeller):
        Labeller.setWindowTitle(QCoreApplication.translate("Labeller", u"Junip3R", None))
#if QT_CONFIG(statustip)
        Labeller.setStatusTip("")
#endif // QT_CONFIG(statustip)
        self.actionFrom_Folder.setText(QCoreApplication.translate("Labeller", u"From Folder", None))
        self.action_export_yolo_dataset.setText(QCoreApplication.translate("Labeller", u"YOLO Dataset", None))
        self.action_open_project_setup.setText(QCoreApplication.translate("Labeller", u"Setup Project", None))
        self.action_open_frame_extractor.setText(QCoreApplication.translate("Labeller", u"Add Video Frames", None))
        self.action_export_as_yolo_dataset.setText(QCoreApplication.translate("Labeller", u"YOLO Training Dataset", None))
        self.label.setText(QCoreApplication.translate("Labeller", u"No images found in project folder", None))
        self.btn_open_frame_extractor.setText(QCoreApplication.translate("Labeller", u"Extract frames from videos", None))
        self.menuWindow.setTitle(QCoreApplication.translate("Labeller", u"Window", None))
        self.menuFile.setTitle(QCoreApplication.translate("Labeller", u"File", None))
        self.menuExport_as.setTitle(QCoreApplication.translate("Labeller", u"Export as...", None))
    # retranslateUi

