# Removal_of_watershed_intersection_by_hierarchical_difference
Script for QGIS that automates the hierarchical difference of overlapping polygons, prioritizing areas of higher elevation, reducing the effect of geostatistical circularity in spatial analyses, eliminating the need for repetitive manual adjustments with the 'Difference' tool. Ideal for watershed studies with multiple sampling points.

## Authors
 -Henrique Ledo Lopes Pinho
 -Jéssica Bassani de Oliveira
 -Yzel Rondon Súarez

You must retain the above copyright notice and this permission notice in all copies or substantial portions of the Software.
If you use or modify this code, please give proper credit to the original authors. 

## General Description

This script was developed to run exclusively in the QGIS environment (versions 3.34.5 or higher).

Run the “Difference” tool iteratively between intersecting polygons, giving priority to those with a higher elevation value.

As a result, polygons that previously encompassed the areas of others are reduced in size, ensuring that none have overlapping areas.

This is possible using existing tools (r.watershed, r.water.outlet, Polygonize, Corret Geometry, Dissolve, Zonal Statistics e Difference) in QGIS, combined with additional commands.

**Important: This script cannot be run outside the QGIS environment. It uses internal libraries and tools, such as QGIS `processing` and the GRASS and GDAL modules.


## Requirements

- QGIS:** Version 3.34.5.
- **Operating Systems:** Windows or Linux.
- Required plugins:** GRASS GIS provider and GDAL Tools

## Installation and configuration

1. install QGIS (version 3.34.5);
2. In QGIS, install and/or enable the GRASS plugin:
   - Go to: `Plugins` > `Manage and Install Plugins`.
   - Search for “GRASS GIS provider” and install it.

## Necessary files
- All in the same Coordinate Reference System (we use UTM)
- DEM (Digital Elevation Model):** File in `.tif` format; pre-processed (mosaic, cropping, correction of negative values, filling in pixels without data and removal of spurious depressions).
- Plot the data collected in the field and generate the flow segment to obtain the outflow points close to the actual collection points (if you have problems generating the flow segment in version 3.34, do this in version 3.16);
- Stream coordinates:** `.txt` file with coordinates in `x,y` format.
- **Shapefile of Collected Points:** `.shp` file containing a column called “Points” with the names of the points.

## Project Structure

- `DEM.tif` - Digital elevation model raster.
- `EXUTORY_COORDINATES.txt` - File with the coordinates of the exits.
- `Collected_Points.shp` - Shapefile with the collection points.
- `stream_segment.tif` - (Optional) The script does not require this layer to be saved in a specific directory in order to work. 
However, we recommend that the user saves this layer to disk, as this makes it easier to visually check that the points are correctly positioned in the pixel corresponding to the stream segment.
- `INTERMEDIARY_FILES/` - Folder for intermediate output files.
- `FINAL_POLYGONS/` - Folder for the final output files (areas of influence).

## Running the Script

1. Open QGIS.
2. Go to `Plugins` > `Python Console`.
3. Copy and paste the contents of the file `Script.py` into the QGIS Python console.
4. Select the entire command (CTRL+A) and press `Enter` to execute.

## Generated Outputs

- `drainage_direction.tif` - Drainage direction.
- `basin_[Point].shp` - Delimited basins for each exuctory point.
- `dissolved_basin_[Point].shp` - Basins with corrected geometries.
- `zonal_basin_[Point].shp` - Shapefile with zonal statistics.
- `exclusive_contribution_area_[Point].shp` - Exclusive Contribution Area for each point.

## Recommendations and Care

1. **Do not change the indentation of the code:** Changes may cause errors.
2. **Check the configuration paths:** Use forward slashes `/` to avoid system errors.
3. **Don't use spaces and special characters **(ç, ã, é, #, @, etc.)**
4. **Avoid very long names **(more than 30 characters can cause problems)**
5. **Correct formats:**
   - Coordinate file: `.txt` with `x,y` separated by a comma.
   - Shapefile of points: Must contain a “Points” column.
6. **Permissions:** Make sure the output directory allows recording.
7. ** If the study area has flat slopes with low variation in elevation, the stream segment will be less accurately aligned with the actual water course, 
and this is due to the limited spatial resolution of the DEM and not due to algorithmic limitations.

## Situations in which the algorithm will not work:
-Use versions prior to 3.34-Prizren to run the script;
-Different coordinate reference system between the .shp file and the raster file;
-Exuture coordinates outside the pixel of the stream segment;
-Space in the .txt file;
-The coordinates of the exuctory points are different from those in the .shp file;
-The column names are different from the example file.
-Try running it a second time without deleting the "INTERMEDIARY_FILES" and "FINAL_POLYGONS" folder.

## Institutional support and partnerships

-State University of Mato Grosso do Sul (UEMS), Dourados, Brazil
-Center for Studies in Natural Resources (CERNA-UEMS), Dourados, Brazil
-Postgraduate Program in Natural Resources (PGRN-UEMS), Dourados, Brazil
-Bachelor's Degree in Information Systems (UEMS), Dourados, Brazil
-Aquatic Environments Studies Laboratory (GEAAQUA - UEMS), Dourados, Brazil
-Technological Innovation Center of the State University of Mato Grosso do Sul (NIT-UEMS), Brazil

## Development agencies

-Coordination for the Improvement of Higher Education Personnel (CAPES), Brazil
-National Council for Scientific and Technological Development (CNPq), Brazil
-Foundation for Support of Education, Science and Technology of the State of Mato Grosso do Sul (Fundect), Brazil

## Contact

For support or questions, please contact one of the authors at: geaaqua@uems.br

---

## License

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
