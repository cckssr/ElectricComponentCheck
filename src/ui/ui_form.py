# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QFrame,
    QGridLayout, QLabel, QLineEdit, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QToolBox, QToolButton, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(985, 738)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.line = QFrame(self.centralwidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 1, 1, 2)

        self.line_2 = QFrame(self.centralwidget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 3, 1, 1, 2)

        self.openbis = QGridLayout()
        self.openbis.setObjectName(u"openbis")
        self.openbis.setContentsMargins(-1, -1, -1, 0)
        self.lcr_progress = QLabel(self.centralwidget)
        self.lcr_progress.setObjectName(u"lcr_progress")
        self.lcr_progress.setMinimumSize(QSize(120, 0))

        self.openbis.addWidget(self.lcr_progress, 1, 3, 1, 1)

        self.lcr_connect = QPushButton(self.centralwidget)
        self.lcr_connect.setObjectName(u"lcr_connect")
        self.lcr_connect.setEnabled(False)

        self.openbis.addWidget(self.lcr_connect, 1, 4, 1, 1)

        self.label_6 = QLabel(self.centralwidget)
        self.label_6.setObjectName(u"label_6")

        self.openbis.addWidget(self.label_6, 0, 0, 1, 1)

        self.openbis_save = QPushButton(self.centralwidget)
        self.openbis_save.setObjectName(u"openbis_save")
        self.openbis_save.setEnabled(False)

        self.openbis.addWidget(self.openbis_save, 0, 4, 1, 1)

        self.lcr_refresh_resource = QToolButton(self.centralwidget)
        self.lcr_refresh_resource.setObjectName(u"lcr_refresh_resource")
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.ViewRefresh))
        self.lcr_refresh_resource.setIcon(icon)

        self.openbis.addWidget(self.lcr_refresh_resource, 1, 2, 1, 1)

        self.session_token = QLineEdit(self.centralwidget)
        self.session_token.setObjectName(u"session_token")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.session_token.sizePolicy().hasHeightForWidth())
        self.session_token.setSizePolicy(sizePolicy)

        self.openbis.addWidget(self.session_token, 0, 1, 1, 1)

        self.label_9 = QLabel(self.centralwidget)
        self.label_9.setObjectName(u"label_9")

        self.openbis.addWidget(self.label_9, 1, 0, 1, 1)

        self.openbis_progress = QLabel(self.centralwidget)
        self.openbis_progress.setObjectName(u"openbis_progress")
        self.openbis_progress.setMinimumSize(QSize(120, 0))

        self.openbis.addWidget(self.openbis_progress, 0, 3, 1, 1)

        self.lcr_resource = QComboBox(self.centralwidget)
        self.lcr_resource.setObjectName(u"lcr_resource")

        self.openbis.addWidget(self.lcr_resource, 1, 1, 1, 1)

        self.openbis.setColumnStretch(1, 1)
        self.openbis.setColumnStretch(3, 1)

        self.gridLayout.addLayout(self.openbis, 0, 1, 1, 2)

        self.general = QGridLayout()
        self.general.setObjectName(u"general")
        self.general.setContentsMargins(-1, -1, -1, 10)
        self.formLayout_2 = QFormLayout()
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_2.setContentsMargins(-1, -1, -1, 0)
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)
        self.label.setMinimumSize(QSize(150, 0))

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.barcode = QLineEdit(self.centralwidget)
        self.barcode.setObjectName(u"barcode")
        self.barcode.setEnabled(False)
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.barcode.sizePolicy().hasHeightForWidth())
        self.barcode.setSizePolicy(sizePolicy2)

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.FieldRole, self.barcode)


        self.general.addLayout(self.formLayout_2, 0, 0, 1, 1)

        self.formLayout_6 = QFormLayout()
        self.formLayout_6.setObjectName(u"formLayout_6")
        self.formLayout_6.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_6.setContentsMargins(-1, -1, -1, 0)
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy1.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy1)
        self.label_4.setMinimumSize(QSize(150, 0))

        self.formLayout_6.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.orig_name = QLineEdit(self.centralwidget)
        self.orig_name.setObjectName(u"orig_name")
        self.orig_name.setEnabled(False)
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.orig_name.sizePolicy().hasHeightForWidth())
        self.orig_name.setSizePolicy(sizePolicy3)

        self.formLayout_6.setWidget(0, QFormLayout.ItemRole.FieldRole, self.orig_name)


        self.general.addLayout(self.formLayout_6, 2, 1, 1, 1)

        self.formLayout_5 = QFormLayout()
        self.formLayout_5.setObjectName(u"formLayout_5")
        self.formLayout_5.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_5.setContentsMargins(-1, -1, -1, 0)
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy1.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy1)
        self.label_3.setMinimumSize(QSize(150, 0))

        self.formLayout_5.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.manufacturer = QLineEdit(self.centralwidget)
        self.manufacturer.setObjectName(u"manufacturer")
        self.manufacturer.setEnabled(False)
        sizePolicy2.setHeightForWidth(self.manufacturer.sizePolicy().hasHeightForWidth())
        self.manufacturer.setSizePolicy(sizePolicy2)

        self.formLayout_5.setWidget(0, QFormLayout.ItemRole.FieldRole, self.manufacturer)


        self.general.addLayout(self.formLayout_5, 2, 0, 1, 1)

        self.object_status = QComboBox(self.centralwidget)
        self.object_status.addItem("")
        self.object_status.addItem("")
        self.object_status.addItem("")
        self.object_status.setObjectName(u"object_status")
        self.object_status.setEnabled(False)

        self.general.addWidget(self.object_status, 0, 1, 1, 1)

        self.formLayout_3 = QFormLayout()
        self.formLayout_3.setObjectName(u"formLayout_3")
        self.formLayout_3.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_3.setContentsMargins(-1, -1, -1, 0)
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)
        self.label_2.setMinimumSize(QSize(150, 0))

        self.formLayout_3.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.type = QComboBox(self.centralwidget)
        self.type.addItem("")
        self.type.addItem("")
        self.type.addItem("")
        self.type.addItem("")
        self.type.addItem("")
        self.type.addItem("")
        self.type.setObjectName(u"type")
        self.type.setEnabled(False)
        sizePolicy2.setHeightForWidth(self.type.sizePolicy().hasHeightForWidth())
        self.type.setSizePolicy(sizePolicy2)

        self.formLayout_3.setWidget(0, QFormLayout.ItemRole.FieldRole, self.type)


        self.general.addLayout(self.formLayout_3, 1, 0, 1, 1)

        self.formLayout_4 = QFormLayout()
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.formLayout_4.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_4.setContentsMargins(-1, -1, -1, 0)
        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")
        sizePolicy1.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy1)
        self.label_5.setMinimumSize(QSize(150, 0))

        self.formLayout_4.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_5)

        self.status = QComboBox(self.centralwidget)
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.setObjectName(u"status")
        self.status.setEnabled(False)
        sizePolicy2.setHeightForWidth(self.status.sizePolicy().hasHeightForWidth())
        self.status.setSizePolicy(sizePolicy2)

        self.formLayout_4.setWidget(0, QFormLayout.ItemRole.FieldRole, self.status)


        self.general.addLayout(self.formLayout_4, 1, 1, 1, 1)


        self.gridLayout.addLayout(self.general, 2, 1, 1, 2)

        self.special = QGridLayout()
        self.special.setObjectName(u"special")
        self.special.setContentsMargins(-1, -1, -1, 50)
        self.label_8 = QLabel(self.centralwidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.special.addWidget(self.label_8, 0, 1, 1, 1)

        self.label_7 = QLabel(self.centralwidget)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.special.addWidget(self.label_7, 0, 0, 1, 1)

        self.specific = QToolBox(self.centralwidget)
        self.specific.setObjectName(u"specific")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.specific.sizePolicy().hasHeightForWidth())
        self.specific.setSizePolicy(sizePolicy4)
        self.specific.setMinimumSize(QSize(450, 0))
        self.resistor = QWidget()
        self.resistor.setObjectName(u"resistor")
        self.resistor.setGeometry(QRect(0, 0, 450, 152))
        self.formLayout = QFormLayout(self.resistor)
        self.formLayout.setObjectName(u"formLayout")
        self.specific.addItem(self.resistor, u"Widerstand")
        self.capacitor = QWidget()
        self.capacitor.setObjectName(u"capacitor")
        self.capacitor.setGeometry(QRect(0, 0, 450, 152))
        self.formLayout_7 = QFormLayout(self.capacitor)
        self.formLayout_7.setObjectName(u"formLayout_7")
        self.specific.addItem(self.capacitor, u"Kondensator")
        self.inductor = QWidget()
        self.inductor.setObjectName(u"inductor")
        self.inductor.setGeometry(QRect(0, 0, 450, 152))
        self.formLayout_8 = QFormLayout(self.inductor)
        self.formLayout_8.setObjectName(u"formLayout_8")
        self.specific.addItem(self.inductor, u"Induktivit\u00e4t")
        self.transistor = QWidget()
        self.transistor.setObjectName(u"transistor")
        self.transistor.setGeometry(QRect(0, 0, 450, 152))
        self.formLayout_9 = QFormLayout(self.transistor)
        self.formLayout_9.setObjectName(u"formLayout_9")
        self.specific.addItem(self.transistor, u"Transistor")
        self.switch_2 = QWidget()
        self.switch_2.setObjectName(u"switch_2")
        self.switch_2.setGeometry(QRect(0, 0, 450, 152))
        self.formLayout_10 = QFormLayout(self.switch_2)
        self.formLayout_10.setObjectName(u"formLayout_10")
        self.specific.addItem(self.switch_2, u"Schalter")
        self.fuse = QWidget()
        self.fuse.setObjectName(u"fuse")
        self.fuse.setGeometry(QRect(0, 0, 450, 152))
        self.formLayout_11 = QFormLayout(self.fuse)
        self.formLayout_11.setObjectName(u"formLayout_11")
        self.specific.addItem(self.fuse, u"Sicherung")

        self.special.addWidget(self.specific, 1, 0, 1, 1)

        self.plot_widget = QWidget(self.centralwidget)
        self.plot_widget.setObjectName(u"plot_widget")
        self.plot_widget.setMinimumSize(QSize(100, 10))

        self.special.addWidget(self.plot_widget, 1, 1, 1, 1)

        self.special.setColumnStretch(1, 1)

        self.gridLayout.addLayout(self.special, 4, 1, 1, 2)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 985, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.label)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.barcode, self.type)

        self.retranslateUi(MainWindow)

        self.specific.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Elektrische Komponentencheck", None))
        self.lcr_progress.setText("")
