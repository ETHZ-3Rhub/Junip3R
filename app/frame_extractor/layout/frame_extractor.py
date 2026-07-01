# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'FrameExtractor.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLayout, QListView, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QSlider,
    QSpinBox, QSplitter, QStatusBar, QVBoxLayout,
    QWidget)

class Ui_FrameExtractor(object):
    def setupUi(self, FrameExtractor):
        if not FrameExtractor.objectName():
            FrameExtractor.setObjectName(u"FrameExtractor")
        FrameExtractor.resize(1089, 703)
        FrameExtractor.setAcceptDrops(True)
        self.action_open_labeller = QAction(FrameExtractor)
        self.action_open_labeller.setObjectName(u"action_open_labeller")
        self.centralwidget = QWidget(FrameExtractor)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.frame = QFrame(self.splitter)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 0))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")

        self.verticalLayout_2.addWidget(self.label)

        self.btn_add_videos = QPushButton(self.frame)
        self.btn_add_videos.setObjectName(u"btn_add_videos")

        self.verticalLayout_2.addWidget(self.btn_add_videos)

        self.lst_videos = QListView(self.frame)
        self.lst_videos.setObjectName(u"lst_videos")
        self.lst_videos.setAcceptDrops(True)
        self.lst_videos.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.lst_videos.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.verticalLayout_2.addWidget(self.lst_videos)

        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout_2.addWidget(self.label_4)

        self.frame_7 = QFrame(self.frame)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.NoFrame)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.gridLayout_4 = QGridLayout(self.frame_7)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.dpd_num_frames_mode = QComboBox(self.frame_7)
        self.dpd_num_frames_mode.addItem("")
        self.dpd_num_frames_mode.addItem("")
        self.dpd_num_frames_mode.setObjectName(u"dpd_num_frames_mode")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dpd_num_frames_mode.sizePolicy().hasHeightForWidth())
        self.dpd_num_frames_mode.setSizePolicy(sizePolicy)

        self.gridLayout_4.addWidget(self.dpd_num_frames_mode, 1, 1, 1, 1)

        self.spb_num_frames = QSpinBox(self.frame_7)
        self.spb_num_frames.setObjectName(u"spb_num_frames")
        self.spb_num_frames.setMaximum(1000)
        self.spb_num_frames.setValue(10)

        self.gridLayout_4.addWidget(self.spb_num_frames, 1, 0, 1, 1)

        self.dpd_target_videos_mode = QComboBox(self.frame_7)
        self.dpd_target_videos_mode.addItem("")
        self.dpd_target_videos_mode.addItem("")
        self.dpd_target_videos_mode.addItem("")
        self.dpd_target_videos_mode.setObjectName(u"dpd_target_videos_mode")

        self.gridLayout_4.addWidget(self.dpd_target_videos_mode, 2, 0, 1, 2)

        self.btn_select_frames = QPushButton(self.frame_7)
        self.btn_select_frames.setObjectName(u"btn_select_frames")

        self.gridLayout_4.addWidget(self.btn_select_frames, 3, 0, 1, 2)

        self.dpd_selection_mode = QComboBox(self.frame_7)
        self.dpd_selection_mode.addItem("")
        self.dpd_selection_mode.addItem("")
        self.dpd_selection_mode.setObjectName(u"dpd_selection_mode")

        self.gridLayout_4.addWidget(self.dpd_selection_mode, 0, 0, 1, 2)


        self.verticalLayout_2.addWidget(self.frame_7)

        self.splitter.addWidget(self.frame)
        self.frame_2 = QFrame(self.splitter)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy1)
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lbl_video = QLabel(self.frame_2)
        self.lbl_video.setObjectName(u"lbl_video")
        self.lbl_video.setMinimumSize(QSize(300, 200))
        self.lbl_video.setAlignment(Qt.AlignCenter)

        self.verticalLayout_3.addWidget(self.lbl_video)

        self.frame_4 = QFrame(self.frame_2)
        self.frame_4.setObjectName(u"frame_4")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.frame_4.sizePolicy().hasHeightForWidth())
        self.frame_4.setSizePolicy(sizePolicy2)
        self.frame_4.setFrameShape(QFrame.NoFrame)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.frame_4)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_5 = QFrame(self.frame_4)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.NoFrame)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.lbl_frame_number = QLabel(self.frame_5)
        self.lbl_frame_number.setObjectName(u"lbl_frame_number")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lbl_frame_number.sizePolicy().hasHeightForWidth())
        self.lbl_frame_number.setSizePolicy(sizePolicy3)
        self.lbl_frame_number.setMinimumSize(QSize(80, 0))

        self.horizontalLayout_3.addWidget(self.lbl_frame_number)

        self.sld_seek = QSlider(self.frame_5)
        self.sld_seek.setObjectName(u"sld_seek")
        self.sld_seek.setOrientation(Qt.Horizontal)

        self.horizontalLayout_3.addWidget(self.sld_seek)


        self.verticalLayout_4.addWidget(self.frame_5)

        self.frame_6 = QFrame(self.frame_4)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.NoFrame)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.btn_frame_backward = QPushButton(self.frame_6)
        self.btn_frame_backward.setObjectName(u"btn_frame_backward")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(1)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.btn_frame_backward.sizePolicy().hasHeightForWidth())
        self.btn_frame_backward.setSizePolicy(sizePolicy4)

        self.horizontalLayout_2.addWidget(self.btn_frame_backward)

        self.btn_play = QPushButton(self.frame_6)
        self.btn_play.setObjectName(u"btn_play")
        sizePolicy4.setHeightForWidth(self.btn_play.sizePolicy().hasHeightForWidth())
        self.btn_play.setSizePolicy(sizePolicy4)

        self.horizontalLayout_2.addWidget(self.btn_play)

        self.btn_frame_forward = QPushButton(self.frame_6)
        self.btn_frame_forward.setObjectName(u"btn_frame_forward")
        sizePolicy4.setHeightForWidth(self.btn_frame_forward.sizePolicy().hasHeightForWidth())
        self.btn_frame_forward.setSizePolicy(sizePolicy4)

        self.horizontalLayout_2.addWidget(self.btn_frame_forward)

        self.dpd_playback_speed = QComboBox(self.frame_6)
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.addItem("")
        self.dpd_playback_speed.setObjectName(u"dpd_playback_speed")

        self.horizontalLayout_2.addWidget(self.dpd_playback_speed)

        self.btn_select_frame = QPushButton(self.frame_6)
        self.btn_select_frame.setObjectName(u"btn_select_frame")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(2)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.btn_select_frame.sizePolicy().hasHeightForWidth())
        self.btn_select_frame.setSizePolicy(sizePolicy5)

        self.horizontalLayout_2.addWidget(self.btn_select_frame)


        self.verticalLayout_4.addWidget(self.frame_6)


        self.verticalLayout_3.addWidget(self.frame_4)

        self.splitter.addWidget(self.frame_2)
        self.frame_3 = QFrame(self.splitter)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMinimumSize(QSize(0, 0))
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame_3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.label_2 = QLabel(self.frame_3)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.lst_frames = QListView(self.frame_3)
        self.lst_frames.setObjectName(u"lst_frames")

        self.verticalLayout.addWidget(self.lst_frames)

        self.label_3 = QLabel(self.frame_3)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout.addWidget(self.label_3)

        self.dpd_target_frames_mode = QComboBox(self.frame_3)
        self.dpd_target_frames_mode.addItem("")
        self.dpd_target_frames_mode.addItem("")
        self.dpd_target_frames_mode.addItem("")
        self.dpd_target_frames_mode.setObjectName(u"dpd_target_frames_mode")

        self.verticalLayout.addWidget(self.dpd_target_frames_mode)

        self.chb_include_context = QCheckBox(self.frame_3)
        self.chb_include_context.setObjectName(u"chb_include_context")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.chb_include_context.sizePolicy().hasHeightForWidth())
        self.chb_include_context.setSizePolicy(sizePolicy6)
        self.chb_include_context.setChecked(True)

        self.verticalLayout.addWidget(self.chb_include_context)

        self.frm_context_size = QFrame(self.frame_3)
        self.frm_context_size.setObjectName(u"frm_context_size")
        self.frm_context_size.setFrameShape(QFrame.NoFrame)
        self.frm_context_size.setFrameShadow(QFrame.Raised)
        self.gridLayout_2 = QGridLayout(self.frm_context_size)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.lbl_context_size = QLabel(self.frm_context_size)
        self.lbl_context_size.setObjectName(u"lbl_context_size")
        sizePolicy7 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.lbl_context_size.sizePolicy().hasHeightForWidth())
        self.lbl_context_size.setSizePolicy(sizePolicy7)

        self.gridLayout_2.addWidget(self.lbl_context_size, 1, 0, 1, 3)

        self.sld_context_size = QSlider(self.frm_context_size)
        self.sld_context_size.setObjectName(u"sld_context_size")
        self.sld_context_size.setMaximum(10)
        self.sld_context_size.setValue(1)
        self.sld_context_size.setOrientation(Qt.Horizontal)
        self.sld_context_size.setTickPosition(QSlider.TicksBelow)
        self.sld_context_size.setTickInterval(1)

        self.gridLayout_2.addWidget(self.sld_context_size, 3, 0, 1, 3)


        self.verticalLayout.addWidget(self.frm_context_size)

        self.btn_extract_frames = QPushButton(self.frame_3)
        self.btn_extract_frames.setObjectName(u"btn_extract_frames")

        self.verticalLayout.addWidget(self.btn_extract_frames)

        self.btn_open_labeller = QPushButton(self.frame_3)
        self.btn_open_labeller.setObjectName(u"btn_open_labeller")

        self.verticalLayout.addWidget(self.btn_open_labeller)

        self.splitter.addWidget(self.frame_3)

        self.horizontalLayout.addWidget(self.splitter)

        FrameExtractor.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(FrameExtractor)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1089, 22))
        self.menuWindow = QMenu(self.menubar)
        self.menuWindow.setObjectName(u"menuWindow")
        FrameExtractor.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(FrameExtractor)
        self.statusbar.setObjectName(u"statusbar")
        FrameExtractor.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuWindow.menuAction())
        self.menuWindow.addAction(self.action_open_labeller)

        self.retranslateUi(FrameExtractor)

        self.dpd_playback_speed.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(FrameExtractor)
    # setupUi

    def retranslateUi(self, FrameExtractor):
        FrameExtractor.setWindowTitle(QCoreApplication.translate("FrameExtractor", u"Labell3R Frame Extractor", None))
        self.action_open_labeller.setText(QCoreApplication.translate("FrameExtractor", u"Start Labelling", None))
        self.label.setText(QCoreApplication.translate("FrameExtractor", u"Videos", None))
        self.btn_add_videos.setText(QCoreApplication.translate("FrameExtractor", u"Add Videos", None))
        self.label_4.setText(QCoreApplication.translate("FrameExtractor", u"Select Frames", None))
        self.dpd_num_frames_mode.setItemText(0, QCoreApplication.translate("FrameExtractor", u"Total", None))
        self.dpd_num_frames_mode.setItemText(1, QCoreApplication.translate("FrameExtractor", u"Per Video", None))

        self.dpd_target_videos_mode.setItemText(0, QCoreApplication.translate("FrameExtractor", u"All Videos", None))
        self.dpd_target_videos_mode.setItemText(1, QCoreApplication.translate("FrameExtractor", u"Selected Videos", None))
        self.dpd_target_videos_mode.setItemText(2, QCoreApplication.translate("FrameExtractor", u"Current Video", None))

        self.btn_select_frames.setText(QCoreApplication.translate("FrameExtractor", u"Select Frames", None))
        self.dpd_selection_mode.setItemText(0, QCoreApplication.translate("FrameExtractor", u"Random", None))
        self.dpd_selection_mode.setItemText(1, QCoreApplication.translate("FrameExtractor", u"K-Means", None))

        self.lbl_video.setText(QCoreApplication.translate("FrameExtractor", u"No Video Selected", None))
        self.lbl_frame_number.setText(QCoreApplication.translate("FrameExtractor", u"0/0", None))
        self.btn_frame_backward.setText("")
