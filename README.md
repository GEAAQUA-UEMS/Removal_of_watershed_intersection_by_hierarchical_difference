# HED-ECA - Removal of watershed intersection by hierarchical difference

Semi-automated script for QGIS that generates exclusive contribution areas (ECAs),
automating the hierarchical difference between overlapping polygons and prioritizing
areas of higher elevation. It also generates hydrological connectivity chains between
sampling points. Especially useful in hydrological and limnological studies for
environmental monitoring with multiple sampling points.

## General Description

This script was developed to run exclusively in the QGIS environment (version 3.34.5).

It runs the "Difference" tool iteratively between intersecting polygons, giving priority
to those with higher elevation values. As a result, polygons that previously encompassed
the areas of others are reduced in size, ensuring that none have overlapping areas.

Additionally, the script traces the full spatial dependency between basins, identifying
which sampling points are nested within larger basins (upstream–downstream relationships),
and records the complete hierarchical connectivity chain for each point.

This is possible using existing tools (r.watershed, r.water.outlet, Polygonize,
Correct Geometry, Dissolve, Zonal Statistics, and Difference) in QGIS, combined
with additional commands.

This script implements the HED-ECA (Hierarchical Elevation-Driven Exclusive Contribution Areas) method, registered at the Brazilian National Institute of Industrial Property (INPI) under the title 'Removal of watershed intersection by hierarchical difference'.

**Important:** This script cannot be run outside the QGIS environment. It uses
internal libraries and tools such as QGIS `processing` and the GRASS and GDAL modules.


## Requirements

- **QGIS:** Version 3.34.5
- **Operating Systems:** Windows or Linux
- **Required plugins:** GRASS GIS provider and GDAL Tools


## Installation and Configuration

1. Install QGIS (version 3.34.5).
2. In QGIS, install and/or enable the GRASS plugin:
   - Go to: `Plugins` > `Manage and Install Plugins`
   - Search for "GRASS GIS provider" and install it.


## Necessary Files

- All files must share the same Coordinate Reference System (UTM recommended).
- **DEM (Digital Elevation Model):** File in `.tif` format; pre-processed (mosaic,
  cropping, correction of negative values, filling pixels without data, and removal
  of spurious depressions).
- Plot field-collected data and generate the flow segment to obtain outflow points
  close to actual collection points (if you have problems generating the flow segment
  in version 3.34, do this in version 3.16).
- **Stream coordinates:** `.txt` file with coordinates in `x,y` format.
- **Shapefile of Collected Points:** `.shp` file containing a column called `"Points"`
  with the names of the points.


## Project Structure

- `DEM.tif` — Digital elevation model raster.
- `EXUTORY_COORDINATES.txt` — File with the coordinates of the outlets.
- `Collected_Points.shp` — Shapefile with the collection points.
- `stream_segment.tif` — (Optional) The script does not require this layer to be
  saved in a specific directory. However, saving it to disk is recommended to
  visually verify that points are correctly positioned on the stream segment pixel.
- `INTERMEDIARY_FILES/` — Folder for intermediate output files.
- `FINAL_POLYGONS/` — Folder for the final output files (exclusive contribution areas
  and connectivity results).


## Running the Script

1. Open QGIS.
2. Go to `Plugins` > `Python Console`.
3. Copy and paste the contents of the file `Script_HED_ECA.py` into the QGIS
   Python console.
4. Select the entire command (`CTRL+A`) and press `Enter` to execute.


## Processing Steps

The script executes five sequential parts:

**Part 1 — Basin Delimitation:** Uses `r.watershed` and `r.water.outlet` to delimit
individual drainage basins for each sampling point, converting outputs to corrected
and dissolved vector polygons.

**Part 2 — Zonal Statistics:** Calculates minimum elevation statistics from the DEM
for each basin polygon. This value is used in Part 3 to establish hierarchical priority.

**Part 3 — Hierarchical Difference:** Sorts basins by minimum elevation (higher
elevation = higher priority), detects intersections, and iteratively subtracts
overlapping areas. Also detects spatial containment relationships between basins and
records them in `basin_dependency.txt`.

**Part 4 — Connectivity Chains:** Reads `basin_dependency.txt` and traces the full
upstream-to-downstream path for each point, generating complete hierarchical
connectivity chains (e.g., `Point1 -> Point110 -> Point4 -> Point61`). Redundant
sub-chains are filtered so only the most complete paths are reported.

**Part 5 — Upstream Attribute:** For each ECA shapefile, adds a field named
`upstream` containing a comma-separated, topologically ordered list of all upstream
ancestor basins (from the most distant headwater to the immediate upstream neighbour).
Elevation is used as a tiebreaker for parallel tributary branches. The `Collected Points`
layer is automatically moved to the top of the QGIS layer panel upon completion.


## Generated Outputs

**Intermediate files (in `INTERMEDIARY_FILES/`):**
- `drainage_direction.tif` — Drainage direction raster.
- `basin_[Point].shp` — Raw vectorized basin for each outlet point.
- `corrected_basin_[Point].shp` — Basin with corrected geometries.
- `dissolved_basin_[Point].shp` — Dissolved basin polygon.
- `zonal_basin_[Point].shp` — Basin with minimum elevation zonal statistics.

**Final outputs (in `FINAL_POLYGONS/`):**
- `ECA_[Point].shp` — Exclusive Contribution Area for each point, including the
  `upstream` attribute field listing all upstream basins in hierarchical order.
- `basin_dependency.txt` — Table of direct upstream–downstream relationships
  (columns: `Upstream_Basin`, `Downstream_Basin`).
- `basin_dependency_chains.txt` — Complete spatial connectivity chains from
  headwater to final outlet for each sampling point.


## Recommendations and Care

1. **Do not change the indentation of the code:** Changes may cause execution errors.
2. **Check configuration paths:** Use forward slashes `/` to avoid system errors.
3. **Do not use spaces or special characters** (ç, ã, é, #, @, etc.) in file or
   folder names.
4. **Avoid very long names** (more than 30 characters can cause problems).
5. **Correct formats:**
   - Coordinate file: `.txt` with `x,y` separated by a comma, no spaces.
   - Shapefile of points: must contain a `"Points"` column.
6. **Permissions:** Make sure the output directory allows writing.
7. If the study area has flat slopes with low variation in elevation, the stream
   segment will be less accurately aligned with the actual watercourse. This is
   due to the limited spatial resolution of the DEM, not an algorithmic limitation.


## Situations in Which the Algorithm Will Not Work

- Using QGIS versions prior to 3.34-Prizren.
- Different coordinate reference systems between the `.shp` file and the raster file.
- Outlet coordinates outside the pixel of the stream segment.
- Spaces in the `.txt` coordinate file.
- Outlet point coordinates that differ from those in the `.shp` file.
- Column names different from the expected format (`"Points"`).
- Running the script a second time without deleting the `INTERMEDIARY_FILES` and
  `FINAL_POLYGONS` folders.


## License

This program is free software; you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version.
