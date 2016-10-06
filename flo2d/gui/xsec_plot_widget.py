# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Flo2D
                                 A QGIS plugin
 FLO-2D tools for QGIS
                              -------------------
        begin                : 2016-08-28
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Lutra Consulting for FLO-2D
        email                : info@lutraconsulting.co.uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.utils import iface
from .. import pyqtgraph

pyqtgraph.setConfigOption('background', 'w')
pyqtgraph.setConfigOption('foreground', 'k')
pyqtgraph.setConfigOption('antialias', True)


class XsecPlotWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.xsec = None
        self.gw = pyqtgraph.GraphicsWindow()
        self.plot = self.gw.addPlot()
        self.plot.showGrid(x=True, y=True)

        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(self.gw)

        l = QVBoxLayout()
        l.addLayout(self.stack_layout)
        self.setLayout(l)

    def clear_plot(self):
        self.plot.clear()

    def add_org_bed_plot(self, data):
        self.plot.getAxis('bottom').setLabel('Station')
        self.plot.getAxis('left').setLabel('Elevation')
        s = QSettings()
        plot_resolution = s.value('/flo2d/xsec_resolution', 1., type=float)
        x,y = data
        pen = pyqtgraph.mkPen(color=QColor("#000000"), width=1, cosmetic=True)
        self.org_bed_plot = self.plot.plot(x=x, y=y, connect='finite', pen=pen, name='Existing')

    def add_new_bed_plot(self, data):
        self.plot.getAxis('bottom').setLabel('Station')
        self.plot.getAxis('left').setLabel('Elevation')
        s = QSettings()
        plot_resolution = s.value('/flo2d/xsec_resolution', 1., type=float)
        x,y = data
        pen = pyqtgraph.mkPen(color=QColor("#17874e"), width=2, cosmetic=True)
        self.new_bed_plot = self.plot.plot(x=x, y=y, connect='finite', pen=pen, name='Changed')