#if QT_CONFIG(shortcut)
        self.btn_frame_backward.setShortcut(QCoreApplication.translate("FrameExtractor", u"Left", None))
#endif // QT_CONFIG(shortcut)
        self.btn_play.setText("")
#if QT_CONFIG(shortcut)
        self.btn_play.setShortcut(QCoreApplication.translate("FrameExtractor", u"Space", None))
#endif // QT_CONFIG(shortcut)
        self.btn_frame_forward.setText("")
#if QT_CONFIG(shortcut)
        self.btn_frame_forward.setShortcut(QCoreApplication.translate("FrameExtractor", u"Right", None))
#endif // QT_CONFIG(shortcut)
        self.dpd_playback_speed.setItemText(0, QCoreApplication.translate("FrameExtractor", u"0.25x", None))
        self.dpd_playback_speed.setItemText(1, QCoreApplication.translate("FrameExtractor", u"0.5x", None))
        self.dpd_playback_speed.setItemText(2, QCoreApplication.translate("FrameExtractor", u"1x", None))
        self.dpd_playback_speed.setItemText(3, QCoreApplication.translate("FrameExtractor", u"1.5x", None))
        self.dpd_playback_speed.setItemText(4, QCoreApplication.translate("FrameExtractor", u"2x", None))
        self.dpd_playback_speed.setItemText(5, QCoreApplication.translate("FrameExtractor", u"3x", None))
        self.dpd_playback_speed.setItemText(6, QCoreApplication.translate("FrameExtractor", u"4x", None))

        self.dpd_playback_speed.setCurrentText(QCoreApplication.translate("FrameExtractor", u"1x", None))
        self.btn_select_frame.setText(QCoreApplication.translate("FrameExtractor", u"Select Frame", None))
