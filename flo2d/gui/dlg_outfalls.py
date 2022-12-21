# -*- coding: utf-8 -*-

# FLO-2D Preprocessor tools for QGIS

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version

from ..utils import is_true, float_or_zero, int_or_zero, is_number
from qgis.core import QgsFeatureRequest
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QInputDialog, 
     QTableWidgetItem, 
     QDialogButtonBox, 
     QApplication, 
     QFileDialog, 
     QHeaderView,
     QStyledItemDelegate,
     QLineEdit
    )

from qgis.PyQt.QtGui import QColor
from .ui_utils import load_ui, set_icon, center_canvas, zoom
from ..geopackage_utils import GeoPackageUtils
from ..user_communication import UserCommunication




uiDialog, qtBaseClass = load_ui("outfalls")


class OutfallNodesDialog(qtBaseClass, uiDialog):
    def __init__(self, iface, lyrs):
        qtBaseClass.__init__(self)
        uiDialog.__init__(self)
        self.iface = iface
        self.lyrs = lyrs
        self.setupUi(self)
        self.uc = UserCommunication(iface, "FLO-2D")
        self.con = None
        self.gutils = None
        self.block = False
        
        set_icon(self.find_outfall_cell_btn, "eye-svgrepo-com.svg")
        set_icon(self.zoom_in_outfall_btn, "zoom_in.svg")
        set_icon(self.zoom_out_outfall_btn, "zoom_out.svg")  
        
        self.outfalls_tuple = ("FIXED", "FREE", "NORMAL", "TIDAL CURVE", "TIME SERIES")
        
        self.setup_connection()
        
        self.outfalls_buttonBox.button(QDialogButtonBox.Save).setText("Save to 'Storm Drain Nodes-Outfalls' User Layer")
        self.outfall_cbo.currentIndexChanged.connect(self.fill_individual_controls_with_current_outfall_in_table)
        self.outfalls_buttonBox.accepted.connect(self.save_outfalls)

        self.find_outfall_cell_btn.clicked.connect(self.find_outfall)
        self.zoom_in_outfall_btn.clicked.connect(self.zoom_in_outfall_cell)
        self.zoom_out_outfall_btn.clicked.connect(self.zoom_out_outfall_cell)
        
        # Connections from individual controls to particular cell in outfalls_tblw table widget:
        # self.grid_element.valueChanged.connect(self.grid_element_valueChanged)
        self.invert_elevation_dbox.valueChanged.connect(self.invert_elevation_dbox_valueChanged)
        self.flap_gate_chbox.stateChanged.connect(self.flap_gate_chbox_stateChanged)
        self.allow_discharge_chbox.stateChanged.connect(self.allow_discharge_chbox_stateChanged)
        self.outfall_type_cbo.currentIndexChanged.connect(self.out_fall_type_cbo_currentIndexChanged)
        self.water_depth_dbox.valueChanged.connect(self.water_depth_dbox_valueChanged)
        self.tidal_curve_cbo.currentIndexChanged.connect(self.tidal_curve_cbo_currentIndexChanged)
        self.time_series_cbo.currentIndexChanged.connect(self.time_series_cbo_currentIndexChanged)

        # self.open_tidal_curve_btn.clicked.connect(self.open_tidal_curve)
        # self.open_time_series_btn.clicked.connect(self.open_time_series)
        #
        # self.set_header()
        
        
        self.grid_lyr = self.lyrs.data["grid"]["qlyr"]
        self.grid_count = self.gutils.count('grid', field="fid")        
        
        self.outfalls_tblw.cellClicked.connect(self.outfalls_tblw_cell_clicked)
        self.outfalls_tblw.verticalHeader().sectionClicked.connect(self.onVerticalSectionClicked)
        
        self.populate_outfalls()

    def set_header(self):
        self.outfalls_tblw.setHorizontalHeaderLabels(
            [
                "Name",  # INP
                "Node",  # FLO-2D
                "Invert Elev.",  # INP
                "Flap Gate",  # INP #FLO-2D
                "Allow Discharge" "Outfall Type",  # FLO-2D  # INP
                "Water Depth",  #
                "Tidal Curve",  # IN P
                "Time Series",
            ]
        )  # INP

    def setup_connection(self):
        con = self.iface.f2d["con"]
        if con is None:
            return
        else:
            self.con = con
            self.gutils = GeoPackageUtils(self.con, self.iface)

    # def invert_connect(self):
    #     self.uc.show_info('Connection!')
    #
    # def grid_element_valueChanged(self):
    #     self.box_valueChanged(self.grid_element, 1)

    def populate_outfalls(self):

        try:
            qry = """SELECT fid,
                            name, 
                            grid, 
                            outfall_invert_elev,
                            flapgate, 
                            swmm_allow_discharge,
                            outfall_type, 
                            water_depth,
                            tidal_curve, 
                            time_series              
                    FROM user_swmm_nodes WHERE sd_type = 'O';"""

            rows = self.gutils.execute(qry).fetchall()  # rows is a list of tuples.
            if not rows:
                QApplication.restoreOverrideCursor()
                self.uc.show_info(
                    "WARNING 121121.0421: No outfalls in 'Storm Drain Nodes' User Layer!"
                )
                return
    
            self.block = True            
       
            self.outfalls_tblw.setRowCount(0)
            for row_number, row_data in enumerate(rows):  # In each iteration gets a tuple, for example:  0, ('fid'12, 'name''OUT3', 2581, 'False', 'False' 0,0,0, '', '')
                self.outfalls_tblw.insertRow(row_number)
                for col_number, data in enumerate(row_data):  # For each iteration gets, for example: first iteration:  0, 12. 2nd. iteration 1, 'OUT3', etc
                    if col_number == 6 and data not in self.outfalls_tuple:
                        data = "NORMAL"
                    item = QTableWidgetItem()
                    item.setData(Qt.DisplayRole, data if data is not None else 0
                    )  # item gets value of data (as QTableWidgetItem Class)

                    # Fill the list of outfall names:
                    if (col_number == 1):  # We need 2nd. col_number: 'OUT3' in the example above, and its fid from row_data[0]
                        self.outfall_cbo.addItem(data, row_data[0])

                    # Fill all text boxes with data of first feature of query (first element in table user_swmm_nodes):
                    if row_number == 0:
                        data = 0 if data is None else data
                        if col_number == 2:
                            self.grid_element_txt.setText(str(data))
                        elif col_number == 3:
                            self.invert_elevation_dbox.setValue(data if data is not None else 0)
                        elif col_number == 4:
                            self.flap_gate_chbox.setChecked(True if is_true(data) else False)
                        elif col_number == 5:
                            self.allow_discharge_chbox.setChecked(True if is_true(data) else False)
                        elif col_number == 6:
                            data = str(data).upper()
                            if data in self.outfalls_tuple:
                                index = self.outfalls_tuple.index(data)
                            else:
                                index = 0
                            self.outfall_type_cbo.setCurrentIndex(index)
                            data = self.outfall_type_cbo.currentText()
                            if not data in ("FIXED", "FREE", "NORMAL", "TIDAL CURVE", "TIME SERIES"):
                                data = "NORMAL"
                            item.setData(Qt.DisplayRole, data)
                        elif col_number == 7:
                            self.water_depth_dbox.setValue(data if data is not None else 0)
                        elif col_number == 8:
                            self.tidal_curve_cbo.setCurrentIndex(0)
                        elif col_number == 9:
                            self.time_series_cbo.setCurrentIndex(0)

                    if col_number > 0:  # For this row disable some elements and omit fid number
                        if (col_number in  (1, 2, 4, 5, 6, 8, 9)):
                            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        self.outfalls_tblw.setItem(row_number, col_number - 1, item)
                        
            self.outfall_cbo.model().sort(0)
            
            self.outfalls_tblw.sortItems(0, Qt.AscendingOrder)
            self.outfalls_tblw.selectRow(0)                     
                        
            self.block = False   
            self.outfall_cbo.setCurrentIndex(0)         
            self.highlight_outfall_cell(self.grid_element_txt.text())   
                     
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.uc.show_error("ERROR 100618.0846: error while loading outfalls components!", e)

    def onVerticalSectionClicked(self, logicalIndex):
        self.outfalls_tblw_cell_clicked(logicalIndex, 0)

    def invert_elevation_dbox_valueChanged(self):
        self.box_valueChanged(self.invert_elevation_dbox, 2)

    def flap_gate_chbox_stateChanged(self):
        self.checkbox_valueChanged(self.flap_gate_chbox, 3)

    def allow_discharge_chbox_stateChanged(self):
        self.checkbox_valueChanged(self.allow_discharge_chbox, 4)

    def out_fall_type_cbo_currentIndexChanged(self):
        self.combo_valueChanged(self.outfall_type_cbo, 5)

        self.disableTypes()

        idx = self.outfall_type_cbo.currentIndex()
        
        if idx == 0:
            self.water_depth_dbox.setEnabled(True)
            self.label_5.setEnabled(True)
        elif idx == 3:
            self.tidal_curve_cbo.setEnabled(True)
            self.label_7.setEnabled(True)
            self.open_tidal_curve_btn.setEnabled(True)
        elif idx == 4:
            self.time_series_cbo.setEnabled(True)
            self.label_8.setEnabled(True)
            self.open_time_series_btn.setEnabled(True)

    def disableTypes(self):
        self.water_depth_dbox.setEnabled(False)
        self.label_5.setEnabled(False)
        
        self.tidal_curve_cbo.setEnabled(False)
        self.label_7.setEnabled(False)
        
        self.time_series_cbo.setEnabled(False)
        self.label_8.setEnabled(False)
        
        self.open_tidal_curve_btn.setEnabled(False)
        self.open_time_series_btn.setEnabled(False)   
    def water_depth_dbox_valueChanged(self):
        self.box_valueChanged(self.water_depth_dbox, 6)

    def tidal_curve_cbo_currentIndexChanged(self):
        self.combo_valueChanged(self.tidal_curve_cbo, 7)

    def time_series_cbo_currentIndexChanged(self):
        self.combo_valueChanged(self.time_series_cbo, 8)

    def open_tidal_curve(self):
        pass

    def open_time_series(self):
        time_series_name = self.time_series_cbo.currentText()
        dlg = OutfallTimeSeriesDialog(self.iface, time_series_name)
        while True:
            save = dlg.exec_()
            if save:
                if dlg.values_ok:
                    dlg.save_time_series()
                    time_series_name = dlg.get_name()
                    if time_series_name != "":
                        # Reload time series list and select the one saved:
                        time_series_names_sql = (
                            "SELECT DISTINCT time_series_name FROM swmm_inflow_time_series GROUP BY time_series_name"
                        )
                        names = self.gutils.execute(time_series_names_sql).fetchall()
                        if names:
                            self.time_series_cbo.clear()
                            for name in names:
                                self.time_series_cbo.addItem(name[0])
                            self.time_series_cbo.addItem("")
            
                            idx = self.time_series_cbo.findText(time_series_name)
                            self.time_series_cbo.setCurrentIndex(idx)                    

                        # self.uc.bar_info("Storm Drain external time series saved for inlet " + "?????")
                        break
                    else:
                       break 
            else:
                break
             

    def box_valueChanged(self, widget, col):
        # if not self.block:        
        #     row = self.outfall_cbo.currentIndex()
        #     item = QTableWidgetItem()
        #     item.setData(Qt.EditRole, widget.value())
        #     self.outfalls_tblw.setItem(row, col, item)
            
            
        if not self.block:
            outfall = self.outfall_cbo.currentText()
            row = 0
            for i in range(1, self.outfalls_tblw.rowCount() - 1):
                name = self.outfalls_tblw.item(i, 0).text()
                if name == outfall:
                    row = i
                    break
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, widget.value())
            if (col in  (0, 1, 3, 4, 5, 7, 8)):
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)            
            self.outfalls_tblw.setItem(row, col, item)            

    def checkbox_valueChanged(self, widget, col):
        row = self.outfall_cbo.currentIndex()
        item = QTableWidgetItem()
        if (col in  (0, 1, 3, 4, 5, 7, 8)):
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)          
        self.outfalls_tblw.setItem(row, col, item)
        self.outfalls_tblw.item(row, col).setText("True" if widget.isChecked() else "False")

    def combo_valueChanged(self, widget, col):
        row = self.outfall_cbo.currentIndex()
        item = QTableWidgetItem()
        data = widget.currentText()
        item.setData(Qt.EditRole, data)
        if (col in  (0, 1, 3, 4, 5, 7, 8)):
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)            
        self.outfalls_tblw.setItem(row, col, item)

    def outfalls_tblw_cell_clicked(self, row, column):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.outfall_cbo.blockSignals(True)

            name = self.outfalls_tblw.item(row, 0).text()
            idx = self.outfall_cbo.findText(name)
            self.outfall_cbo.setCurrentIndex(idx)

            self.outfall_cbo.blockSignals(False)

            self.block = True
            
            self.grid_element_txt.setText(self.outfalls_tblw.item(row, 1).text())
            self.invert_elevation_dbox.setValue(float_or_zero(self.outfalls_tblw.item(row, 2)))
            self.flap_gate_chbox.setChecked(True if is_true(self.outfalls_tblw.item(row, 3).text()) else False)
            self.allow_discharge_chbox.setChecked(True if is_true(self.outfalls_tblw.item(row, 4).text()) else False)
            # Set index of outfall_type_cbo (a combo) depending of text contents:
            item = self.outfalls_tblw.item(row, 5)
            if item is not None:
                itemTxt = item.text().upper().strip()
                itemTxt = "TIDAL CURVE" if itemTxt == "TIDAL" else "TIME SERIES" if itemTxt == "TIME" else itemTxt
                if itemTxt in self.outfalls_tuple:
                    index = self.outfall_type_cbo.findText(itemTxt)
                else:
                    itemTxt = "NORMAL"
                    index = self.outfall_type_cbo.findText(itemTxt)
                index = 4 if index > 4 else 0 if index < 0 else index
                self.outfall_type_cbo.setCurrentIndex(index)
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, self.outfall_type_cbo.currentText())
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)   
                self.outfalls_tblw.setItem(row, 5, item)

            self.water_depth_dbox.setValue(float_or_zero(self.outfalls_tblw.item(row, 6)))
            
            self.block = False
            
            self.highlight_outfall_cell(self.grid_element_txt.text())

            QApplication.restoreOverrideCursor()
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.uc.show_error("ERROR 210618.1702: error assigning outfall values!", e)

    def fill_individual_controls_with_current_outfall_in_table(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if not self.block:
            # Highlight row in table:
            row = self.outfall_cbo.currentIndex()
            self.outfalls_tblw.selectRow(row)
    
            # Load controls (text boxes, etc.) with selected row in table:
            item = QTableWidgetItem()
    
            item = self.outfalls_tblw.item(row, 1)
            if item is not None:
                self.grid_element_txt.setText(str(item.text()))
    
            self.invert_elevation_dbox.setValue(float_or_zero(self.outfalls_tblw.item(row, 2)))
    
            item = self.outfalls_tblw.item(row, 3)
            if item is not None:
                self.flap_gate_chbox.setChecked(True if is_true(item.text()) else False)
    
            #                                             True if item.text() == 'true' or item.text() == 'True' or item.text() == '1'
            #                                             or item.text() == 'Yes' or item.text() == 'yes' else False)
    
            item = self.outfalls_tblw.item(row, 4)
            if item is not None:
                self.allow_discharge_chbox.setChecked(True if is_true(item.text()) else False)
    
            #                                             True if item.text() == 'true' or item.text() == 'True' or item.text() == '1' else False)
    
            item = self.outfalls_tblw.item(row, 5)
            if item is not None:
                itemTxt = item.text().upper()
                if itemTxt in self.outfalls_tuple:
                    index = self.outfall_type_cbo.findText(itemTxt)
                else:
                    if itemTxt == "":
                        index = 0
                    else:
                        if is_number(itemTxt):
                            index = itemTxt
                        else:
                            index = 0
                index = 4 if index > 4 else 0 if index < 0 else index
                self.outfall_type_cbo.setCurrentIndex(index)
                item = QTableWidgetItem()
                item.setData(Qt.EditRole, self.outfall_type_cbo.currentText())
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)   
                self.outfalls_tblw.setItem(row, 5, item)
    
            self.water_depth_dbox.setValue(float_or_zero(self.outfalls_tblw.item(row, 6)))
            
            self.highlight_outfall_cell(self.grid_element_txt.text())
            
        QApplication.restoreOverrideCursor()
        
    def find_outfall(self):
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if self.grid_lyr is not None:
                if self.grid_lyr:
                    outfall = self.outfall_to_find_le.text()
                    if outfall != "":
                        indx = self.outfall_cbo.findText(outfall)
                        if  indx != -1:
                            self.outfall_cbo.setCurrentIndex(indx)
                        else:
                            self.uc.bar_warn("WARNING 121121.0746: outfall " + str(outfall) + " not found.")
                    else:
                        self.uc.bar_warn("WARNING  121121.0747: outfall " + str(outfall) + " not found.")
        except ValueError:
            self.uc.bar_warn("WARNING  121121.0748: outfall " + str(outfall) + " is not a levee cell.")
            pass
        finally:
            QApplication.restoreOverrideCursor()

    def highlight_outfall_cell(self, cell):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.grid_lyr is not None:
                if cell != "":
                    cell = int(cell)
                    if self.grid_count >= cell and cell > 0:
                        self.lyrs.show_feat_rubber(self.grid_lyr.id(), cell, QColor(Qt.yellow))
                        feat = next(self.grid_lyr.getFeatures(QgsFeatureRequest(cell)))
                        x, y = feat.geometry().centroid().asPoint()
                        self.lyrs.zoom_to_all()
                        center_canvas(self.iface, x, y)
                        zoom(self.iface, 0.45)

                    else:
                        self.uc.bar_warn("WARNING 121121.1140: Cell " + str(cell) + " not found.")
                        self.lyrs.clear_rubber()
                else:
                    self.uc.bar_warn("WARNING 121121.1139: Cell " + str(cell) + " not found.")
                    self.lyrs.clear_rubber()
                    
            QApplication.restoreOverrideCursor() 
                   
        except ValueError:
            QApplication.restoreOverrideCursor()
            self.uc.bar_warn("WARNING 121121.1134: Cell " + str(cell) + "is not valid.")
            self.lyrs.clear_rubber()
            pass

    def zoom_in_outfall_cell(self):
        self.currentCell = next(self.grid_lyr.getFeatures(QgsFeatureRequest(int(self.grid_element_txt.text()))))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        x, y = self.currentCell.geometry().centroid().asPoint()
        center_canvas(self.iface, x, y)
        zoom(self.iface, 0.4)
        # self.update_extent()
        QApplication.restoreOverrideCursor()

    def zoom_out_outfall_cell(self):
        self.currentCell = next(self.grid_lyr.getFeatures(QgsFeatureRequest(int(self.grid_element_txt.text()))))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        x, y = self.currentCell.geometry().centroid().asPoint()
        center_canvas(self.iface, x, y)
        zoom(self.iface, -0.4)
        # self.update_extent()
        QApplication.restoreOverrideCursor()

    def save_outfalls(self):
        """
        Save changes of user_swmm_nodes layer.
        """
        # self.save_attrs()
        update_qry = """
                        UPDATE user_swmm_nodes
                        SET
                            name = ?, 
                            grid = ?, 
                            outfall_invert_elev = ?,
                            flapgate = ?, 
                            swmm_allow_discharge = ?,
                            outfall_type = ?,
                            water_depth = ?,
                            tidal_curve = ?,
                            time_series = ?
                        WHERE fid = ?;"""

        for row in range(0, self.outfalls_tblw.rowCount()):
            item = QTableWidgetItem()

            fid = self.outfall_cbo.itemData(row)

            item = self.outfalls_tblw.item(row, 0)
            if item is not None:
                name = str(item.text())

            item = self.outfalls_tblw.item(row, 1)
            if item is not None:
                grid = str(item.text())

            item = self.outfalls_tblw.item(row, 2)
            if item is not None:
                invert_elev = str(item.text())

            item = self.outfalls_tblw.item(row, 3)
            if item is not None:
                flapgate = str(True if is_true(item.text()) else False)

            item = self.outfalls_tblw.item(row, 4)
            if item is not None:
                allow_discharge = str(True if is_true(item.text()) else False)

            item = self.outfalls_tblw.item(row, 5)
            if item is not None:
                outfall_type = str(item.text())
                if not outfall_type in ("FIXED", "FREE", "NORMAL", "TIDAL CURVE", "TIME SERIES"):
                    outfall_type = "NORMAL"

            item = self.outfalls_tblw.item(row, 6)
            if item is not None:
                water_depth = str(item.text())

            item = self.outfalls_tblw.item(row, 7)
            # if item is not None:
            tidal_curve = str(item.text()) if item is not None else ""

            item = self.outfalls_tblw.item(row, 8)
            # if item is not None:
            time_series = str(item.text()) if item is not None else ""

            self.gutils.execute(
                update_qry,
                (
                    name,
                    grid,
                    invert_elev,
                    flapgate,
                    allow_discharge,
                    outfall_type,
                    water_depth,
                    tidal_curve,
                    time_series,
                    fid,
                ),
            )

