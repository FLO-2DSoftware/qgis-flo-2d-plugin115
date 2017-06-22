# -*- coding: utf-8 -*-

# FLO-2D Preprocessor tools for QGIS
# Copyright © 2016 Lutra Consulting for FLO-2D

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version

import os
import traceback
from PyQt4.QtCore import Qt, QSettings
from PyQt4.QtGui import QColor, QInputDialog, QFileDialog, QApplication
from ui_utils import load_ui, try_disconnect, set_icon
from flo2d.flo2d_ie.rainfall_io import ASCProcessor, HDFProcessor
from flo2d.utils import is_number, m_fdata
from flo2d.geopackage_utils import GeoPackageUtils, connection_required
from table_editor_widget import StandardItemModel, StandardItem, CommandItemEdit
from flo2d.flo2dobjects import Rain
from flo2d.user_communication import UserCommunication
from math import isnan

uiDialog, qtBaseClass = load_ui('rain_editor')


class RainEditorWidget(qtBaseClass, uiDialog):

    def __init__(self, iface, plot, table, lyrs):
        qtBaseClass.__init__(self)
        uiDialog.__init__(self)
        self.iface = iface
        self.con = None
        self.setupUi(self)
        self.lyrs = lyrs
        self.plot = plot
        self.table = table
        self.tview = table.tview
        self.rain = None
        self.gutils = None
        self.uc = UserCommunication(iface, 'FLO-2D')
        self.rain_data_model = StandardItemModel()
        self.rain_tseries_data = None
        self.plot_item_name = None
        self.d1, self.d2 = [[], []]

        set_icon(self.show_table_btn, 'show_cont_table.svg')
        set_icon(self.remove_tseries_btn, 'mActionDeleteSelected.svg')
        set_icon(self.add_tseries_btn, 'add_bc_data.svg')
        set_icon(self.rename_tseries_btn, 'change_name.svg')

    def block_saving(self):
        try_disconnect(self.rain_data_model.dataChanged, self.save_tseries_data)

    def unblock_saving(self):
        self.rain_data_model.dataChanged.connect(self.save_tseries_data)

    def itemDataChangedSlot(self, item, oldValue, newValue, role, save=True):
        """
        Slot used to push changes of existing items onto undoStack.
        """
        if role == Qt.EditRole:
            command = CommandItemEdit(self, item, oldValue, newValue,
                                      "Text changed from '{0}' to '{1}'".format(oldValue, newValue))
            self.tview.undoStack.push(command)
            return True

    def connect_signals(self):
        self.asc_btn.clicked.connect(self.import_rainfall)
        self.hdf_btn.clicked.connect(self.export_rainfall)
        self.tseries_cbo.currentIndexChanged.connect(self.populate_tseries_data)
        self.simulate_rain_chbox.stateChanged.connect(self.set_rain)
        self.real_time_chbox.stateChanged.connect(self.set_realtime)
        self.building_chbox.stateChanged.connect(self.set_building)
        self.arf_chbox.stateChanged.connect(self.set_arf)
        self.moving_storm_chbox.stateChanged.connect(self.set_moving_storm)
        self.total_rainfall_sbox.editingFinished.connect(self.set_tot_rainfall)
        self.rainfall_abst_sbox.editingFinished.connect(self.set_rainfall_abst)
        self.show_table_btn.clicked.connect(self.populate_tseries_data)
        self.add_tseries_btn.clicked.connect(self.add_tseries)
        self.remove_tseries_btn.clicked.connect(self.delete_tseries)
        self.rename_tseries_btn.clicked.connect(self.rename_tseries)
        self.rain_data_model.dataChanged.connect(self.save_tseries_data)
        self.table.before_paste.connect(self.block_saving)
        self.table.after_paste.connect(self.unblock_saving)
        self.rain_data_model.itemDataChanged.connect(self.itemDataChangedSlot)

    def setup_connection(self):
        con = self.iface.f2d['con']
        if con is None:
            return
        self.con = con
        self.gutils = GeoPackageUtils(self.con, self.iface)
        qry = '''SELECT value FROM cont WHERE name = 'IRAIN';'''
        row = self.gutils.execute(qry).fetchone()
        if is_number(row[0]) and not row[0] == '0':
            self.simulate_rain_chbox.setChecked(True)
        self.rain = Rain(self.con, self.iface)
        self.create_plot()

    def import_rainfall(self):
        s = QSettings()
        last_dir = s.value('FLO-2D/lastASC', '')
        asc_dir = QFileDialog.getExistingDirectory(
            None,
            'Select directory with Rainfall ASCII grid files',
            directory=last_dir)
        if not asc_dir:
            return
        s.setValue('FLO-2D/lastASC', asc_dir)
        try:
            grid_lyr = self.lyrs.data['grid']['qlyr']
            QApplication.setOverrideCursor(Qt.WaitCursor)
            asc_processor = ASCProcessor(grid_lyr, asc_dir)
            head_qry = 'INSERT INTO raincell (rainintime, irinters, timestamp) VALUES(?,?,?);'
            data_qry = 'INSERT INTO raincell_data (time_interval, rrgrid, iraindum) VALUES (?,?,?);'
            self.gutils.clear_tables('raincell', 'raincell_data')
            header = asc_processor.parse_rfc()
            time_step = float(header[0])
            self.gutils.execute(head_qry, header)
            time_interval = 0
            for rain_series in asc_processor.rainfall_sampling():
                cur = self.gutils.con.cursor()
                for val, gid in rain_series:
                    cur.execute(data_qry, (time_interval, gid, val))
                self.gutils.con.commit()
                time_interval += time_step
            QApplication.restoreOverrideCursor()
            self.uc.show_info('Importing Rainfall Data finished!')
        except Exception as e:
            self.uc.log_info(traceback.format_exc())
            QApplication.restoreOverrideCursor()
            self.uc.bar_warn('Importing Rainfall Data failed! Please check your input data.')

    def export_rainfall(self):
        try:
            import h5py
        except ImportError:
            self.uc.bar_warn('There is no h5py module installed! Please install it to run export tool.')
            return
        s = QSettings()
        last_dir = s.value('FLO-2D/lastHDF', '')
        hdf_file = QFileDialog.getSaveFileName(
            None,
            'Export Rainfall to HDF file',
            directory=last_dir,
            filter='*.hdf5')
        if not hdf_file:
            return
        s.setValue('FLO-2D/lastHDF', os.path.dirname(hdf_file))
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            qry_header = 'SELECT rainintime, irinters, timestamp FROM raincell LIMIT 1;'
            header = self.gutils.execute(qry_header).fetchone()
            rainintime, irinters, timestamp = header
            header_data = [rainintime, irinters, timestamp]
            qry_data = 'SELECT iraindum FROM raincell_data ORDER BY rrgrid, time_interval;'
            data = self.gutils.execute(qry_data).fetchall()
            data = [data[i:i+irinters] for i in xrange(0, len(data), irinters)]
            hdf_processor = HDFProcessor(hdf_file)
            hdf_processor.export_rainfall(header_data, data)
            QApplication.restoreOverrideCursor()
            self.uc.show_info('Exporting Rainfall Data finished!')
        except Exception as e:
            self.uc.log_info(traceback.format_exc())
            QApplication.restoreOverrideCursor()
            self.uc.bar_warn('Exporting Rainfall Data failed! Please check your input data.')

    def create_plot(self):
        """
        Create initial plot.
        """
        self.plot.clear()
        self.plot_item_name = 'Rain timeseries'
        self.plot.add_item(self.plot_item_name, [self.d1, self.d2], col=QColor("#0018d4"))

    @connection_required
    def rain_properties(self):
        if not self.rain:
            return
        row = self.rain.get_row()
        if self.gutils.get_cont_par('IRAIN') == '1':
            self.simulate_rain_chbox.setChecked(True)
        else:
            self.simulate_rain_chbox.setChecked(False)
        if row['irainreal'] == 1:
            self.real_time_chbox.setChecked(True)
        else:
            self.real_time_chbox.setChecked(False)
        if row['irainbuilding'] == 1:
            self.building_chbox.setChecked(True)
        else:
            self.building_chbox.setChecked(False)
        if row['movingstrom'] == 1:
            self.moving_storm_chbox.setChecked(True)
        else:
            self.moving_storm_chbox.setChecked(False)
        if row['irainarf'] == 1:
            self.arf_chbox.setChecked(True)
        else:
            self.moving_storm_chbox.setChecked(False)
        if is_number(row['tot_rainfall']):
            self.total_rainfall_sbox.setValue(float((row['tot_rainfall'])))
        else:
            self.total_rainfall_sbox.setValue(0)
        if is_number(row['rainabs']):
            self.rainfall_abst_sbox.setValue(float(row['rainabs']))
        else:
            self.rainfall_abst_sbox.setValue(0)
        self.populate_tseries()
        idx = self.tseries_cbo.findData(self.rain.series_fid)
        self.tseries_cbo.setCurrentIndex(idx)
        self.populate_tseries_data()
        self.connect_signals()

    def populate_tseries(self):
        self.tseries_cbo.clear()
        for row in self.rain.get_time_series():
            ts_fid, name = [x if x is not None else '' for x in row]
            self.tseries_cbo.addItem(name, ts_fid)

    def add_tseries(self):
        if not self.rain:
            return
        self.rain.add_time_series()
        self.populate_tseries()

    def delete_tseries(self):
        if not self.rain:
            return
        self.rain.del_time_series()
        self.populate_tseries()

    def rename_tseries(self):
        if not self.rain:
            return
        new_name, ok = QInputDialog.getText(None, 'Change timeseries name', 'New name:')
        if not ok or not new_name:
            return
        if not self.tseries_cbo.findText(new_name) == -1:
            msg = 'Time series with name {} already exists in the database. Please, choose another name.'.format(
                new_name)
            self.uc.show_warn(msg)
            return
        self.rain.set_time_series_data_name(new_name)
        self.populate_tseries()

    def populate_tseries_data(self):
        """
        Get current time series data, populate data table and create plot.
        """
        cur_ts_idx = self.tseries_cbo.currentIndex()
        cur_ts_fid = self.tseries_cbo.itemData(cur_ts_idx)
        self.rain.series_fid = cur_ts_fid
        self.rain_tseries_data = self.rain.get_time_series_data()
        if not self.rain_tseries_data:
            return
        self.create_plot()
        self.tview.undoStack.clear()
        self.tview.setModel(self.rain_data_model)
        self.rain_data_model.clear()
        self.rain_data_model.setHorizontalHeaderLabels(['Time', 'Cum. Perc. of Total Storm'])
        self.d1, self.d1 = [[], []]
        for row in self.rain_tseries_data:
            items = [StandardItem('{:.4f}'.format(x)) if x is not None else StandardItem('') for x in row]
            self.rain_data_model.appendRow(items)
            self.d1.append(row[0] if not row[0] is None else float('NaN'))
            self.d2.append(row[1] if not row[1] is None else float('NaN'))
        rc = self.rain_data_model.rowCount()
        if rc < 500:
            for row in range(rc, 500 + 1):
                items = [StandardItem(x) for x in ('',) * 2]
                self.rain_data_model.appendRow(items)
        self.tview.horizontalHeader().setStretchLastSection(True)
        for col in range(2):
            self.tview.setColumnWidth(col, 100)
        for i in range(self.rain_data_model.rowCount()):
            self.tview.setRowHeight(i, 20)
        self.rain.set_row()
        self.update_plot()

    def save_tseries_data(self):
        """
        Get rain timeseries data and save them in gpkg.
        """
        self.update_plot()
        ts_data = []
        for i in range(self.rain_data_model.rowCount()):
            # save only rows with a number in the first column
            if is_number(m_fdata(self.rain_data_model, i, 0)) and not isnan(m_fdata(self.rain_data_model, i, 0)):
                ts_data.append(
                    (
                        self.rain.series_fid,
                        m_fdata(self.rain_data_model, i, 0),
                        m_fdata(self.rain_data_model, i, 1)
                    )
                )
            else:
                pass
        data_name = self.tseries_cbo.currentText()
        self.rain.set_time_series_data(data_name, ts_data)

    def update_plot(self):
        """
        When time series data for plot change, update the plot.
        """
        if not self.plot_item_name:
            return
        # self.plot.clear()
        self.d1, self.d2 = [[], []]
        for i in range(self.rain_data_model.rowCount()):
            self.d1.append(m_fdata(self.rain_data_model, i, 0))
            self.d2.append(m_fdata(self.rain_data_model, i, 1))
        self.plot.update_item(self.plot_item_name, [self.d1, self.d2])

    def set_rain(self):
        if not self.rain:
            return
        if self.simulate_rain_chbox.isChecked():
            self.gutils.set_cont_par('IRAIN', 1)
        else:
            self.gutils.set_cont_par('IRAIN', 0)

    def set_realtime(self):
        if not self.rain:
            return
        self.rain.irainreal = self.real_time_chbox.isChecked()
        self.rain.set_row()

    def set_building(self):
        if not self.rain:
            return
        self.rain.irainbuilding = self.building_chbox.isChecked()
        self.rain.set_row()

    def set_arf(self):
        if not self.rain:
            return
        self.rain.irainarf = self.arf_chbox.isChecked()
        self.rain.set_row()

    def set_moving_storm(self):
        if not self.rain:
            return
        self.rain.movingstrom = self.moving_storm_chbox.isChecked()
        self.rain.set_row()

    def set_tot_rainfall(self):
        if not self.rain:
            return
        self.rain.tot_rainfall = self.total_rainfall_sbox.value()
        self.rain.set_row()

    def set_rainfall_abst(self):
        if not self.rain:
            return
        self.rain.rainabs = self.rainfall_abst_sbox.value()
        self.rain.set_row()
