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
    QMenuBar, QSizePolicy, QStatusBar, QToolBox,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1140, 873)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.toolBox = QToolBox(self.centralwidget)
        self.toolBox.setObjectName(u"toolBox")
        self.resistor = QWidget()
        self.resistor.setObjectName(u"resistor")
        self.resistor.setGeometry(QRect(0, 0, 1116, 459))
        self.toolBox.addItem(self.resistor, u"Widerstand")
        self.capacitor = QWidget()
        self.capacitor.setObjectName(u"capacitor")
        self.capacitor.setGeometry(QRect(0, 0, 1116, 459))
        self.toolBox.addItem(self.capacitor, u"Kondensator")
        self.inductor = QWidget()
        self.inductor.setObjectName(u"inductor")
        self.inductor.setGeometry(QRect(0, 0, 1116, 459))
        self.toolBox.addItem(self.inductor, u"Induktivit\u00e4t")
        self.transistor = QWidget()
        self.transistor.setObjectName(u"transistor")
        self.transistor.setGeometry(QRect(0, 0, 1116, 459))
        self.toolBox.addItem(self.transistor, u"Transistor")
        self.switch_2 = QWidget()
        self.switch_2.setObjectName(u"switch_2")
        self.switch_2.setGeometry(QRect(0, 0, 1116, 459))
        self.toolBox.addItem(self.switch_2, u"Schalter")
        self.fuse = QWidget()
        self.fuse.setObjectName(u"fuse")
        self.fuse.setGeometry(QRect(0, 0, 1116, 459))
        self.toolBox.addItem(self.fuse, u"Sicherung")

        self.gridLayout.addWidget(self.toolBox, 2, 1, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(-1, -1, -1, 10)
        self.formLayout_2 = QFormLayout()
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_2.setContentsMargins(-1, -1, -1, 0)
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMinimumSize(QSize(150, 0))

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.barcode = QLineEdit(self.centralwidget)
        self.barcode.setObjectName(u"barcode")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.barcode.sizePolicy().hasHeightForWidth())
        self.barcode.setSizePolicy(sizePolicy1)

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.FieldRole, self.barcode)


        self.gridLayout_2.addLayout(self.formLayout_2, 0, 0, 1, 1)

        self.formLayout_6 = QFormLayout()
        self.formLayout_6.setObjectName(u"formLayout_6")
        self.formLayout_6.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_6.setContentsMargins(-1, -1, -1, 0)
        self.status = QComboBox(self.centralwidget)
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.addItem("")
        self.status.setObjectName(u"status")
        sizePolicy1.setHeightForWidth(self.status.sizePolicy().hasHeightForWidth())
        self.status.setSizePolicy(sizePolicy1)

        self.formLayout_6.setWidget(0, QFormLayout.ItemRole.FieldRole, self.status)

        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        self.label_5.setMinimumSize(QSize(150, 0))

        self.formLayout_6.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_5)


        self.gridLayout_2.addLayout(self.formLayout_6, 2, 1, 1, 1)

        self.formLayout_5 = QFormLayout()
        self.formLayout_5.setObjectName(u"formLayout_5")
        self.formLayout_5.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_5.setContentsMargins(-1, -1, -1, 0)
        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setMinimumSize(QSize(150, 0))

        self.formLayout_5.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.orig_name = QLineEdit(self.centralwidget)
        self.orig_name.setObjectName(u"orig_name")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.orig_name.sizePolicy().hasHeightForWidth())
        self.orig_name.setSizePolicy(sizePolicy2)

        self.formLayout_5.setWidget(0, QFormLayout.ItemRole.FieldRole, self.orig_name)


        self.gridLayout_2.addLayout(self.formLayout_5, 2, 0, 1, 1)

        self.formLayout_3 = QFormLayout()
        self.formLayout_3.setObjectName(u"formLayout_3")
        self.formLayout_3.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_3.setContentsMargins(-1, -1, -1, 0)
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
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
        sizePolicy1.setHeightForWidth(self.type.sizePolicy().hasHeightForWidth())
        self.type.setSizePolicy(sizePolicy1)

        self.formLayout_3.setWidget(0, QFormLayout.ItemRole.FieldRole, self.type)


        self.gridLayout_2.addLayout(self.formLayout_3, 1, 0, 1, 1)

        self.formLayout_4 = QFormLayout()
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.formLayout_4.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.formLayout_4.setContentsMargins(-1, -1, -1, 0)
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setMinimumSize(QSize(150, 0))

        self.formLayout_4.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.manufacturer = QLineEdit(self.centralwidget)
        self.manufacturer.setObjectName(u"manufacturer")
        sizePolicy1.setHeightForWidth(self.manufacturer.sizePolicy().hasHeightForWidth())
        self.manufacturer.setSizePolicy(sizePolicy1)

        self.formLayout_4.setWidget(0, QFormLayout.ItemRole.FieldRole, self.manufacturer)


        self.gridLayout_2.addLayout(self.formLayout_4, 1, 1, 1, 1)


        self.gridLayout.addLayout(self.gridLayout_2, 0, 1, 1, 1)

        self.line_2 = QFrame(self.centralwidget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_2, 1, 1, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1140, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
#if QT_CONFIG(shortcut)
        self.label.setBuddy(self.label)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.barcode, self.type)
        QWidget.setTabOrder(self.type, self.manufacturer)
        QWidget.setTabOrder(self.manufacturer, self.orig_name)
        QWidget.setTabOrder(self.orig_name, self.status)

        self.retranslateUi(MainWindow)

        self.toolBox.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.resistor), QCoreApplication.translate("MainWindow", u"Widerstand", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.capacitor), QCoreApplication.translate("MainWindow", u"Kondensator", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.inductor), QCoreApplication.translate("MainWindow", u"Induktivit\u00e4t", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.transistor), QCoreApplication.translate("MainWindow", u"Transistor", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.switch_2), QCoreApplication.translate("MainWindow", u"Schalter", None))
        self.toolBox.setItemText(self.toolBox.indexOf(self.fuse), QCoreApplication.translate("MainWindow", u"Sicherung", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Barcode", None))
        self.status.setItemText(0, QCoreApplication.translate("MainWindow", u"Funktioniert", u"FUNC"))
        self.status.setItemText(1, QCoreApplication.translate("MainWindow", u"Unkalibriert", u"NOCALB"))
        self.status.setItemText(2, QCoreApplication.translate("MainWindow", u"Kalibriert", u"OK"))
        self.status.setItemText(3, QCoreApplication.translate("MainWindow", u"Unbekannt", u"UNKWN"))
        self.status.setItemText(4, QCoreApplication.translate("MainWindow", u"Defekt", u"DEF"))
        self.status.setItemText(5, QCoreApplication.translate("MainWindow", u"Archiviert", u"ARCHIVE"))

        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Funktionsstatus", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Herstellerbezeichnung</p></body></html>", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Kategorie", None))
        self.type.setItemText(0, QCoreApplication.translate("MainWindow", u"Widerstand", None))
        self.type.setItemText(1, QCoreApplication.translate("MainWindow", u"Kondensator", None))
        self.type.setItemText(2, QCoreApplication.translate("MainWindow", u"Induktivit\u00e4t", None))
        self.type.setItemText(3, QCoreApplication.translate("MainWindow", u"Transistor", None))
        self.type.setItemText(4, QCoreApplication.translate("MainWindow", u"Schalter", None))
        self.type.setItemText(5, QCoreApplication.translate("MainWindow", u"Sicherung", None))

        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Hersteller", None))
    # retranslateUi

