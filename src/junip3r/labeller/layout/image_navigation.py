# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ImageNavigation.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSlider, QVBoxLayout,
    QWidget)

class Ui_ImageNavigation(object):
    def setupUi(self, ImageNavigation):
        if not ImageNavigation.objectName():
            ImageNavigation.setObjectName(u"ImageNavigation")
        ImageNavigation.resize(398, 68)
        self.verticalLayout = QVBoxLayout(ImageNavigation)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.lbl_current_image = QLabel(ImageNavigation)
        self.lbl_current_image.setObjectName(u"lbl_current_image")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_current_image.sizePolicy().hasHeightForWidth())
        self.lbl_current_image.setSizePolicy(sizePolicy)
        self.lbl_current_image.setMinimumSize(QSize(0, 20))
        self.lbl_current_image.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout.addWidget(self.lbl_current_image)

        self.frame_3 = QFrame(ImageNavigation)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMinimumSize(QSize(0, 0))
        self.frame_3.setMaximumSize(QSize(16777215, 50))
        self.frame_3.setStyleSheet(u"")
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.lbl_image_number = QLabel(self.frame_3)
        self.lbl_image_number.setObjectName(u"lbl_image_number")

        self.horizontalLayout_2.addWidget(self.lbl_image_number)

        self.sld_image_number = QSlider(self.frame_3)
        self.sld_image_number.setObjectName(u"sld_image_number")
        self.sld_image_number.setOrientation(Qt.Horizontal)

        self.horizontalLayout_2.addWidget(self.sld_image_number)

        self.btn_previous_image = QPushButton(self.frame_3)
        self.btn_previous_image.setObjectName(u"btn_previous_image")

        self.horizontalLayout_2.addWidget(self.btn_previous_image)

        self.btn_next_image = QPushButton(self.frame_3)
        self.btn_next_image.setObjectName(u"btn_next_image")

        self.horizontalLayout_2.addWidget(self.btn_next_image)


        self.verticalLayout.addWidget(self.frame_3)


        self.retranslateUi(ImageNavigation)

        QMetaObject.connectSlotsByName(ImageNavigation)
    # setupUi

    def retranslateUi(self, ImageNavigation):
        ImageNavigation.setWindowTitle(QCoreApplication.translate("ImageNavigation", u"Form", None))
        self.lbl_current_image.setText(QCoreApplication.translate("ImageNavigation", u"TextLabel", None))
        self.lbl_image_number.setText(QCoreApplication.translate("ImageNavigation", u"1/100", None))
        self.btn_previous_image.setText(QCoreApplication.translate("ImageNavigation", u"Previous", None))
        self.btn_next_image.setText(QCoreApplication.translate("ImageNavigation", u"Next", None))
    # retranslateUi

