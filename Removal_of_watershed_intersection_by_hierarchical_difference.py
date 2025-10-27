"""
**********************************************************************************************************************
    Removal of watershed intersection by hierarchical difference.py                                                  *
    -----------------------------------------------------------------------------------------------------------------*
    Date                 : March 2025                                                                                *
    Copyright            : (C) 2025 by Henrique Ledo Lopes Pinho, Jéssica Bassani de Oliveira, Yzel Rondon Súarez    *
    Email                : geaaqua@uems.br                                                                           *
**********************************************************************************************************************
*                                                                                                                    *
*   This program is free software; you can redistribute it and/or modify it under the terms of the GNU General       *
*   Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option)*
*   any later version.                                                                                               *
*                                                                                                                    *
**********************************************************************************************************************
"""

#IMPORTANT RECOMMENDATIONS FOR THE USER:
# - **Do not change the indentation of the code**: Indentation (alignment) is essential for the script to work. 
# Changes can cause execution errors.
# - **Check the paths of the initial settings**:
# 1. make sure that the indicated files (DEM, coordinates, shapefiles) are in the specified locations.
# Use normal forward slashes `/` for the paths, as backslashes `\` can cause errors depending on the operating system.
# Confirm the file formats:
# The coordinates file for the exits must be in `.txt` format with coordinates in `x,y` format (separated by a comma).
# The shapefile of collected points must contain a column called "Points" with the names of the collection points.
# - **Make sure that QGIS is configured correctly**:
# 1. QGIS must be installed and configured on the system.
# Check that all the necessary plugins (GRASS and GDAL) are installed and working.
# - **Operating system permissions**:
# 1. Make sure that the output directory has write permissions.
# The script may not work correctly if there are read or write restrictions on the input/output directories.
# - **Operating system compatibility**:
# This script is designed to work on Windows or Linux systems with QGIS installed. 
# Check the file paths and adapt them as necessary.
# ==============================================================

import os
import processing
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsProject

# Function to add layers to the project
# ========================================
def add_layer_to_project(layer, name):
    """
    Adds layers to the QGIS project.
    Checks if the layer is valid and, if so, adds it to the project.
    """
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        print(f"Layer '{name}' loaded into the project.")
    else:
        print(f"Error: Layer '{name}' is not valid and has not been loaded.")

# Initial configuration: Paths and Global Parameters
# ====================================================
dem_path = "C:/EXAMPLE/ELEVATION_RASTER/DEM.tif" #Directory where the digital elevation model raster is stored
exutory_txt = "C:/EXAMPLE/EXUTORY_COORDINATES/EXUTORY_COORDINATES.txt"#Directory where this coordinates of the exuctory are stored
collection_shp = "C:/EXAMPLE/COLLECTED_POINTS/Collected_Points.shp"#Directory where the shapefile with the collected points is stored
intermediary_layers_dir = "C:/EXAMPLE/INTERMEDIARY_FILES/"#Defines the output directory for the intermediate layers (generates a new folder)
final_polygon_dir = "C:/EXAMPLE/FINAL_POLYGONS/"#Defines the output directory containing the areas of influence (generates a new folder)
stream_segments_path = "C:/EXAMPLE/STREAM_SEGMENTS/stream_segments.tif"#Directory where the stream segment this stored (Optional)
threshold = 1000#Threshold parameter for basins outside the main watercourse
convergence = 5#Convergence factor for multiple flow direction
memory = 300#Maximum memory to be used (in MB)

