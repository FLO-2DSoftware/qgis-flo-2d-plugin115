-- Create GeoPackage structure


 -- Create base GeoPackage tables

SELECT gpkgCreateBaseTables();

-- Add aspatial extension

INSERT INTO gpkg_extensions
  (table_name, column_name, extension_name, definition, scope)
VALUES (
    NULL,
    NULL,
    'gdal_aspatial',
    'http://gdal.org/geopackage_aspatial.html',
    'read-write'
);


-- FLO-2D tables definitions

-- The main table with model control parameters (from CONT.DAT and others)

CREATE TABLE cont (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "value" TEXT,
    "note" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('cont', 'aspatial');


-- Grid table - data from FPLAIN.DAT, CADPTS.DAT, TOPO.DAT, MANNINGS_N.DAT

CREATE TABLE "grid" ( `fid` INTEGER PRIMARY KEY AUTOINCREMENT,
   "cell_north" INTEGER,
   "cell_east" INTEGER,
   "cell_south" INTEGER,
   "cell_west" INTEGER,
   "n_value" REAL,
   "elevation" REAL
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('grid', 'features', 4326);
SELECT gpkgAddGeometryColumn('grid', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('grid', 'geom');
SELECT gpkgAddSpatialIndex('grid', 'geom');


-- Inflow - INFLOW.DAT

CREATE TABLE "inflow" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT,
    "time_series_fid" INTEGER,
    "ident" TEXT NOT NULL,
    "inoutfc" INTEGER NOT NULL,
    "note" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('inflow', 'features', 4326);
SELECT gpkgAddGeometryColumn('inflow', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('inflow', 'geom');
SELECT gpkgAddSpatialIndex('inflow', 'geom');

CREATE TABLE "inflow_cells" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "inflow_fid" INTEGER NOT NULL,
    "grid_fid" INTEGER NOT NULL,
    "area_factor" REAL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('inflow_cells', 'aspatial');

CREATE TRIGGER "find_inflow_cells_insert"
    AFTER INSERT ON "inflow"
    WHEN (new."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "inflow_cells" WHERE inflow_fid = NEW."fid";
        INSERT INTO "inflow_cells" (inflow_fid, grid_fid) SELECT NEW.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_inflow_cells_update"
    AFTER UPDATE ON "inflow"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "inflow_cells" WHERE inflow_fid = OLD."fid";
        INSERT INTO "inflow_cells" (inflow_fid, grid_fid) SELECT OLD.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_inflow_cells_delete"
    AFTER DELETE ON "inflow"
--     WHEN (OLD."geom" NOT NULL AND NOT ST_IsEmpty(OLD."geom"))
    BEGIN
        DELETE FROM "inflow_cells" WHERE inflow_fid = OLD."fid";
    END;

-- Outflows

CREATE TABLE "outflow" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT,
    "ident" TEXT,
    "nostacfp" INTEGER,
    "time_series_fid" INTEGER,
    "qh_params_fid" INTEGER,
    "note" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('outflow', 'features', 4326);
SELECT gpkgAddGeometryColumn('outflow', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('outflow', 'geom');
SELECT gpkgAddSpatialIndex('outflow', 'geom');

CREATE TABLE "outflow_cells" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "outflow_fid" INTEGER NOT NULL,
    "grid_fid" INTEGER NOT NULL,
    "area_factor" REAL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('outflow_cells', 'aspatial');

CREATE TABLE "outflow_chan_elems" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "outflow_fid" INTEGER NOT NULL,
    "elem_fid" INTEGER NOT NULL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('outflow_chan_elems', 'aspatial');

CREATE TRIGGER "find_outflow_cells_insert"
    AFTER INSERT ON "outflow"
    WHEN (new."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom") AND NEW."ident" = 'N')
    BEGIN
        DELETE FROM "outflow_cells" WHERE outflow_fid = NEW."fid";
        INSERT INTO "outflow_cells" (outflow_fid, grid_fid, area_factor) 
        SELECT NEW.fid, g.fid, ST_Area(ST_Intersection(CastAutomagic(g.geom), CastAutomagic(NEW.geom)))/ST_Area(NEW.geom) FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_outflow_chan_elems_insert"
    AFTER INSERT ON "outflow"
    WHEN (new."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom") AND NEW."ident" = 'K')
    BEGIN
        DELETE FROM "outflow_chan_elems" WHERE outflow_fid = NEW."fid";
        INSERT INTO "outflow_chan_elems" (outflow_fid, elem_fid) SELECT NEW.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_outflow_cells_update"
    AFTER UPDATE ON "outflow"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom") AND NOT NULL)
    BEGIN
        DELETE FROM "outflow_cells" WHERE outflow_fid = OLD."fid" AND NEW."ident" = 'N';
        INSERT INTO "outflow_cells" (outflow_fid, grid_fid) SELECT OLD.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom)) AND NEW."ident" = 'N';
    END;

CREATE TRIGGER "find_outflow_chan_elems_update"
    AFTER UPDATE ON "outflow"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom") AND NOT NULL)
    BEGIN
        DELETE FROM "outflow_chan_elems" WHERE outflow_fid = OLD."fid" AND NEW."ident" = 'K';
        INSERT INTO "outflow_chan_elems" (outflow_fid, elem_fid) SELECT OLD.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom)) AND NEW."ident" = 'K';
    END;