#if QT_CONFIG(tooltip)
        self.lcr_connect.setToolTip(QCoreApplication.translate("MainWindow", u"Verbindet die ausgew\u00e4hlte Ressource (LCR-Meter).", None))
#endif // QT_CONFIG(tooltip)
        self.lcr_connect.setText(QCoreApplication.translate("MainWindow", u"Verbinden", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Session Token", None))
#if QT_CONFIG(tooltip)
        self.openbis_save.setToolTip(QCoreApplication.translate("MainWindow", u"L\u00e4dt die Neuerungen, \u00c4nderungen, Messungen zu OpenBIS hoch.", None))
#endif // QT_CONFIG(tooltip)
        self.openbis_save.setText(QCoreApplication.translate("MainWindow", u"Upload", None))
#if QT_CONFIG(tooltip)
        self.lcr_refresh_resource.setToolTip(QCoreApplication.translate("MainWindow", u"Resourcen neu laden", None))
#endif // QT_CONFIG(tooltip)
        self.lcr_refresh_resource.setText("")
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Auswahl LCR-Meter", None))
        self.openbis_progress.setText(QCoreApplication.translate("MainWindow", u"Warten auf SessionToken...", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Barcode", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Herstellerbezeichnung</p></body></html>", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Hersteller", None))
        self.object_status.setItemText(0, "")
        self.object_status.setItemText(1, QCoreApplication.translate("MainWindow", u"Neues Objekt", None))
        self.object_status.setItemText(2, QCoreApplication.translate("MainWindow", u"Bekannt", None))

        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Kategorie", None))
        self.type.setItemText(0, QCoreApplication.translate("MainWindow", u"Widerstand", None))
        self.type.setItemText(1, QCoreApplication.translate("MainWindow", u"Kondensator", None))
        self.type.setItemText(2, QCoreApplication.translate("MainWindow", u"Induktivit\u00e4t", None))
        self.type.setItemText(3, QCoreApplication.translate("MainWindow", u"Transistor", None))
        self.type.setItemText(4, QCoreApplication.translate("MainWindow", u"Schalter", None))
        self.type.setItemText(5, QCoreApplication.translate("MainWindow", u"Sicherung", None))

        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Funktionsstatus", None))
        self.status.setItemText(0, QCoreApplication.translate("MainWindow", u"Funktioniert", u"FUNC"))
        self.status.setItemText(1, QCoreApplication.translate("MainWindow", u"Unkalibriert", u"NOCALB"))
        self.status.setItemText(2, QCoreApplication.translate("MainWindow", u"Kalibriert", u"OK"))
        self.status.setItemText(3, QCoreApplication.translate("MainWindow", u"Unbekannt", u"UNKWN"))
        self.status.setItemText(4, QCoreApplication.translate("MainWindow", u"Defekt", u"DEF"))
        self.status.setItemText(5, QCoreApplication.translate("MainWindow", u"Archiviert", u"ARCHIVE"))

        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Messung (LCR)", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"OpenBIS Eigenschaften", None))
        self.specific.setItemText(self.specific.indexOf(self.resistor), QCoreApplication.translate("MainWindow", u"Widerstand", None))
        self.specific.setItemText(self.specific.indexOf(self.capacitor), QCoreApplication.translate("MainWindow", u"Kondensator", None))
        self.specific.setItemText(self.specific.indexOf(self.inductor), QCoreApplication.translate("MainWindow", u"Induktivit\u00e4t", None))
        self.specific.setItemText(self.specific.indexOf(self.transistor), QCoreApplication.translate("MainWindow", u"Transistor", None))
        self.specific.setItemText(self.specific.indexOf(self.switch_2), QCoreApplication.translate("MainWindow", u"Schalter", None))
        self.specific.setItemText(self.specific.indexOf(self.fuse), QCoreApplication.translate("MainWindow", u"Sicherung", None))
    # retranslateUi

