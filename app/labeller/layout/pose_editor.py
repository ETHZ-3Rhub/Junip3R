# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PoseEditor.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QGridLayout,
    QLabel, QSizePolicy, QSlider, QWidget)

from app.labeller.widgets.pose_image import PoseImage

class Ui_PoseEditor(object):
    def setupUi(self, PoseEditor):
        if not PoseEditor.objectName():
            PoseEditor.setObjectName(u"PoseEditor")
        PoseEditor.resize(413, 300)
        self.gridLayout = QGridLayout(PoseEditor)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.frm_post_processing = QFrame(PoseEditor)
        self.frm_post_processing.setObjectName(u"frm_post_processing")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frm_post_processing.sizePolicy().hasHeightForWidth())
        self.frm_post_processing.setSizePolicy(sizePolicy)
        self.frm_post_processing.setMinimumSize(QSize(200, 50))
        self.frm_post_processing.setMaximumSize(QSize(200, 16777215))
        self.frm_post_processing.setFrameShape(QFrame.StyledPanel)
        self.frm_post_processing.setFrameShadow(QFrame.Raised)
        self.formLayout = QFormLayout(self.frm_post_processing)
        self.formLayout.setObjectName(u"formLayout")
        self.label_4 = QLabel(self.frm_post_processing)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_4)

        self.sld_brightness = QSlider(self.frm_post_processing)
        self.sld_brightness.setObjectName(u"sld_brightness")
        self.sld_brightness.setOrientation(Qt.Horizontal)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.sld_brightness)

        self.label_5 = QLabel(self.frm_post_processing)
        self.label_5.setObjectName(u"label_5")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_5)

        self.sld_contrast = QSlider(self.frm_post_processing)
        self.sld_contrast.setObjectName(u"sld_contrast")
        self.sld_contrast.setOrientation(Qt.Horizontal)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.sld_contrast)

        self.lbl_overlay = QLabel(self.frm_post_processing)
        self.lbl_overlay.setObjectName(u"lbl_overlay")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.lbl_overlay)

        self.sld_overlay = QSlider(self.frm_post_processing)
        self.sld_overlay.setObjectName(u"sld_overlay")
        self.sld_overlay.setMaximum(100)
        self.sld_overlay.setSingleStep(1)
        self.sld_overlay.setOrientation(Qt.Horizontal)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.sld_overlay)


        self.gridLayout.addWidget(self.frm_post_processing, 0, 1, 1, 1)

        self.pose_image = PoseImage(PoseEditor)
        self.pose_image.setObjectName(u"pose_image")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.pose_image.sizePolicy().hasHeightForWidth())
        self.pose_image.setSizePolicy(sizePolicy1)
        self.pose_image.setMinimumSize(QSize(100, 100))
        self.pose_image.setStyleSheet(u"")
        self.pose_image.setScaledContents(True)
        self.pose_image.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.gridLayout.addWidget(self.pose_image, 0, 0, 2, 1)


        self.retranslateUi(PoseEditor)

        QMetaObject.connectSlotsByName(PoseEditor)
    # setupUi

    def retranslateUi(self, PoseEditor):
        PoseEditor.setWindowTitle(QCoreApplication.translate("PoseEditor", u"Form", None))
        self.label_4.setText(QCoreApplication.translate("PoseEditor", u"Brightness:", None))
        self.label_5.setText(QCoreApplication.translate("PoseEditor", u"Contrast:", None))
        self.lbl_overlay.setText(QCoreApplication.translate("PoseEditor", u"Overlay:", None))
        self.pose_image.setText("")
    # retranslateUi