# Part 1: River Basin Delimitation
# ============================================
def process_basin_delimitation():
    """
     Part 1: River Basin Delimitation in QGIS.
    Performs the basin delimitation process using the digital elevation model (DEM)
    and the specified outflow points.
    """
    print("Executing Part 1: Basin Delimitation")

    # Create the output directories if they don't exist
    os.makedirs(intermediary_layers_dir, exist_ok=True)
    os.makedirs(final_polygon_dir, exist_ok=True)

    # Reading the coordinates from the exits file
    outlet_coords = []
    with open(exutory_txt, mode='r') as txtfile:
        for line in txtfile:
            # Ignore header and edit coordinates (x, y)
            if 'x' in line.lower() and 'y' in line.lower():
                continue
            x, y = map(float, line.strip().split(','))
            outlet_coords.append({'x': x, 'y': y})

    # Load the Digital Elevation Model (DEM)
    print("Loading the Digital Elevation Model (DEM)...")
    dem_layer = QgsRasterLayer(dem_path, "Digital Elevation Model")
    if not dem_layer.isValid():
        raise RuntimeError(f"Erro: The raster could not be loaded in the path {dem_path}")
    add_layer_to_project(dem_layer, "Digital Elevation Model")

    # Load the collection points
    print("Loading collection points...")
    collection_layer = QgsVectorLayer(collection_shp, "Collected Points", "ogr")
    if not collection_layer.isValid():
        raise RuntimeError(f"Error: Unable to load point shapefile on path {collection_shp}")
    add_layer_to_project(collection_layer, "Collected Points")

    # Extract the names of the points collected
    collection_features = collection_layer.getFeatures()
    collection_names = [feature['Points'] for feature in collection_features]

    # If the path of the flow segment has been entered, load the layer
    if stream_segments_path:
        print("Loading stream segments...")
        segments_layer = QgsRasterLayer(stream_segments_path, "Stream Segments")
        if segments_layer.isValid():
            add_layer_to_project(segments_layer, "Stream Segments")
        else:
            print(f"Erro: Could not load flow segment in path {stream_segments_path}")


    # Run r.watershed to calculate drainage direction and stream segments
    print("Executing r.watershed...")
    drainage_output = os.path.join(intermediary_layers_dir, "drainage_direction.tif")
    processing.run("grass7:r.watershed", {
        'elevation': dem_path,
        'threshold': threshold,
        'convergence':convergence,
        'memory':memory,
        'drainage': drainage_output,
        'GRASS_REGION_PARAMETER': f"{dem_path}",
        'GRASS_REGION_CELLSIZE_PARAMETER': 0
    })

   # Load the drainage direction into the project
    drainage_layer = QgsRasterLayer(drainage_output, "Drainage Direction")
    if drainage_layer.isValid():
        add_layer_to_project(drainage_layer, "Drainage Direction")
    else:
        print(f"Error: Unable to load drainage direction raster in {drainage_output}")

   
   # Generate watersheds for each exutory of points
    corrected_outputs = []
    for coord, collection_name in zip(outlet_coords, collection_names):
        raster_output = os.path.join(intermediary_layers_dir, f"basin_{collection_name}.tif")
        vector_output = os.path.join(intermediary_layers_dir, f"basin_{collection_name}.shp")
        corrected_output = os.path.join(intermediary_layers_dir, f"corrected_basin_{collection_name}.shp")

        # Execute r.water.outlet to delimit the basin of the exutory point
        print(f"Running r.water.outlet for the point {collection_name}...")
        processing.run("grass7:r.water.outlet", {
            'input': drainage_output,
            'coordinates': f"{coord['x']},{coord['y']}",
            'output': raster_output,
            'GRASS_REGION_PARAMETER': f"{dem_path}",
            'GRASS_REGION_CELLSIZE_PARAMETER': 0
        })

        # Convert the output raster to vector (polygonize)
        print("Correcting geometry...")
        processing.run("gdal:polygonize", {
            'INPUT': raster_output,
            'FIELD': "DN",
            'OUTPUT': vector_output
        })
        processing.run("native:fixgeometries", {
            'INPUT': vector_output,
            'OUTPUT': corrected_output
        })
        corrected_outputs.append(corrected_output)

    # Dissolve the geometries of the corrected basins
    dissolved_outputs = []
    for corrected_output, collection_name in zip(corrected_outputs, collection_names):
        dissolved_output = os.path.join(intermediary_layers_dir, f"dissolved_basin_{collection_name}.shp")

        print(f"Dissolving geometries for the point {collection_name}...")
        processing.run("native:dissolve", {
            'INPUT': corrected_output,
            'OUTPUT': dissolved_output
        })
        dissolved_outputs.append(dissolved_output)

    print("Part 1 successfully completed!")



