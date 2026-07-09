# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'PoseEditor.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QSizePolicy, QSlider,
    QSpacerItem, QToolButton, QVBoxLayout, QWidget)

from junip3r.labeller.widgets.pose_image import PoseImage

class Ui_PoseEditor(object):
    def setupUi(self, PoseEditor):
        if not PoseEditor.objectName():
            PoseEditor.setObjectName(u"PoseEditor")
        PoseEditor.resize(411, 300)
        self.gridLayout = QGridLayout(PoseEditor)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.frm_post_processing = QFrame(PoseEditor)
        self.frm_post_processing.setObjectName(u"frm_post_processing")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frm_post_processing.sizePolicy().hasHeightForWidth())
        self.frm_post_processing.setSizePolicy(sizePolicy)
        self.frm_post_processing.setFrameShape(QFrame.NoFrame)
        self.frm_post_processing.setFrameShadow(QFrame.Plain)
        self.horizontalLayout_4 = QHBoxLayout(self.frm_post_processing)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.frame_2 = QFrame(self.frm_post_processing)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(9, 9, 9, 0)
        self.frm_post_processing_inner = QFrame(self.frame_2)
        self.frm_post_processing_inner.setObjectName(u"frm_post_processing_inner")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frm_post_processing_inner.sizePolicy().hasHeightForWidth())
        self.frm_post_processing_inner.setSizePolicy(sizePolicy1)
        self.frm_post_processing_inner.setMinimumSize(QSize(200, 50))
        self.frm_post_processing_inner.setMaximumSize(QSize(200, 16777215))
        self.frm_post_processing_inner.setFrameShape(QFrame.NoFrame)
        self.frm_post_processing_inner.setFrameShadow(QFrame.Raised)
        self.formLayout = QFormLayout(self.frm_post_processing_inner)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, -1)
        self.label_4 = QLabel(self.frm_post_processing_inner)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.sld_brightness = QSlider(self.frm_post_processing_inner)
        self.sld_brightness.setObjectName(u"sld_brightness")
        self.sld_brightness.setOrientation(Qt.Horizontal)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.sld_brightness)

        self.label_5 = QLabel(self.frm_post_processing_inner)
        self.label_5.setObjectName(u"label_5")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_5)

        self.sld_contrast = QSlider(self.frm_post_processing_inner)
        self.sld_contrast.setObjectName(u"sld_contrast")
        self.sld_contrast.setOrientation(Qt.Horizontal)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.sld_contrast)

        self.lbl_overlay = QLabel(self.frm_post_processing_inner)
        self.lbl_overlay.setObjectName(u"lbl_overlay")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_overlay)

        self.sld_overlay = QSlider(self.frm_post_processing_inner)
        self.sld_overlay.setObjectName(u"sld_overlay")
        self.sld_overlay.setMaximum(100)
        self.sld_overlay.setSingleStep(1)
        self.sld_overlay.setOrientation(Qt.Horizontal)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.sld_overlay)


        self.horizontalLayout.addWidget(self.frm_post_processing_inner)

        self.frame = QFrame(self.frame_2)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.btn_restore_preferences = QToolButton(self.frame)
        self.btn_restore_preferences.setObjectName(u"btn_restore_preferences")
        self.btn_restore_preferences.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_restore_preferences.setStyleSheet(u"border:none;\n"
"background-color:none;")
        icon = QIcon()
        iconThemeName = u"view-restore"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u".", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.btn_restore_preferences.setIcon(icon)

        self.verticalLayout_2.addWidget(self.btn_restore_preferences)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)


        self.horizontalLayout.addWidget(self.frame)


        self.horizontalLayout_4.addWidget(self.frame_2)


        self.gridLayout.addWidget(self.frm_post_processing, 0, 1, 1, 1)

        self.pose_image = PoseImage(PoseEditor)
        self.pose_image.setObjectName(u"pose_image")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.pose_image.sizePolicy().hasHeightForWidth())
        self.pose_image.setSizePolicy(sizePolicy2)
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
        self.btn_restore_preferences.setText("")
        self.pose_image.setText("")
    # retranslateUi

