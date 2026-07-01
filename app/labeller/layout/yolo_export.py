# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'YOLOExport.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QSizePolicy,
    QSlider, QToolButton, QVBoxLayout, QWidget)

class Ui_DYOLOExport(object):
    def setupUi(self, DYOLOExport):
        if not DYOLOExport.objectName():
            DYOLOExport.setObjectName(u"DYOLOExport")
        DYOLOExport.resize(374, 327)
        self.verticalLayout = QVBoxLayout(DYOLOExport)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame = QFrame(DYOLOExport)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.formLayout = QFormLayout(self.frame)
        self.formLayout.setObjectName(u"formLayout")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.frame_2 = QFrame(self.frame)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.lbl_target_folder = QLabel(self.frame_2)
        self.lbl_target_folder.setObjectName(u"lbl_target_folder")

        self.horizontalLayout.addWidget(self.lbl_target_folder)

        self.btn_select_target_folder = QToolButton(self.frame_2)
        self.btn_select_target_folder.setObjectName(u"btn_select_target_folder")
        icon = QIcon(QIcon.fromTheme(u"folder"))
        self.btn_select_target_folder.setIcon(icon)

        self.horizontalLayout.addWidget(self.btn_select_target_folder)


        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.frame_2)

        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.dpd_split_by = QComboBox(self.frame)
        self.dpd_split_by.addItem("")
        self.dpd_split_by.addItem("")
        self.dpd_split_by.setObjectName(u"dpd_split_by")

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.dpd_split_by)

        self.frame_3 = QFrame(self.frame)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.lbl_num_train = QLabel(self.frame_3)
        self.lbl_num_train.setObjectName(u"lbl_num_train")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_num_train.sizePolicy().hasHeightForWidth())
        self.lbl_num_train.setSizePolicy(sizePolicy)
        self.lbl_num_train.setMinimumSize(QSize(60, 0))
        self.lbl_num_train.setMaximumSize(QSize(60, 16777215))

        self.horizontalLayout_2.addWidget(self.lbl_num_train)

        self.lbl_already_split = QLabel(self.frame_3)
        self.lbl_already_split.setObjectName(u"lbl_already_split")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lbl_already_split.sizePolicy().hasHeightForWidth())
        self.lbl_already_split.setSizePolicy(sizePolicy1)
        self.lbl_already_split.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_2.addWidget(self.lbl_already_split)

        self.sld_split = QSlider(self.frame_3)
        self.sld_split.setObjectName(u"sld_split")
        self.sld_split.setOrientation(Qt.Horizontal)

        self.horizontalLayout_2.addWidget(self.sld_split)

        self.lbl_num_val = QLabel(self.frame_3)
        self.lbl_num_val.setObjectName(u"lbl_num_val")
        sizePolicy.setHeightForWidth(self.lbl_num_val.sizePolicy().hasHeightForWidth())
        self.lbl_num_val.setSizePolicy(sizePolicy)
        self.lbl_num_val.setMinimumSize(QSize(60, 0))
        self.lbl_num_val.setMaximumSize(QSize(60, 16777215))
        self.lbl_num_val.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.lbl_num_val)


        self.formLayout.setWidget(3, QFormLayout.SpanningRole, self.frame_3)

        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.frame_4 = QFrame(self.frame)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.NoFrame)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.lbl_split_file = QLabel(self.frame_4)
        self.lbl_split_file.setObjectName(u"lbl_split_file")

        self.horizontalLayout_3.addWidget(self.lbl_split_file)

        self.btn_select_split_file = QToolButton(self.frame_4)
        self.btn_select_split_file.setObjectName(u"btn_select_split_file")
        icon1 = QIcon()
        iconThemeName = u"document-open"
        if QIcon.hasThemeIcon(iconThemeName):
            icon1 = QIcon.fromTheme(iconThemeName)
        else:
            icon1.addFile(u"../../../../../WINDOWS/system32", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.btn_select_split_file.setIcon(icon1)

        self.horizontalLayout_3.addWidget(self.btn_select_split_file)


        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.frame_4)


        self.verticalLayout.addWidget(self.frame)

        self.label_4 = QLabel(DYOLOExport)
        self.label_4.setObjectName(u"label_4")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy2)

        self.verticalLayout.addWidget(self.label_4)

        self.lst_instance_types = QListWidget(DYOLOExport)
        self.lst_instance_types.setObjectName(u"lst_instance_types")

        self.verticalLayout.addWidget(self.lst_instance_types)

        self.btnbox = QDialogButtonBox(DYOLOExport)
        self.btnbox.setObjectName(u"btnbox")
        self.btnbox.setOrientation(Qt.Horizontal)
        self.btnbox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.verticalLayout.addWidget(self.btnbox)


        self.retranslateUi(DYOLOExport)
        self.btnbox.accepted.connect(DYOLOExport.accept)
        self.btnbox.rejected.connect(DYOLOExport.reject)

        QMetaObject.connectSlotsByName(DYOLOExport)
    # setupUi

    def retranslateUi(self, DYOLOExport):
        DYOLOExport.setWindowTitle(QCoreApplication.translate("DYOLOExport", u"Export YOLO Dataset", None))
        self.label.setText(QCoreApplication.translate("DYOLOExport", u"Target Folder:", None))
        self.lbl_target_folder.setText(QCoreApplication.translate("DYOLOExport", u"Not Selected", None))
        self.btn_select_target_folder.setText(QCoreApplication.translate("DYOLOExport", u"...", None))
        self.label_3.setText(QCoreApplication.translate("DYOLOExport", u"Train/Val Split by:", None))
        self.dpd_split_by.setItemText(0, QCoreApplication.translate("DYOLOExport", u"Video", None))
        self.dpd_split_by.setItemText(1, QCoreApplication.translate("DYOLOExport", u"Image", None))

        self.lbl_num_train.setText(QCoreApplication.translate("DYOLOExport", u"Train 9", None))
        self.lbl_already_split.setText(QCoreApplication.translate("DYOLOExport", u"Set is already fully split", None))
        self.lbl_num_val.setText(QCoreApplication.translate("DYOLOExport", u"1 Val", None))
        self.label_2.setText(QCoreApplication.translate("DYOLOExport", u"Existing Split File:", None))
        self.lbl_split_file.setText(QCoreApplication.translate("DYOLOExport", u"Not Selected", None))
        self.btn_select_split_file.setText(QCoreApplication.translate("DYOLOExport", u"...", None))
        self.label_4.setText(QCoreApplication.translate("DYOLOExport", u"Instance Types", None))
    # retranslateUi