# Part 2: Calculating Zonal Statistics
# ========================================
def calculate_zonal_statistics():
    """
    Part 2: Calculating Zonal Statistics.
    Calculates digital elevation model statistics for each basin.
    """
    print("Executing Part 2: Zonal Statistics")

    # Identify shapefiles in the temporary polygon directory
    shapefiles = [
        os.path.join(intermediary_layers_dir, file)
        for file in os.listdir(intermediary_layers_dir)
        if file.startswith("dissolved_basin_") and file.endswith(".shp")
    ]

    if not shapefiles:
        print("No shapefile found to process.")
        return

    print(f"Shapefiles found: {shapefiles}")

    # Load the Collected Points layer
    points_layer = QgsVectorLayer(collection_shp, "Collected Points", "ogr")
    if not points_layer.isValid():
        print("Erro: The file could not be uploaded Collected_Points.shp.")
        return

    points_nomes = [feature["Points"] for feature in points_layer.getFeatures()]
    if len(points_nomes) != len(shapefiles):
        print("Error: The number of collected points does not match the number of shapefiles.")
        return

    for shapefile in shapefiles:
        # Extract the shapefile suffix
        suffix = os.path.basename(shapefile).split("dissolved_basin_")[1].replace(".shp", "")

        output_path = os.path.join(intermediary_layers_dir, f"zonal_basin_{suffix}.shp")
        print(f"Processing {shapefile} for the suffix {suffix}...")

        # Calculating zonal statistics
        print("alculating zonal statistics...")
        try:
            processing.run("native:zonalstatisticsfb", {
                'INPUT': shapefile,             # The shapefile containing the basins for which the zonal statistics will be calculated.
                'INPUT_RASTER': dem_path,       # The input raster (in this case, the Digital Elevation Model - DEM).
                'RASTER_BAND': 1,               # The number of the raster band that will be used for the calculation (usually 1 for rasters with a single band).
                'COLUMN_PREFIX': '_',           # Prefix added to the names of the output columns in the shapefile to identify the results of the statistics.
                'STATISTICS': [5],              # List of statistics to be calculated. The value 5 indicates that the **minimum value** of the elevations in the raster within each polygon of the shapefile will be calculated.
                'OUTPUT': output_path           # Path where the output shapefile will be saved, containing the calculated statistics as additional attributes.
            })
            print(f"Zonal statistics calculated for {shapefile}. Output: {output_path}")
        except Exception as e:
            print(f"Error in calculating zonal statistics for {shapefile}: {e}")

    print("Part 2 successfully completed!")


# Part 3: Processing Differences between Basins.
# ==================================================
def process_basin_difference():
    """
    Part 3: Processing differences between basins.
    Sorts shapefiles based on minimum elevation, calculates differences between basins
    to generate unique basins.
    """
    print("Executing Part 3: Differences between Basins")

    shapefiles = [
        os.path.join(intermediary_layers_dir, file)
        for file in os.listdir(intermediary_layers_dir)
        if file.startswith("zonal_basin_") and file.endswith(".shp")
    ]

    if not shapefiles:
        print("No zonal basin shapefile found to process.")
        return

    elevation_stats = []
    for shapefile in shapefiles:
        suffix = os.path.basename(shapefile).split("zonal_basin_")[1].replace(".shp", "")

        layer = QgsVectorLayer(shapefile, "", "ogr")
        for feature in layer.getFeatures():
            if '_min' in feature.fields().names():
                elevation_stats.append({'path': shapefile, 'min': feature['_min'], 'suffix': suffix})

    elevation_stats = sorted(elevation_stats, key=lambda x: x['min'], reverse=True)

    output_files = []

    for i, current_stat in enumerate(elevation_stats):
        suffix = current_stat['suffix']
        # Save influence_area files in the FINAL_POLYGON directory
        output_path = os.path.join(final_polygon_dir, f"exclusive_contribution_area_{suffix}.shp")

        if i == 0:
            processing.run("native:savefeatures", {
                'INPUT': current_stat['path'],
                'OUTPUT': output_path
            })
        else:
            temp_base_path = current_stat['path']
            for j in range(i):
                overlay_layer_path = elevation_stats[j]['path']
                # INTERMEDIARY files remain in INTERMEDIARY LAYERS directory
                temp_output = os.path.join(intermediary_layers_dir, f"temp_diff_{i}_{j}.shp")
                processing.run("native:difference", {
                    'INPUT': temp_base_path,
                    'OVERLAY': overlay_layer_path,
                    'OUTPUT': temp_output
                })
                temp_base_path = temp_output

            processing.run("native:savefeatures", {
                'INPUT': temp_base_path,
                'OUTPUT': output_path
            })

        output_files.append(output_path)

    # Load all layers to the project (including influence_area files from FINAL_POLYGON)
    project = QgsProject.instance()
    
    
    # Load final influence_area files from FINAL_POLYGON directory
    for output_file in output_files:
        layer_name = os.path.basename(output_file).replace(".shp", "")
        layer = QgsVectorLayer(output_file, layer_name, "ogr")
        if layer.isValid():
            project.addMapLayer(layer)

    print("Part 3 successfully completed!")


# ==================================================
# Execute all parts
process_basin_delimitation()
calculate_zonal_statistics()
process_basin_difference()


print("Processing completed successfully! All the parts have been executed.")
