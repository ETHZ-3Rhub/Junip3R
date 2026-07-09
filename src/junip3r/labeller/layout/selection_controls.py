# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SelectionControls.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
    QLabel, QListView, QSizePolicy, QSplitter,
    QVBoxLayout, QWidget)

class Ui_SelectionControls(object):
    def setupUi(self, SelectionControls):
        if not SelectionControls.objectName():
            SelectionControls.setObjectName(u"SelectionControls")
        SelectionControls.resize(267, 662)
        self.verticalLayout = QVBoxLayout(SelectionControls)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.splt_right = QSplitter(SelectionControls)
        self.splt_right.setObjectName(u"splt_right")
        self.splt_right.setOrientation(Qt.Vertical)
        self.splt_right.setChildrenCollapsible(False)
        self.frm_tag_list = QFrame(self.splt_right)
        self.frm_tag_list.setObjectName(u"frm_tag_list")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(4)
        sizePolicy.setHeightForWidth(self.frm_tag_list.sizePolicy().hasHeightForWidth())
        self.frm_tag_list.setSizePolicy(sizePolicy)
        self.frm_tag_list.setFrameShape(QFrame.NoFrame)
        self.frm_tag_list.setFrameShadow(QFrame.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frm_tag_list)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.lbl_tag_list = QLabel(self.frm_tag_list)
        self.lbl_tag_list.setObjectName(u"lbl_tag_list")
        font = QFont()
        font.setPointSize(12)
        self.lbl_tag_list.setFont(font)

        self.verticalLayout_7.addWidget(self.lbl_tag_list)

        self.lst_tags = QListView(self.frm_tag_list)
        self.lst_tags.setObjectName(u"lst_tags")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.lst_tags.sizePolicy().hasHeightForWidth())
        self.lst_tags.setSizePolicy(sizePolicy1)
        self.lst_tags.setMinimumSize(QSize(150, 0))
        self.lst_tags.setMaximumSize(QSize(16777215, 16777215))
        self.lst_tags.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.verticalLayout_7.addWidget(self.lst_tags)

        self.splt_right.addWidget(self.frm_tag_list)
        self.frm_instance_list = QFrame(self.splt_right)
        self.frm_instance_list.setObjectName(u"frm_instance_list")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(10)
        sizePolicy2.setHeightForWidth(self.frm_instance_list.sizePolicy().hasHeightForWidth())
        self.frm_instance_list.setSizePolicy(sizePolicy2)
        self.frm_instance_list.setFrameShape(QFrame.NoFrame)
        self.frm_instance_list.setFrameShadow(QFrame.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.frm_instance_list)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.lbl_instance_list = QLabel(self.frm_instance_list)
        self.lbl_instance_list.setObjectName(u"lbl_instance_list")
        self.lbl_instance_list.setFont(font)

        self.verticalLayout_4.addWidget(self.lbl_instance_list)

        self.lst_instances = QListView(self.frm_instance_list)
        self.lst_instances.setObjectName(u"lst_instances")
        sizePolicy1.setHeightForWidth(self.lst_instances.sizePolicy().hasHeightForWidth())
        self.lst_instances.setSizePolicy(sizePolicy1)
        self.lst_instances.setMinimumSize(QSize(150, 0))
        self.lst_instances.setMaximumSize(QSize(16777215, 16777215))
        self.lst_instances.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.verticalLayout_4.addWidget(self.lst_instances)

        self.splt_right.addWidget(self.frm_instance_list)
        self.frame_5 = QFrame(self.splt_right)
        self.frame_5.setObjectName(u"frame_5")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.frame_5.sizePolicy().hasHeightForWidth())
        self.frame_5.setSizePolicy(sizePolicy3)
        self.frame_5.setFrameShape(QFrame.NoFrame)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame_5)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.frame_5)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font)

        self.verticalLayout_5.addWidget(self.label_2)

        self.dpd_instance_type = QComboBox(self.frame_5)
        self.dpd_instance_type.addItem("")
        self.dpd_instance_type.addItem("")
        self.dpd_instance_type.setObjectName(u"dpd_instance_type")
        self.dpd_instance_type.setFont(font)

        self.verticalLayout_5.addWidget(self.dpd_instance_type)

        self.splt_right.addWidget(self.frame_5)
        self.frame_6 = QFrame(self.splt_right)
        self.frame_6.setObjectName(u"frame_6")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(15)
        sizePolicy4.setHeightForWidth(self.frame_6.sizePolicy().hasHeightForWidth())
        self.frame_6.setSizePolicy(sizePolicy4)
        self.frame_6.setFrameShape(QFrame.NoFrame)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.frame_6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.frame_6)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font)

        self.verticalLayout_6.addWidget(self.label_3)

        self.lst_points = QListView(self.frame_6)
        self.lst_points.setObjectName(u"lst_points")
        sizePolicy1.setHeightForWidth(self.lst_points.sizePolicy().hasHeightForWidth())
        self.lst_points.setSizePolicy(sizePolicy1)
        self.lst_points.setMinimumSize(QSize(150, 0))
        self.lst_points.setMaximumSize(QSize(16777215, 16777215))
        self.lst_points.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalLayout_6.addWidget(self.lst_points)

        self.splt_right.addWidget(self.frame_6)

        self.verticalLayout.addWidget(self.splt_right)


        self.retranslateUi(SelectionControls)

        QMetaObject.connectSlotsByName(SelectionControls)
    # setupUi

    def retranslateUi(self, SelectionControls):
        SelectionControls.setWindowTitle(QCoreApplication.translate("SelectionControls", u"Form", None))
        self.lbl_tag_list.setText(QCoreApplication.translate("SelectionControls", u"Image Tags:", None))
        self.lbl_instance_list.setText(QCoreApplication.translate("SelectionControls", u"Instances:", None))
        self.label_2.setText(QCoreApplication.translate("SelectionControls", u"Instance Type:", None))
        self.dpd_instance_type.setItemText(0, QCoreApplication.translate("SelectionControls", u"Face", None))
        self.dpd_instance_type.setItemText(1, QCoreApplication.translate("SelectionControls", u"Box", None))

        self.label_3.setText(QCoreApplication.translate("SelectionControls", u"Points:", None))
    # retranslateUi

