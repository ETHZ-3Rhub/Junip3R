# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Editor.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QSizePolicy,
    QSplitter, QVBoxLayout, QWidget)

from junip3r.labeller.widgets.image_navigation import ImageNavigation
from junip3r.labeller.widgets.pose_editor import PoseEditor
from junip3r.labeller.widgets.selection_controls import SelectionControls

class Ui_Editor(object):
    def setupUi(self, Editor):
        if not Editor.objectName():
            Editor.setObjectName(u"Editor")
        Editor.resize(686, 407)
        Editor.setStyleSheet(u"")
        self.action_export_yolo_dataset = QAction(Editor)
        self.action_export_yolo_dataset.setObjectName(u"action_export_yolo_dataset")
        self.horizontalLayout = QHBoxLayout(Editor)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Editor)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.frame = QFrame(self.splitter)
        self.frame.setObjectName(u"frame")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_2 = QFrame(self.frame)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.pose_editor = PoseEditor(self.frame_2)
        self.pose_editor.setObjectName(u"pose_editor")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.pose_editor.sizePolicy().hasHeightForWidth())
        self.pose_editor.setSizePolicy(sizePolicy1)

        self.verticalLayout_2.addWidget(self.pose_editor)


        self.verticalLayout.addWidget(self.frame_2)

        self.image_navigation = ImageNavigation(self.frame)
        self.image_navigation.setObjectName(u"image_navigation")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.image_navigation.sizePolicy().hasHeightForWidth())
        self.image_navigation.setSizePolicy(sizePolicy2)

        self.verticalLayout.addWidget(self.image_navigation)

        self.splitter.addWidget(self.frame)
        self.selection_controls = SelectionControls(self.splitter)
        self.selection_controls.setObjectName(u"selection_controls")
        self.splitter.addWidget(self.selection_controls)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(Editor)

        QMetaObject.connectSlotsByName(Editor)
    # setupUi

    def retranslateUi(self, Editor):
        Editor.setWindowTitle("")
        self.action_export_yolo_dataset.setText(QCoreApplication.translate("Editor", u"Export YOLO Dataset", None))
    # retranslateUi