uiDialog, qtBaseClass = load_ui("storm_drain_outfall_time_series")
class OutfallTimeSeriesDialog(qtBaseClass, uiDialog):
    def __init__(self, iface, time_series_name):
        qtBaseClass.__init__(self)

        uiDialog.__init__(self)
        self.iface = iface
        self.time_series_name = time_series_name
        self.setupUi(self)
        self.uc = UserCommunication(iface, "FLO-2D")
        self.con = None
        self.gutils = None
        
        self.values_ok = False
        set_icon(self.add_time_data_btn, "add.svg")
        set_icon(self.delete_time_data_btn, "remove.svg") 
               
        self.setup_connection()

        delegate = NumericDelegate(self.inflow_time_series_tblw)
        self.inflow_time_series_tblw.setItemDelegate(delegate)
        
        self.time_series_buttonBox.accepted.connect(self.is_ok_to_save)
        self.select_time_series_btn.clicked.connect(self.select_time_series_file)   
        self.inflow_time_series_tblw.itemChanged.connect(self.ts_tblw_changed)
        self.add_time_data_btn.clicked.connect(self.add_time) 
        self.delete_time_data_btn.clicked.connect(self.delete_time) 

        self.populate_time_series_dialog()

    def setup_connection(self):
        con = self.iface.f2d["con"]
        if con is None:
            return
        else:
            self.con = con
            self.gutils = GeoPackageUtils(self.con, self.iface)

    def populate_time_series_dialog(self):
        if self.time_series_name == "":
            self.use_table_radio.setChecked(True)
            pass
        else:
            series_sql = "SELECT * FROM swmm_inflow_time_series WHERE time_series_name = ?"
            row = self.gutils.execute(series_sql, (self.time_series_name,)).fetchone()
            if row:
                self.name_le.setText(row[1])
                self.description_le.setText(row[2])
                self.file_le.setText(row[3])
                external = True if is_true(row[4]) else False
                
                if external:    
                    self.use_table_radio.setChecked(True)
                    self.external_radio.setChecked(False)                          
                else:
                    self.external_radio.setChecked(True)
                    self.use_table_radio.setChecked(False)
                    
                data_qry = """SELECT
                                date, 
                                time, 
                                value
                        FROM swmm_inflow_time_series_data WHERE time_series_name = ?;"""
                rows = self.gutils.execute(data_qry, (self.time_series_name,)).fetchall()
                if rows:
                    self.inflow_time_series_tblw.setRowCount(0)
            
                    for row_number, row_data in enumerate(rows):
                        self.inflow_time_series_tblw.insertRow(row_number)
                        for cell, data in enumerate(row_data):
            
                            item = QTableWidgetItem()     
                            item.setData(Qt.DisplayRole, data)
                            self.inflow_time_series_tblw.setItem(row_number, cell, item)
        
                    self.inflow_time_series_tblw.sortItems(0, Qt.AscendingOrder)                    
            else:
                self.name_le.setText(self.time_series_name)
                self.external_radio.setChecked(True)
                self.use_table_radio.setChecked(False)
        
        QApplication.restoreOverrideCursor()  
             
    def select_time_series_file(self):
        self.uc.clear_bar_messages()

        s = QSettings()
        last_dir = s.value("FLO-2D/lastSWMMDir", "")
        time_series_file, __ = QFileDialog.getOpenFileName(None, "Select time series data file", directory=last_dir)
        if not time_series_file:
            return
        s.setValue("FLO-2D/lastSWMMDir", os.path.dirname(time_series_file))
        self.file_le.setText(time_series_file)

        # For future use
        try:
            pass
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.uc.show_error("ERROR 140220.0807: reading time series data file failed!", e)
            return

    def is_ok_to_save(self):
        if self.name_le.text() == "":
            self.uc.bar_warn("Time Series name required!", 2)
            self.time_series_name = ""
            self.values_ok = False
            
        elif self.description_le.text() == "":
            self.uc.bar_warn("Time Series description required!", 2)
            self.values_ok = False
            
        elif self.external_radio.isChecked() and  self.file_le.text() == "":
            self.uc.bar_warn("Data file name required!", 2)
            self.values_ok = False
        else:
            self.values_ok = True
    
    def save_time_series(self):      
        delete_sql = "DELETE FROM swmm_inflow_time_series WHERE time_series_name = ?"
        self.gutils.execute(delete_sql, (self.name_le.text(),))
        insert_sql = "INSERT INTO swmm_inflow_time_series (time_series_name, time_series_description, time_series_file, time_series_data) VALUES (?, ?, ?, ?);"
        self.gutils.execute(
            insert_sql,
            (
                self.name_le.text(),
                self.description_le.text(),
                self.file_le.text(),
                "True" if self.use_table_radio.isChecked()else "False"
            ),
        )

        delete_data_sql = "DELETE FROM swmm_inflow_time_series_data WHERE time_series_name = ?"
        self.gutils.execute(delete_data_sql, (self.name_le.text(),))
        
        insert_data_sql = ["""INSERT INTO swmm_inflow_time_series_data (time_series_name, date, time, value) VALUES""", 4]
        for row in range(0, self.inflow_time_series_tblw.rowCount()):
            date = self.inflow_time_series_tblw.item(row, 0)
            if date:
                date = date.text()
                                         
            time = self.inflow_time_series_tblw.item(row, 1)
            if time:
                time = time.text()
                
            value = self.inflow_time_series_tblw.item(row, 2)
            if value:
                value = value.text()
                
            insert_data_sql += [(self.name_le.text(), date, time, value)]
        self.gutils.batch_execute(insert_data_sql)   
            
        self.uc.bar_info("Inflow time series " + self.name_le.text() + " saved.", 2)
        self.time_series_name = self.name_le.text()
        self.close()

    def get_name(self):
        return self.time_series_name

    def inflow_time_series_tblw_clicked(self):
        self.uc.show_info("Clicked")
        
    def time_series_model_changed(self, i,j):
        self.uc.show_info("Changed") 
        
        
    def ts_tblw_changed(self, Qitem):  
        return
        try:
            test = float(Qitem.text())
        except ValueError:
            self.uc.show_info("Float error") 
            Qitem.setText("")     

    def add_time(self):
        self.inflow_time_series_tblw.insertRow(self.inflow_time_series_tblw.rowCount())  
        row_number = self.inflow_time_series_tblw.rowCount() - 1
        
        item = QTableWidgetItem()
        d= QDate.currentDate()
        d = str(d.month()) + "/" + str(d.day()) + "/" + str(d.year()) 
        item.setData(Qt.DisplayRole, d)                         
        self.inflow_time_series_tblw.setItem(row_number, 0, item)   
        
        item = QTableWidgetItem()
        t = QTime.currentTime()
        t = str(t.hour()) + ":" + str(t.minute())
        item.setData(Qt.DisplayRole, t)                         
        self.inflow_time_series_tblw.setItem(row_number, 1, item) 
        
        item = QTableWidgetItem()
        item.setData(Qt.DisplayRole, "0.0")                         
        self.inflow_time_series_tblw.setItem(row_number, 2, item) 
       
        self.inflow_time_series_tblw.selectRow(row_number)
        self.inflow_time_series_tblw.setFocus()                   

    def delete_time(self):
        self.inflow_time_series_tblw.removeRow(self.inflow_time_series_tblw.currentRow())      
        self.inflow_time_series_tblw.selectRow(0)
        self.inflow_time_series_tblw.setFocus()
                                          
class NumericDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super(NumericDelegate, self).createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            reg_ex = QRegExp("[0-9]+.?[0-9]{,2}")
            validator = QRegExpValidator(reg_ex, editor)
            editor.setValidator(validator)
        return editor                                           
                           

