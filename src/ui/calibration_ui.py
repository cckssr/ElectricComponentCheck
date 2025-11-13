# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calibration.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QGridLayout, QLayout, QSizePolicy,
    QTextBrowser, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(520, 400)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        Dialog.setMinimumSize(QSize(511, 400))
        Dialog.setMaximumSize(QSize(1000, 1000))
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.textBrowser = QTextBrowser(Dialog)
        self.textBrowser.setObjectName(u"textBrowser")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.textBrowser.sizePolicy().hasHeightForWidth())
        self.textBrowser.setSizePolicy(sizePolicy1)
        self.textBrowser.setMinimumSize(QSize(496, 0))
        self.textBrowser.setMaximumSize(QSize(16777215, 140))

        self.gridLayout.addWidget(self.textBrowser, 0, 0, 1, 1)

        self.shortCal = QCheckBox(Dialog)
        self.shortCal.setObjectName(u"shortCal")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.shortCal.sizePolicy().hasHeightForWidth())
        self.shortCal.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.shortCal, 1, 0, 1, 1)

        self.textBrowser_2 = QTextBrowser(Dialog)
        self.textBrowser_2.setObjectName(u"textBrowser_2")
        sizePolicy1.setHeightForWidth(self.textBrowser_2.sizePolicy().hasHeightForWidth())
        self.textBrowser_2.setSizePolicy(sizePolicy1)
        self.textBrowser_2.setMaximumSize(QSize(16777215, 140))

        self.gridLayout.addWidget(self.textBrowser_2, 2, 0, 1, 1)

        self.openCal = QCheckBox(Dialog)
        self.openCal.setObjectName(u"openCal")
        sizePolicy2.setHeightForWidth(self.openCal.sizePolicy().hasHeightForWidth())
        self.openCal.setSizePolicy(sizePolicy2)

        self.gridLayout.addWidget(self.openCal, 3, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        sizePolicy2.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy2)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 1)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Kalibrierung des LCR-Meter", None))
        self.textBrowser.setHtml(QCoreApplication.translate("Dialog", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'.AppleSystemUIFont'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">F\u00fcr die Kurzschlusskorrektur folgende Schritte befolgen:</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">1.  Beiligenden Kurzschlussleiste in H<span style=\" vertical-align:sub;\">pot</span> und L<span style=\" vertical-align:sub;\">pot</span> stecken.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px;"
                        " margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">2.  <span style=\" font-style:italic;\">REL / CAL </span>mind. 3 sek dr\u00fccken.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">3.  <span style=\" font-style:italic;\">REL / CAL</span> erneut einmalig dr\u00fccken.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Die Kalibrierung wird automatisch durchgef\u00fchrt (ca. 1 min). Das Display zeigt &quot;<span style=\" font-style:italic;\">Shorting calibration</span>&quot; wenn die Kurzschlussleiste korrekt eingesetzt wurde.</p></body></html>", None))
        self.shortCal.setText(QCoreApplication.translate("Dialog", u"Kurzschluss Kalibrierung durchgef\u00fchrt", None))
        self.textBrowser_2.setHtml(QCoreApplication.translate("Dialog", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'.AppleSystemUIFont'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">F\u00fcr die Leerlaufkorrektur folgende Schritte befolgen:</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">1.  Sicherstellen, dass <span style=\" font-weight:700;\">KEINE</span> Messbuchse mit etwas verbunden ist</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block"
                        "-indent:0; text-indent:0px;\">2.  <span style=\" font-style:italic;\">REL / CAL </span>mind. 3 sek dr\u00fccken.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">3.  <span style=\" font-style:italic;\">REL / CAL</span> erneut einmalig dr\u00fccken.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Die Kalibrierung wird automatisch durchgef\u00fchrt (ca. 3 min). Das Display zeigt &quot;<span style=\" font-style:italic;\">Open calibration</span>&quot; wenn korrekt die offenen Buchsen erkannt wurden.</p></body></html>", None))
        self.openCal.setText(QCoreApplication.translate("Dialog", u"Leerlauf Kalibrierung durchgef\u00fchrt", None))
    # retranslateUi