#if QT_CONFIG(shortcut)
        self.btn_select_frame.setShortcut(QCoreApplication.translate("FrameExtractor", u"Return", None))
#endif // QT_CONFIG(shortcut)
        self.label_2.setText(QCoreApplication.translate("FrameExtractor", u"Selected Frames", None))
        self.label_3.setText(QCoreApplication.translate("FrameExtractor", u"Extract Frames", None))
        self.dpd_target_frames_mode.setItemText(0, QCoreApplication.translate("FrameExtractor", u"New Frames", None))
        self.dpd_target_frames_mode.setItemText(1, QCoreApplication.translate("FrameExtractor", u"All Frames", None))
        self.dpd_target_frames_mode.setItemText(2, QCoreApplication.translate("FrameExtractor", u"Selected Frames", None))

        self.chb_include_context.setText(QCoreApplication.translate("FrameExtractor", u"Extract Context Video", None))
        self.lbl_context_size.setText(QCoreApplication.translate("FrameExtractor", u"Context Size: 1 seconds", None))
        self.btn_extract_frames.setText(QCoreApplication.translate("FrameExtractor", u"Extract Frames", None))
        self.btn_open_labeller.setText(QCoreApplication.translate("FrameExtractor", u"Start Labelling \u2b95", None))
        self.menuWindow.setTitle(QCoreApplication.translate("FrameExtractor", u"Window", None))
    # retranslateUi

