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
    QSpacerItem, QStackedWidget, QToolButton, QVBoxLayout,
    QWidget)

from junip3r.labeller.widgets.pose_image import PoseImage

class Ui_PoseEditor(object):
    def setupUi(self, PoseEditor):
        if not PoseEditor.objectName():
            PoseEditor.setObjectName(u"PoseEditor")
        PoseEditor.resize(505, 306)
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
        self.frm_post_processing.setStyleSheet(u"")
        self.frm_post_processing.setFrameShape(QFrame.NoFrame)
        self.frm_post_processing.setFrameShadow(QFrame.Plain)
        self.verticalLayout_4 = QVBoxLayout(self.frm_post_processing)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.frame_2 = QFrame(self.frm_post_processing)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy1)
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(9, 9, 9, 9)
        self.frm_post_processing_inner = QFrame(self.frame_2)
        self.frm_post_processing_inner.setObjectName(u"frm_post_processing_inner")
        sizePolicy1.setHeightForWidth(self.frm_post_processing_inner.sizePolicy().hasHeightForWidth())
        self.frm_post_processing_inner.setSizePolicy(sizePolicy1)
        self.frm_post_processing_inner.setMinimumSize(QSize(200, 0))
        self.frm_post_processing_inner.setMaximumSize(QSize(200, 16777215))
        self.frm_post_processing_inner.setStyleSheet(u"b")
        self.frm_post_processing_inner.setFrameShape(QFrame.NoFrame)
        self.frm_post_processing_inner.setFrameShadow(QFrame.Raised)
        self.formLayout = QFormLayout(self.frm_post_processing_inner)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
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

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)


        self.horizontalLayout.addWidget(self.frame)


        self.verticalLayout_4.addWidget(self.frame_2)


        self.gridLayout.addWidget(self.frm_post_processing, 0, 2, 1, 1, Qt.AlignTop)

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

        self.gridLayout.addWidget(self.pose_image, 0, 0, 2, 3)

        self.frm_context = QFrame(PoseEditor)
        self.frm_context.setObjectName(u"frm_context")
        sizePolicy.setHeightForWidth(self.frm_context.sizePolicy().hasHeightForWidth())
        self.frm_context.setSizePolicy(sizePolicy)
        self.frm_context.setStyleSheet(u"")
        self.frm_context.setFrameShape(QFrame.NoFrame)
        self.frm_context.setFrameShadow(QFrame.Plain)
        self.verticalLayout = QVBoxLayout(self.frm_context)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frm_context_inner = QFrame(self.frm_context)
        self.frm_context_inner.setObjectName(u"frm_context_inner")
        sizePolicy1.setHeightForWidth(self.frm_context_inner.sizePolicy().hasHeightForWidth())
        self.frm_context_inner.setSizePolicy(sizePolicy1)
        self.frm_context_inner.setFrameShape(QFrame.StyledPanel)
        self.frm_context_inner.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frm_context_inner)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(9, 9, 9, 9)
        self.stk_context = QStackedWidget(self.frm_context_inner)
        self.stk_context.setObjectName(u"stk_context")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.verticalLayout_5 = QVBoxLayout(self.page)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.frame_4 = QFrame(self.page)
        self.frame_4.setObjectName(u"frame_4")
        sizePolicy1.setHeightForWidth(self.frame_4.sizePolicy().hasHeightForWidth())
        self.frame_4.setSizePolicy(sizePolicy1)
        self.frame_4.setFrameShape(QFrame.NoFrame)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.frame_4)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_3.addWidget(self.label_3)

        self.lbl_context_pos = QLabel(self.frame_4)
        self.lbl_context_pos.setObjectName(u"lbl_context_pos")
        self.lbl_context_pos.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.lbl_context_pos)


        self.verticalLayout_5.addWidget(self.frame_4)

        self.frame_3 = QFrame(self.page)
        self.frame_3.setObjectName(u"frame_3")
        sizePolicy1.setHeightForWidth(self.frame_3.sizePolicy().hasHeightForWidth())
        self.frame_3.setSizePolicy(sizePolicy1)
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.lbl_context_min = QLabel(self.frame_3)
        self.lbl_context_min.setObjectName(u"lbl_context_min")

        self.horizontalLayout_2.addWidget(self.lbl_context_min)

        self.sld_context = QSlider(self.frame_3)
        self.sld_context.setObjectName(u"sld_context")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.sld_context.sizePolicy().hasHeightForWidth())
        self.sld_context.setSizePolicy(sizePolicy3)
        self.sld_context.setMinimumSize(QSize(50, 0))
        self.sld_context.setMinimum(-30)
        self.sld_context.setMaximum(30)
        self.sld_context.setOrientation(Qt.Horizontal)

        self.horizontalLayout_2.addWidget(self.sld_context)

        self.lbl_context_max = QLabel(self.frame_3)
        self.lbl_context_max.setObjectName(u"lbl_context_max")

        self.horizontalLayout_2.addWidget(self.lbl_context_max)


        self.verticalLayout_5.addWidget(self.frame_3)

        self.stk_context.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.verticalLayout_6 = QVBoxLayout(self.page_2)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label = QLabel(self.page_2)
        self.label.setObjectName(u"label")

        self.verticalLayout_6.addWidget(self.label)

        self.stk_context.addWidget(self.page_2)

        self.verticalLayout_3.addWidget(self.stk_context)


        self.verticalLayout.addWidget(self.frm_context_inner)


        self.gridLayout.addWidget(self.frm_context, 0, 0, 1, 1, Qt.AlignTop)

        self.pose_image.raise_()
        self.frm_context.raise_()
        self.frm_post_processing.raise_()

        self.retranslateUi(PoseEditor)

        self.stk_context.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(PoseEditor)
    # setupUi

    def retranslateUi(self, PoseEditor):
        PoseEditor.setWindowTitle(QCoreApplication.translate("PoseEditor", u"Form", None))
        self.label_4.setText(QCoreApplication.translate("PoseEditor", u"Brightness:", None))
        self.label_5.setText(QCoreApplication.translate("PoseEditor", u"Contrast:", None))
        self.btn_restore_preferences.setText("")
        self.pose_image.setText("")
        self.label_3.setText(QCoreApplication.translate("PoseEditor", u"Context", None))
        self.lbl_context_pos.setText(QCoreApplication.translate("PoseEditor", u"0", None))
        self.lbl_context_min.setText(QCoreApplication.translate("PoseEditor", u"-30", None))
        self.lbl_context_max.setText(QCoreApplication.translate("PoseEditor", u"30", None))
        self.label.setText(QCoreApplication.translate("PoseEditor", u"Loading context...", None))
    # retranslateUi

