# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Editor.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt)
from PySide6.QtGui import (QAction, QFont)
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFormLayout,
                               QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLayout, QListView, QPushButton, QSizePolicy,
                               QSlider, QSplitter, QVBoxLayout)

from junip3r.labeller.widgets.pose_image import PoseImage

class Ui_LabelEditor(object):
    def setupUi(self, LabelEditor):
        if not LabelEditor.objectName():
            LabelEditor.setObjectName(u"LabelEditor")
        LabelEditor.resize(1425, 891)
        LabelEditor.setStyleSheet(u"")
        self.action_export_yolo_dataset = QAction(LabelEditor)
        self.action_export_yolo_dataset.setObjectName(u"action_export_yolo_dataset")
        self.gridLayout = QGridLayout(LabelEditor)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter = QSplitter(LabelEditor)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setOpaqueResize(True)
        self.splitter.setChildrenCollapsible(False)
        self.frame = QFrame(self.splitter)
        self.frame.setObjectName(u"frame")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame.sizePolicy().hasHeightForWidth())
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setMinimumSize(QSize(0, 0))
        self.frame.setStyleSheet(u"")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.frm_editor = QFrame(self.frame)
        self.frm_editor.setObjectName(u"frm_editor")
        self.frm_editor.setFrameShape(QFrame.StyledPanel)
        self.frm_editor.setFrameShadow(QFrame.Raised)
        self.gridLayout_2 = QGridLayout(self.frm_editor)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.pose_image = PoseImage(self.frm_editor)
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

        self.gridLayout_2.addWidget(self.pose_image, 0, 0, 2, 1)

        self.frm_post_processing = QFrame(self.frm_editor)
        self.frm_post_processing.setObjectName(u"frm_post_processing")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.frm_post_processing.sizePolicy().hasHeightForWidth())
        self.frm_post_processing.setSizePolicy(sizePolicy2)
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


        self.gridLayout_2.addWidget(self.frm_post_processing, 0, 1, 1, 1)


        self.verticalLayout_2.addWidget(self.frm_editor)

        self.lbl_current_image = QLabel(self.frame)
        self.lbl_current_image.setObjectName(u"lbl_current_image")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lbl_current_image.sizePolicy().hasHeightForWidth())
        self.lbl_current_image.setSizePolicy(sizePolicy3)
        self.lbl_current_image.setMinimumSize(QSize(0, 20))
        self.lbl_current_image.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout_2.addWidget(self.lbl_current_image)

        self.frame_3 = QFrame(self.frame)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMinimumSize(QSize(0, 0))
        self.frame_3.setMaximumSize(QSize(16777215, 50))
        self.frame_3.setStyleSheet(u"")
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
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


        self.verticalLayout_2.addWidget(self.frame_3)

        self.splitter.addWidget(self.frame)
        self.frame_2 = QFrame(self.splitter)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy1.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy1)
        self.frame_2.setBaseSize(QSize(0, 0))
        font = QFont()
        font.setPointSize(12)
        self.frame_2.setFont(font)
        self.frame_2.setStyleSheet(u"")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame_2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.splt_right = QSplitter(self.frame_2)
        self.splt_right.setObjectName(u"splt_right")
        self.splt_right.setOrientation(Qt.Vertical)
        self.splt_right.setChildrenCollapsible(False)
        self.frm_tag_list = QFrame(self.splt_right)
        self.frm_tag_list.setObjectName(u"frm_tag_list")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(4)
        sizePolicy4.setHeightForWidth(self.frm_tag_list.sizePolicy().hasHeightForWidth())
        self.frm_tag_list.setSizePolicy(sizePolicy4)
        self.frm_tag_list.setFrameShape(QFrame.NoFrame)
        self.frm_tag_list.setFrameShadow(QFrame.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frm_tag_list)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.lbl_tag_list = QLabel(self.frm_tag_list)
        self.lbl_tag_list.setObjectName(u"lbl_tag_list")
        self.lbl_tag_list.setFont(font)

        self.verticalLayout_7.addWidget(self.lbl_tag_list)

        self.lst_tags = QListView(self.frm_tag_list)
        self.lst_tags.setObjectName(u"lst_tags")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(1)
        sizePolicy5.setHeightForWidth(self.lst_tags.sizePolicy().hasHeightForWidth())
        self.lst_tags.setSizePolicy(sizePolicy5)
        self.lst_tags.setMinimumSize(QSize(150, 0))
        self.lst_tags.setMaximumSize(QSize(16777215, 16777215))
        self.lst_tags.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.verticalLayout_7.addWidget(self.lst_tags)

        self.splt_right.addWidget(self.frm_tag_list)
        self.frm_instance_list = QFrame(self.splt_right)
        self.frm_instance_list.setObjectName(u"frm_instance_list")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(10)
        sizePolicy6.setHeightForWidth(self.frm_instance_list.sizePolicy().hasHeightForWidth())
        self.frm_instance_list.setSizePolicy(sizePolicy6)
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
        sizePolicy5.setHeightForWidth(self.lst_instances.sizePolicy().hasHeightForWidth())
        self.lst_instances.setSizePolicy(sizePolicy5)
        self.lst_instances.setMinimumSize(QSize(150, 0))
        self.lst_instances.setMaximumSize(QSize(16777215, 16777215))
        self.lst_instances.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.verticalLayout_4.addWidget(self.lst_instances)

        self.splt_right.addWidget(self.frm_instance_list)
        self.frame_5 = QFrame(self.splt_right)
        self.frame_5.setObjectName(u"frame_5")
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

        self.verticalLayout_5.addWidget(self.dpd_instance_type)

        self.splt_right.addWidget(self.frame_5)
        self.frame_6 = QFrame(self.splt_right)
        self.frame_6.setObjectName(u"frame_6")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(15)
        sizePolicy7.setHeightForWidth(self.frame_6.sizePolicy().hasHeightForWidth())
        self.frame_6.setSizePolicy(sizePolicy7)
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
        sizePolicy5.setHeightForWidth(self.lst_points.sizePolicy().hasHeightForWidth())
        self.lst_points.setSizePolicy(sizePolicy5)
        self.lst_points.setMinimumSize(QSize(150, 0))
        self.lst_points.setMaximumSize(QSize(16777215, 16777215))
        self.lst_points.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalLayout_6.addWidget(self.lst_points)

        self.splt_right.addWidget(self.frame_6)

        self.verticalLayout.addWidget(self.splt_right)

        self.splitter.addWidget(self.frame_2)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)


        self.retranslateUi(LabelEditor)

        QMetaObject.connectSlotsByName(LabelEditor)
    # setupUi

    def retranslateUi(self, LabelEditor):
        LabelEditor.setWindowTitle("")
        self.action_export_yolo_dataset.setText(QCoreApplication.translate("LabelEditor", u"Export YOLO Dataset", None))
        self.pose_image.setText("")
        self.label_4.setText(QCoreApplication.translate("LabelEditor", u"Brightness:", None))
        self.label_5.setText(QCoreApplication.translate("LabelEditor", u"Contrast:", None))
        self.lbl_overlay.setText(QCoreApplication.translate("LabelEditor", u"Overlay:", None))
        self.lbl_current_image.setText(QCoreApplication.translate("LabelEditor", u"TextLabel", None))
        self.lbl_image_number.setText(QCoreApplication.translate("LabelEditor", u"1/100", None))
        self.btn_previous_image.setText(QCoreApplication.translate("LabelEditor", u"Previous", None))
        self.btn_next_image.setText(QCoreApplication.translate("LabelEditor", u"Next", None))
        self.lbl_tag_list.setText(QCoreApplication.translate("LabelEditor", u"Image Tags:", None))
        self.lbl_instance_list.setText(QCoreApplication.translate("LabelEditor", u"Instances:", None))
        self.label_2.setText(QCoreApplication.translate("LabelEditor", u"Instance Type:", None))
        self.dpd_instance_type.setItemText(0, QCoreApplication.translate("LabelEditor", u"Face", None))
        self.dpd_instance_type.setItemText(1, QCoreApplication.translate("LabelEditor", u"Box", None))

        self.label_3.setText(QCoreApplication.translate("LabelEditor", u"Points:", None))
    # retranslateUi