CREATE TRIGGER "find_outflow_cells_delete"
    AFTER DELETE ON "outflow"
    WHEN (OLD."ident" = 'N')
    BEGIN
        DELETE FROM "outflow_cells" WHERE outflow_fid = OLD."fid";
    END;

CREATE TRIGGER "find_outflow_chan_elems_delete"
    AFTER DELETE ON "outflow"
    WHEN (OLD."ident" = 'K')
    BEGIN
        DELETE FROM "outflow_chan_elems" WHERE outflow_fid = OLD."fid";
    END;

CREATE TABLE "qh_params" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "max" REAL,
    "coef" REAL,
    "exponent" REAL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('qh_params', 'aspatial');

CREATE TABLE "outflow_hydrographs" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "hydro_fid" TEXT NOT NULL,
    "grid_fid" INTEGER NOT NULL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('outflow_hydrographs', 'aspatial');

CREATE TABLE "reservoirs" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT,
    "grid_fid" INTEGER,
    "wsel" REAL,
    "note" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('reservoirs', 'features', 4326);
SELECT gpkgAddGeometryColumn('reservoirs', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('reservoirs', 'geom');
SELECT gpkgAddSpatialIndex('reservoirs', 'geom');

CREATE TABLE "time_series" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "name" TEXT,
    "type" TEXT,
    "hourdaily" INTEGER
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('time_series', 'aspatial');

CREATE TABLE "time_series_data" (
    "fid" INTEGER PRIMARY KEY NOT NULL,
    "series_fid" INTEGER NOT NULL,
    "time" REAL NOT NULL,
    "value" REAL NOT NULL,
    "value2" REAL,
    "value3" REAL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('time_series_data', 'aspatial');


-- RAIN.DAT

CREATE TABLE "rain" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "name" TEXT, -- name of rain
    "irainreal" INTEGER, -- IRAINREAL switch for real-time rainfall (NEXRAD)
    "ireainbuilding" INTEGER, -- IRAINBUILDING, switch, if 1 rainfall on ARF portion of grid will be contributed to surface runoff
    "time_series_fid" INTEGER, -- id of time series used for rain cumulative distribution (in time)
    "tot_rainfall" REAL, -- RTT, total storm rainfall [inch or mm]
    "rainabs" REAL, -- RAINABS, rain interception or abstraction
    "irainarf" REAL, -- IRAINARF, switch for individual grid elements rain area reduction factor (1 is ON)
    "movingstrom" INTEGER, -- MOVINGSTORM, switch for moving storm simulation (1 is ON)
    "rainspeed" REAL, -- RAINSPEED, speed of moving storm
    "iraindir" INTEGER, -- IRAINDIR, direction of moving storm
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('rain', 'aspatial');

CREATE TABLE "rain_arf_areas" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "rain_fid" INTEGER, -- fid of rain the area is defined for
    "arf" REAL, -- RAINARF(I), area reduction factor
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('rain_arf_areas', 'features', 4326);
SELECT gpkgAddGeometryColumn('rain_arf_areas', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('rain_arf_areas', 'geom');
SELECT gpkgAddSpatialIndex('rain_arf_areas', 'geom');

CREATE TABLE "rain_arf_cells" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "rain_arf_area_fid" INTEGER, -- fid of area with ARF defined
    "grid_fid" INTEGER, -- IRGRID(I), nr of grid element
    "arf" REAL -- RAINARF(I), ARF value for a grid elemen
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('rain_arf_cells', 'aspatial');

CREATE TRIGGER "find_rain_arf_cells_insert"
    AFTER INSERT ON "rain_arf_areas"
    WHEN (new."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "rain_arf_cells" WHERE rain_arf_area_fid = NEW."fid";
        INSERT INTO "rain_arf_cells" (rain_arf_area_fid, grid_fid, arf) 
        SELECT NEW.fid, g.fid, NEW.arf FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_rain_arf_cells_update"
    AFTER UPDATE ON "rain_arf_areas"
    WHEN (new."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "rain_arf_cells" WHERE rain_arf_area_fid = NEW."fid";
        INSERT INTO "rain_arf_cells" (rain_arf_area_fid, grid_fid, arf) 
        SELECT NEW.fid, g.fid, NEW.arf FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_rain_arf_cells_delete"
    AFTER DELETE ON "rain_arf_areas"
    BEGIN
        DELETE FROM "rain_arf_cells" WHERE rain_arf_area_fid = OLD."fid";
    END;


-- CHAN.DAT

CREATE TABLE "chan" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "name" TEXT, -- name of segment (optional)
    "depinitial" REAL, -- DEPINITIAL, initial channel flow depth
    "froudc" REAL, -- FROUDC, max Froude channel number
    "roughadj" REAL, -- ROUGHADJ, coefficient for depth adjustment
    "isedn" INTEGER, -- ISEDN, sediment transport equation or data
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('chan', 'features', 4326);
SELECT gpkgAddGeometryColumn('chan', 'geom', 'LINESTRING', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('chan', 'geom');
SELECT gpkgAddSpatialIndex('chan', 'geom');

CREATE TABLE "chan_r" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "seg_fid" INTEGER, -- fid of cross-section's segment
    "nr_in_seg" INTEGER, -- cross-section number in segment
    "ichangrid" INTEGER, -- ICHANGRID, grid element number for left bank
    "bankell" REAL, -- BANKELL, left bank elevation
    "bankelr" REAL, -- BANKELR, right bank elevation
    "fcn" REAL, -- FCN, average Manning's n in the grid element
    "fcw" REAL, -- FCW, channel width
    "fcd" REAL, -- channel channel thalweg depth (deepest part measured from the lowest bank)
    "xlen" REAL, -- channel length contained within the grid element ICHANGRID
    "rbankgrid" INTEGER, -- RIGHTBANK, right bank grid element fid
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('chan_r', 'features', 4326);
SELECT gpkgAddGeometryColumn('chan_r', 'geom', 'LINESTRING', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('chan_r', 'geom');
SELECT gpkgAddSpatialIndex('chan_r', 'geom');

CREATE TABLE "chan_v" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "seg_fid" INTEGER, -- fid of cross-section's segment
    "nr_in_seg" INTEGER, -- cross-section number in segment
    "ichangrid" INTEGER, -- ICHANGRID, grid element number for left bank
    "bankell" REAL, -- BANKELL, left bank elevation
    "bankelr" REAL, -- BANKELR, right bank elevation
    "fcn" REAL, -- FCN, average Manning's n in the grid element
    "fcd" REAL, -- channel channel thalweg depth (deepest part measured from the lowest bank)
    "xlen" REAL, -- channel length contained within the grid element ICHANGRID
    "a1" REAL, -- A1,
    "a2" REAL, -- A2,
    "b1" REAL, -- B1,
    "b2" REAL, -- B2,
    "c1" REAL, -- C1,
    "c2" REAL, -- C2,
    "excdep" REAL, -- EXCDEP, channel depth above which second variable area relationship will be applied
    "a11" REAL, -- A11,
    "a22" REAL, -- A22,
    "b11" REAL, -- B11,
    "b22" REAL, -- B22,
    "c11" REAL, -- C11,
    "c22" REAL, -- C22,
    "rbankgrid" INTEGER, -- RIGHTBANK, right bank grid element fid
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('chan_v', 'features', 4326);
SELECT gpkgAddGeometryColumn('chan_v', 'geom', 'LINESTRING', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('chan_v', 'geom');
SELECT gpkgAddSpatialIndex('chan_v', 'geom');

CREATE TABLE "chan_t" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "seg_fid" INTEGER, -- fid of cross-section's segment
    "nr_in_seg" INTEGER, -- cross-section number in segment
    "ichangrid" INTEGER, -- ICHANGRID, grid element number for left bank
    "bankell" REAL, -- BANKELL, left bank elevation
    "bankelr" REAL, -- BANKELR, right bank elevation
    "fcn" REAL, -- FCN, average Manning's n in the grid element
    "fcw" REAL, -- FCW, channel width
    "fcd" REAL, -- channel channel thalweg depth (deepest part measured from the lowest bank)
    "xlen" REAL, -- channel length contained within the grid element ICHANGRID
    "zl" REAL, -- ZL left side slope
    "zr" REAL, --ZR right side slope
    "rbankgrid" INTEGER, -- RIGHTBANK, right bank grid element fid
    
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('chan_t', 'features', 4326);
SELECT gpkgAddGeometryColumn('chan_t', 'geom', 'LINESTRING', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('chan_t', 'geom');
SELECT gpkgAddSpatialIndex('chan_t', 'geom');

CREATE TABLE "chan_n" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "seg_fid" INTEGER, -- fid of cross-section's segment
    "nr_in_seg" INTEGER, -- cross-section number in segment
    "ichangrid" INTEGER, -- ICHANGRID, grid element number for left bank
    "fcn" REAL, -- FCN, average Manning's n in the grid element
    "xlen" REAL, -- channel length contained within the grid element ICHANGRID
    "nxecnum" INTEGER, -- NXSECNUM, surveyed cross section number assigned in XSEC.DAT
    "rbankgrid" INTEGER, -- RIGHTBANK, right bank grid element fid
    "xsecname" TEXT, -- xsection name
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('chan_n', 'features', 4326);
SELECT gpkgAddGeometryColumn('chan_n', 'geom', 'LINESTRING', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('chan_n', 'geom');
SELECT gpkgAddSpatialIndex('chan_n', 'geom');

-- TODO: create triggers for geometry INSERT and UPDATE
-- use notes column to flag features created by user!
-- -- create geometry when rightbank and leftbank are given
-- CREATE TRIGGER "chan_n_geom_insert"
--     AFTER INSERT ON "chan_n"
--     WHEN (NEW."ichangrid" NOT NULL AND NEW."rbankgrid" NOT NULL)
--     BEGIN
--         UPDATE "chan_n" 
--             SET geom = (
--                 SELECT 
--                     AsGPB(MakeLine((ST_Centroid(CastAutomagic(g1.geom))),
--                     (ST_Centroid(CastAutomagic(g2.geom)))))
--                 FROM grid AS g1, grid AS g2
--                 WHERE g1.fid = ichangrid AND g2.fid = rbankgrid);
--     END;

--update left and right bank fids when geometry changed
-- CREATE TRIGGER "chan_n_banks_update_geom_changed"
--     AFTER UPDATE ON "chan_n"
--     WHEN ( NEW.notes IS NULL )
--     BEGIN
--         UPDATE "chan_n" SET ichangrid = (SELECT g.fid FROM grid AS g
--             WHERE ST_Intersects(g.geom,StartPoint(CastAutomagic(geom))))
--             WHERE fid = NEW.fid;
--         UPDATE "chan_n" SET rbankgrid = (SELECT g.fid FROM grid AS g
--             WHERE ST_Intersects(g.geom,EndPoint(CastAutomagic(geom))))
--             WHERE fid = NEW.fid;
--     END;

-- CREATE TRIGGER "chan_n_geom_update_banks_changed"
--     AFTER UPDATE OF ichangrid, rbankgrid ON "chan_n"
-- --     WHEN (NEW."ichangrid" NOT NULL AND NEW."rbankgrid" NOT NULL)
--     BEGIN
--         UPDATE "chan_n" 
--             SET geom = (
--                 SELECT 
--                     AsGPB(MakeLine((ST_Centroid(CastAutomagic(g1.geom))),
--                     (ST_Centroid(CastAutomagic(g2.geom)))))
--                 FROM grid AS g1, grid AS g2
--                 WHERE g1.fid = ichangrid AND g2.fid = rbankgrid);
--     END;

CREATE VIEW "chan_elems_in_segment" (
    chan_elem_fid,
    seg_fid
) AS 
SELECT DISTINCT ichangrid, seg_fid FROM chan_r
UNION ALL
SELECT DISTINCT ichangrid, seg_fid FROM chan_v
UNION ALL
SELECT DISTINCT ichangrid, seg_fid FROM chan_t
UNION ALL
SELECT DISTINCT ichangrid, seg_fid FROM chan_n;

CREATE TABLE "chan_confluences" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "conf_fid" INTEGER, -- confluence fid
    "type" INTEGER, -- switch, tributary (0 if ICONFLO1) or main channel (1 if ICONFLO2) 
    "chan_elem_fid" INTEGER, -- ICONFLO1 or ICONFLO2, tributary or main channel element fid
    "seg_fid" INTEGER, -- fid of channel segment 
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('chan_confluences', 'features', 4326);
SELECT gpkgAddGeometryColumn('chan_confluences', 'geom', 'POINT', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('chan_confluences', 'geom');
SELECT gpkgAddSpatialIndex('chan_confluences', 'geom');

-- automatically create/modify geometry of confluences on iconflo1/2 insert/update
CREATE TRIGGER "confluence_geom_insert"
    AFTER INSERT ON "chan_confluences"
    WHEN (NEW."chan_elem_fid" NOT NULL)
    BEGIN
        UPDATE "chan_confluences" 
            SET geom = (SELECT AsGPB(ST_Centroid(CastAutomagic(g.geom))) FROM grid AS g WHERE g.fid = chan_elem_fid);
        -- TODO: set also seg_fid
    END;

CREATE TRIGGER "confluence_geom_update"
    AFTER UPDATE ON "chan_confluences"
    WHEN (NEW."chan_elem_fid" NOT NULL)
    BEGIN
        UPDATE "chan_confluences" 
            SET geom = (SELECT AsGPB(ST_Centroid(CastAutomagic(g.geom))) FROM grid AS g WHERE g.fid = chan_elem_fid);
        -- TODO: set also seg_fid
    END;

CREATE TABLE "noexchange_chan_areas" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "notes" TEXT
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('noexchange_chan_areas', 'features', 4326);
SELECT gpkgAddGeometryColumn('noexchange_chan_areas', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('noexchange_chan_areas', 'geom');
SELECT gpkgAddSpatialIndex('noexchange_chan_areas', 'geom');

CREATE TABLE "noexchange_chan_elems" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "noex_area_fid" INTEGER, -- fid of noexchange_chan_area polygon
    "chan_elem_fid" INTEGER -- NOEXCHANGE, channel element number not exchanging flow. Filled in by a geoprocessing trigger
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('noexchange_chan_elems', 'aspatial');

CREATE TRIGGER "find_noexchange_cells_insert"
    AFTER INSERT ON "noexchange_chan_areas"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "noexchange_chan_elems" WHERE noex_fid = NEW."fid";
        INSERT INTO "noexchange_chan_elems" (noex_fid, grid_fid) 
        SELECT NEW.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_noexchange_cells_update"
    AFTER UPDATE ON "noexchange_chan_areas"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "noexchange_chan_elems" WHERE noex_fid = NEW."fid";
        INSERT INTO "noexchange_chan_elems" (noex_fid, grid_fid) 
        SELECT NEW.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_noexchange_cells_delete"
    AFTER DELETE ON "noexchange_chan_areas"
    BEGIN
        DELETE FROM "noexchange_chan_elems" WHERE noex_fid = OLD."fid";
    END;

CREATE TABLE "chan_wsel" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "seg_fid" INTEGER, -- found by geoprocessing trigger, channel segment for which the WSELs are specified
    "istart" INTEGER, -- ISTART, first channel element with a starting WSEL specified
    "wselstart" REAL, -- WSELSTART, first channel element starting WSEL
    "iend" INTEGER, -- IEND, last channel element with a starting WSEL specified
    "wselend" REAL -- WSELEND, last channel element starting WSEL
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('chan_wsel', 'aspatial');


-- XSEC.DAT

CREATE TABLE "xsec_n_data" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "chan_n_nxsecnum" INTEGER, -- NXSECNUM, fid of cross-section in chan_n
    "x" REAL, -- XI, station distance from left point
    "y" REAL -- YI, elevation
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('xsec_n_data', 'aspatial');


-- EVAPOR.DAT

CREATE TABLE "evapor" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "ievapmonth" INTEGER, -- IEVAPMONTH, starting month of simulation
    "iday" INTEGER, -- IDAY, starting day of the week (1-7)
    "clocktime" REAL -- CLOCKTIME, starting clock time
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('evapor', 'aspatial');

CREATE TABLE "evapor_monthly" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "month" TEXT, -- EMONTH, name of the month
    "monthly_evap" REAL -- EVAP, monthly evaporation rate
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('evapor_month', 'aspatial');

CREATE TABLE "evapor_hourly" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "month" TEXT, -- EMONTH, name of the month
    "hour" INTEGER, -- hour of the day (1-24)
    "hourly_evap" REAL -- EVAPER, Hourly percentage of the daily total evaporation
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('evapor_hourly', 'aspatial');


-- INFIL.DAT

CREATE TABLE "infil" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "infmethod" INTEGER, -- INFMETHOD, infiltration method number
    "abstr" REAL, -- ABSTR, Green Ampt global floodplain rainfall abstraction or interception
    "sati" REAL, -- SATI, Global initial saturation of the soil
    "satf" REAL, -- SATF, Global final saturation of the soil
    "poros" REAL, -- POROS, global floodplain soil porosity
    "soild" REAL, -- SOILD, Green Ampt global soil limiting depth storage
    "infchan" INTEGER, -- INFCHAN, switch for simulating channel infiltration
    "hydcall" REAL, -- HYDCALL, average global floodplain hydraulic conductivity
    "soilall" REAL, -- SOILALL, average global floodplain capillary suction
    "hydcadj" REAL, -- HYDCADJ, hydraulic conductivity adjustment variable
    "hydcxx" REAL, -- HYDCXX, global channel infiltration hydraulic conductivity
    "scsnall" REAL, -- SCSNALL, global floodplain SCS curve number
    "abstr1" REAL, -- ABSTR1, SCS global floodplain rainfall abstraction or interception
    "fhortoni" REAL, -- FHORTONI, global Horton’s equation initial infiltration rate
    "fhortonf" REAL, -- FHORTONF, global Horton’s equation final infiltration rate
    "decaya" REAL --DECAYA, Horton’s equation decay coefficient
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('infil', 'aspatial');

CREATE TABLE "infil_chan_seg" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "chan_seg_fid" INTEGER, -- channel segment fid from chan table
    "hydcx" REAL, -- HYDCX, initial hydraulic conductivity for a channel segment
    "hydcxfinal" REAL, -- HYDCXFINAL, final hydraulic conductivity for a channel segment
    "soildepthcx" REAL -- SOILDEPTHCX, maximum soil depth for the initial channel infiltration
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('infil_chan_seg', 'aspatial');

CREATE TABLE "infil_areas_green" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "hydc" REAL, -- HYDC, grid element average hydraulic conductivity
    "soils" REAL, -- SOILS, capillary suction head for floodplain grid elements
    "dtheta" REAL, -- DTHETA, grid element soil moisture deficit
    "abstrinf" REAL -- ABSTRINF, grid element rainfall abstraction
    "rtimpf" REAL, -- RTIMPF, percent impervious floodplain area on a grid element
    "soil_depth" REAL -- SOIL_DEPTH, maximum soil depth for infiltration on a grid element
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('infil_areas_green', 'features', 4326);
SELECT gpkgAddGeometryColumn('infil_areas_green', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('infil_areas_green', 'geom');
SELECT gpkgAddSpatialIndex('infil_areas_green', 'geom');

    -- Green Ampt

CREATE TABLE "infil_cells_green" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "grid_fid" INTEGER, -- grid element number from grid table
    "infil_area_fid" INTEGER -- polygon fid from infil_areas_green table
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('infil_cells_green', 'aspatial');

CREATE TRIGGER "find_infil_cells_green_insert"
    AFTER INSERT ON "infil_areas_green"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "infil_areas_green" WHERE infil_area_fid = NEW."fid";
        INSERT INTO "infil_areas_green" (infil_area_fid, grid_fid) 
        SELECT NEW.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_infil_cells_green_update"
    AFTER UPDATE ON "infil_areas_green"
    WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
    BEGIN
        DELETE FROM "infil_areas_green" WHERE infil_area_fid = NEW."fid";
        INSERT INTO "infil_areas_green" (infil_area_fid, grid_fid) 
        SELECT NEW.fid, g.fid FROM grid as g
        WHERE ST_Intersects(CastAutomagic(g.geom), CastAutomagic(NEW.geom));
    END;

CREATE TRIGGER "find_infil_cells_green_delete"
    AFTER DELETE ON "infil_areas_green"
    BEGIN
        DELETE FROM "infil_areas_green" WHERE infil_area_fid = OLD."fid";
    END;

    -- SCS

CREATE TABLE "infil_areas_scs" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "scscn" REAL -- SCSCN, SCS curve numbers of the floodplain grid elements
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('infil_areas_scs', 'features', 4326);
SELECT gpkgAddGeometryColumn('infil_areas_scs', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('infil_areas_scs', 'geom');
SELECT gpkgAddSpatialIndex('infil_areas_scs', 'geom');

CREATE TABLE "infil_cells_scs" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "grid_fid" INTEGER, -- grid element number from grid table
    "infil_area_fid" INTEGER -- polygon fid from infil_areas_scs table
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('infil_cells_scs', 'aspatial');

CREATE TABLE "infil_areas_horton" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "fhorti" REAL, -- FHORTI, Horton’s equation floodplain initial infiltration rate
    "fhortf" REAL, -- FHORTF, Horton’s equation floodplain final infiltration rate
    "deca" REAL --DECA, Horton’s equation decay coefficient
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('infil_areas_horton', 'features', 4326);
SELECT gpkgAddGeometryColumn('infil_areas_horton', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('infil_areas_horton', 'geom');
SELECT gpkgAddSpatialIndex('infil_areas_horton', 'geom');

CREATE TABLE "infil_cells_horton" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "grid_fid" INTEGER, -- grid element number from grid table
    "infil_area_fid" INTEGER -- polygon fid from infil_areas_horton table
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('infil_cells_horton', 'aspatial');

CREATE TABLE "infil_areas_chan" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "hydconch" REAL -- HYDCONCH, hydraulic conductivity for a channel element
);
INSERT INTO gpkg_contents (table_name, data_type, srs_id) VALUES ('infil_areas_chan', 'features', 4326);
SELECT gpkgAddGeometryColumn('infil_areas_chan', 'geom', 'POLYGON', 0, 0, 0);
SELECT gpkgAddGeometryTriggers('infil_areas_chan', 'geom');
SELECT gpkgAddSpatialIndex('infil_areas_chan', 'geom');

CREATE TABLE "infil_chan_elems" (
    "fid" INTEGER NOT NULL PRIMARY KEY,
    "grid_fid" INTEGER, -- grid element number from grid table
    "infil_area_fid" INTEGER -- polygon fid from infil_areas_chan table
);
INSERT INTO gpkg_contents (table_name, data_type) VALUES ('infil_chan_elems', 'aspatial');