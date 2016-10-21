# -*- coding: utf-8 -*-

# FLO-2D Preprocessor tools for QGIS
# Copyright © 2016 Lutra Consulting for FLO-2D

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version

from .utils import load_ui
from qgis.core import QgsFeatureRequest

uiDialog, qtBaseClass = load_ui('grid_info_dock')


class GridInfoDock(qtBaseClass, uiDialog):

    def __init__(self, iface, lyrs):
        qtBaseClass.__init__(self)
        uiDialog.__init__(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.lyrs = lyrs
        self.setupUi(self)
        self.setEnabled(True)
        self.grid = None

    def set_info_layer(self, lyr):
        self.grid = lyr

    def update_fields(self, fid):
        if not fid == -1:
            feat = self.grid.getFeatures(QgsFeatureRequest(fid)).next()
            self.elevEdit.setText(str(feat['elevation']))
            self.mannEdit.setText(str(feat['n_value']))
        else:
            self.elevEdit.setText('')
            self.mannEdit.setText('')
