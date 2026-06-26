"""
**********************************************************************************************************************
    HED-ECA v2.0 — Hydrological connectivity chain derivation.py                                                     *
    -----------------------------------------------------------------------------------------------------------------*
    Date                 : June 2026                                                                                 *
    Copyright            : Anonymous version for peer review                                                         *
    Email                : Anonymous version for peer review                                                         *
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
from qgis.core import (
    QgsVectorLayer, QgsRasterLayer, QgsProject,
    QgsField, QgsVectorFileWriter, QgsCoordinateTransformContext
)
from PyQt5.QtCore import QVariant

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
dem_path = "C:/1_HED_ECA/ELEVATION_RASTER/DSM.tif" #Directory where the digital elevation model raster is stored
exutory_txt = "C:/1_HED_ECA/EXUTORY_COORDINATES/EXUTORY_COORDINATES.txt"#Directory where this coordinates of the exuctory are stored
collection_shp = "C:/1_HED_ECA/COLLECTED_POINTS/Collected_Points.shp"#Directory where the shapefile with the collected points is stored
intermediary_layers_dir = "C:/1_HED_ECA/INTERMEDIARY_FILES"#Defines the output directory for the intermediate layers (generates a new folder)
final_polygon_dir = "C:/1_HED_ECA/FINAL_POLYGONS"#Define the output directory that will contain the exclusive contribution areas (generates a new folder)
stream_segments_path = "C:/1_HED_ECA/STREAM_SEGMENTS/STREAM_SEGMENTS.tif"#Directory where the stream segment this stored (Optional)
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

    # ensure output folder exists
    os.makedirs(final_polygon_dir, exist_ok=True)
    
    # ===============================================
    # Detect spatial dependency between basins
    # ===============================================
    dependency_file = os.path.join(final_polygon_dir, "basin_dependency.txt")

    with open(dependency_file, "w") as dep:
        dep.write("Upstream_Basin,Downstream_Basin\n")

        for i in range(len(elevation_stats)):
            basin_i_path = elevation_stats[i]['path']
            basin_i_name = elevation_stats[i]['suffix']
            layer_i = QgsVectorLayer(basin_i_path, "", "ogr")

            for j in range(i + 1, len(elevation_stats)):
                basin_j_path = elevation_stats[j]['path']
                basin_j_name = elevation_stats[j]['suffix']
                layer_j = QgsVectorLayer(basin_j_path, "", "ogr")

                for feat_i in layer_i.getFeatures():
                    geom_i = feat_i.geometry()

                    for feat_j in layer_j.getFeatures():
                        geom_j = feat_j.geometry()

                        if geom_i.intersects(geom_j):
                            # check containment
                            if geom_j.contains(geom_i):
                                dep.write(f"{basin_i_name},{basin_j_name}\n")
                            elif geom_i.contains(geom_j):
                                dep.write(f"{basin_j_name},{basin_i_name}\n")

    print("Spatial dependency file generated.")

    for i, current_stat in enumerate(elevation_stats):
        suffix = current_stat['suffix']
        # Save exclusive_contribution_area files in the FINAL_POLYGON directory
        output_path = os.path.join(final_polygon_dir, f"ECA_{suffix}.shp")

        if i == 0:
            processing.run("native:savefeatures", {
                'INPUT': current_stat['path'],
                'OUTPUT': output_path
            })
        else:
            temp_base_path = current_stat['path']
            layer_i = QgsVectorLayer(temp_base_path, "", "ogr")

            intersecting_basins = []
            
            print(f"Analyzing overlaps for basin {suffix} (comparing with {i} previous basins)...")

            # Detect which previous basins intersect
            for j in range(i):
                overlay_path = elevation_stats[j]['path']
                layer_j = QgsVectorLayer(overlay_path, "", "ogr")

                for feat_i in layer_i.getFeatures():
                    geom_i = feat_i.geometry()

                    for feat_j in layer_j.getFeatures():
                        geom_j = feat_j.geometry()

                        if geom_i.intersects(geom_j):
                            intersecting_basins.append(overlay_path)
                            break

            # Calculate performance gain to show in the console
            skipped_basins = i - len(intersecting_basins)
            if skipped_basins > 0:
                print(f"  -> Great! No intersection with {skipped_basins} basin(s). Heavy processing avoided!")
            
            # If there are intersections, perform difference
            if intersecting_basins:
                print(f"  -> Executing topological difference only on the {len(intersecting_basins)} overlapping basin(s)...")
                for overlay_layer_path in intersecting_basins:
                    
                    # Ensuring the temporary output file name is clean
                    overlay_name = os.path.basename(overlay_layer_path).replace('.shp', '')
                    temp_output = os.path.join(
                        intermediary_layers_dir,
                        f"temp_diff_{i}_{overlay_name}.shp"
                    )

                    processing.run("native:difference", {
                        'INPUT': temp_base_path,
                        'OVERLAY': overlay_layer_path,
                        'OUTPUT': temp_output
                    })
                    temp_base_path = temp_output
            else:
                print("  -> No overlap found. Saving polygon directly!")

            # Save final polygon
            processing.run("native:savefeatures", {
                'INPUT': temp_base_path,
                'OUTPUT': output_path
            })

        output_files.append(output_path)

    # Load all layers to the project (including exclusive_contribution_area files from FINAL_POLYGON)
    project = QgsProject.instance()
    
    # Load final exclusive_contribution_area files from FINAL_POLYGON directory
    for output_file in output_files:
        layer_name = os.path.basename(output_file).replace(".shp", "")
        layer = QgsVectorLayer(output_file, layer_name, "ogr")
        if layer.isValid():
            project.addMapLayer(layer)

    print("Part 3 successfully completed!")
    
# Part 4: Hierarchical Connectivity Chains
# ==================================================
def generate_dependency_chains():
    """
    Part 4: Hierarchical Connectivity Chains.
    Correctly traces the full nested hierarchy of points (e.g., 1 -> 110 -> 4 -> 61)
    by identifying all intermediate basins between a point and the final exutory.
    """
    print("Executing Part 4: Generating hierarchical connectivity chains")

    dependency_file = os.path.join(final_polygon_dir, "basin_dependency.txt")
    dependency_file2 = os.path.join(final_polygon_dir, "basin_dependency_chains.txt")

    if not os.path.exists(dependency_file):
        print(f"Error: Base dependency file not found at {dependency_file}")
        return

    # 1. Create a map of ALL downstream connections for each point
    # Mapping: point -> list of ALL points that contain it
    connections = {}
    all_points = set()

    with open(dependency_file, "r") as f:
        lines = f.readlines()[1:] # Skip header
        for line in lines:
            if ',' in line:
                u, d = line.strip().split(',')
                if u not in connections:
                    connections[u] = []
                connections[u].append(d)
                all_points.add(u)
                all_points.add(d)

    # 2. Build hierarchical chains
    final_chains = []
    
    # Identify points that are NOT downstream of anyone else (potential headwaters)
    # or simply process all points to find their full path to the exit.
    for start_point in all_points:
        path = [start_point]
        current = start_point
        
        # While there is a basin containing the current one
        while current in connections:
            # Sort containers by area or logic (here we use the one with the smallest 
            # 'min' elevation next, which is already the logic of your Part 3)
            # For simplicity, we take the direct dependency found in your spatial join
            possible_next = connections[current]
            
            # If there are multiple, we need the "immediate" next.
            # In your logic, the immediate next is the one with the highest 'min' 
            # elevation among those that contain it.
            if len(possible_next) > 1:
                # We stop or choose the best fit. Usually, spatial 'contains' 
                # in a nested set will have the immediate container as the first match.
                next_point = possible_next[0] 
            else:
                next_point = possible_next[0]
                
            path.append(next_point)
            current = next_point
            
        if len(path) > 1:
            final_chains.append(" -> ".join(path))

    # 3. Filter chains to keep only the most complete ones (optional)
    # If we have 1->110->4->61, we don't need 110->4->61 as a separate line.
    final_output = []
    sorted_chains = sorted(list(set(final_chains)), key=len, reverse=True)
    
    for i, chain in enumerate(sorted_chains):
        is_subchain = False
        for j, other_chain in enumerate(sorted_chains):
            if i != j and chain in other_chain:
                is_subchain = True
                break
        if not is_subchain:
            final_output.append(chain)

    # 4. Save to file
    with open(dependency_file2, "w") as dep2:
        dep2.write("Complete Spatial Connectivity Chains:\n")
        dep2.write("=====================================\n")
        for c in sorted(final_output):
            dep2.write(f"{c}\n")

    print(f"Part 4 successfully completed! Chains saved to: {dependency_file2}")


# Part 5: Add upstream basin list as attribute field in each ECA shapefile
# =========================================================================
def add_upstream_attribute():
    """
    Part 5: Upstream Basin Attribute.
    Reads basin_dependency.txt, computes ALL transitive upstream ancestors
    for every point, then writes a new field 'upstream' in each
    ECA_<suffix>.shp inside FINAL_POLYGONS.
    Points that have no upstream basins receive an empty string.

    Uses dataProvider() directly to ensure changes are written to disk
    regardless of whether the layer is already loaded in the QGIS project.
    """
    print("Executing Part 5: Adding upstream attribute to ECA polygons")

    from qgis.core import QgsVectorDataProvider

    dependency_file = os.path.join(final_polygon_dir, "basin_dependency.txt")

    if not os.path.exists(dependency_file):
        print(f"Error: Dependency file not found at {dependency_file}. Run Part 3 first.")
        return

    # ------------------------------------------------------------------
    # 1. Build a reverse map: downstream -> set of DIRECT upstream points
    #    Example: {'Point61': {'Point4'}, 'Point4': {'Point1', 'Point110'}}
    # ------------------------------------------------------------------
    direct_upstream = {}   # downstream -> {direct upstream neighbours}
    all_points = set()

    with open(dependency_file, "r") as f:
        lines = f.readlines()[1:]  # skip header
        for line in lines:
            line = line.strip()
            if ',' not in line:
                continue
            up, down = line.split(',', 1)
            up, down = up.strip(), down.strip()
            if down not in direct_upstream:
                direct_upstream[down] = set()
            direct_upstream[down].add(up)
            all_points.add(up)
            all_points.add(down)

    # ------------------------------------------------------------------
    # 2. For each point, compute ALL transitive upstream ancestors via BFS
    # ------------------------------------------------------------------
    def get_all_upstream(point):
        """Returns the set of ALL upstream ancestors for a given point."""
        visited = set()
        queue = list(direct_upstream.get(point, []))
        while queue:
            current = queue.pop(0)
            if current not in visited:
                visited.add(current)
                queue.extend(direct_upstream.get(current, []))
        return visited

    # ------------------------------------------------------------------
    # 2b. Read minimum elevation for each point from zonal shapefiles.
    #     Used as tiebreaker for parallel branches (afluentes irmãos).
    #     Higher min elevation = more upstream = comes first.
    # ------------------------------------------------------------------
    min_elevation = {}  # suffix -> float(_min)
    for zonal_file in os.listdir(intermediary_layers_dir):
        if zonal_file.startswith("zonal_basin_") and zonal_file.endswith(".shp"):
            z_suffix = zonal_file.replace("zonal_basin_", "").replace(".shp", "")
            z_layer = QgsVectorLayer(
                os.path.join(intermediary_layers_dir, zonal_file), "", "ogr"
            )
            for feat in z_layer.getFeatures():
                if '_min' in feat.fields().names():
                    min_elevation[z_suffix] = feat['_min']
                    break

    def elev_key(point):
        """Higher elevation = more upstream = sorted first (descending)."""
        return -min_elevation.get(point, 0)

    # ------------------------------------------------------------------
    # 2c. Topological sort of ancestors: most upstream (headwater) first,
    #     immediate upstream of the current point last.
    #     Uses Kahn's algorithm; parallel branches are broken by elevation.
    # ------------------------------------------------------------------
    def topological_sort_ancestors(ancestors):
        """
        Given a set of ancestor point names, returns them sorted from
        the most upstream (headwater) to the most downstream (closest
        to the current point). Parallel branches (same in_degree==0 at
        the same time) are ordered by minimum elevation descending so
        the highest point always appears first.
        """
        if not ancestors:
            return []

        # Build a subgraph restricted to these ancestors.
        in_degree = {a: 0 for a in ancestors}
        sub_edges = {a: [] for a in ancestors}

        for a in ancestors:
            for up in direct_upstream.get(a, []):
                if up in ancestors:
                    sub_edges[up].append(a)
                    in_degree[a] += 1

        # Kahn's BFS — tiebreaker: higher elevation first
        queue = sorted([a for a in ancestors if in_degree[a] == 0], key=elev_key)
        ordered = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for downstream_node in sorted(sub_edges[node], key=elev_key):
                in_degree[downstream_node] -= 1
                if in_degree[downstream_node] == 0:
                    queue.append(downstream_node)
            queue.sort(key=elev_key)  # re-sort after each insertion

        # Safety: append any remaining nodes (e.g. in case of cycles)
        remaining = [a for a in ancestors if a not in ordered]
        ordered.extend(sorted(remaining, key=elev_key))
        return ordered

    upstream_map = {}  # point -> hierarchically ordered comma-separated string
    for point in all_points:
        ancestors = get_all_upstream(point)
        ordered_ancestors = topological_sort_ancestors(ancestors)
        upstream_map[point] = ','.join(ordered_ancestors) if ordered_ancestors else ''

    # ------------------------------------------------------------------
    # 3. For each ECA shapefile, add the 'upstream' field via dataProvider
    #    so that writes go straight to disk without depending on the
    #    QGIS project edit buffer.
    # ------------------------------------------------------------------
    eca_files = [
        f for f in os.listdir(final_polygon_dir)
        if f.startswith("ECA_") and f.endswith(".shp")
    ]

    if not eca_files:
        print("No ECA shapefile found in FINAL_POLYGONS. Run Part 3 first.")
        return

    field_name = 'upstream'   # Name of the new attribute column
    max_field_length = 254    # Maximum length for a String field in Shapefile format

    for eca_file in sorted(eca_files):
        suffix = eca_file.replace("ECA_", "").replace(".shp", "")
        shp_path = os.path.join(final_polygon_dir, eca_file)

        upstream_value = upstream_map.get(suffix, '')

        # Open a fresh instance (not linked to the project layer registry)
        layer = QgsVectorLayer(shp_path, suffix, "ogr")
        if not layer.isValid():
            print(f"  Warning: Could not load {shp_path}. Skipping.")
            continue

        provider = layer.dataProvider()

        # ---- (a) Add field if it doesn't exist yet ----
        existing_fields = [f.name() for f in provider.fields()]
        if field_name not in existing_fields:
            if not (provider.capabilities() & QgsVectorDataProvider.AddAttributes):
                print(f"  Warning: Provider for {eca_file} does not support AddAttributes. Skipping.")
                continue
            ok = provider.addAttributes([QgsField(field_name, QVariant.String, len=max_field_length)])
            if not ok:
                print(f"  Warning: Failed to add field to {eca_file}. Skipping.")
                continue
            layer.updateFields()
            print(f"  Field '{field_name}' created in {eca_file}.")
        else:
            print(f"  Field '{field_name}' already exists in {eca_file}. Updating value.")

        field_index = layer.fields().indexFromName(field_name)

        # ---- (b) Build attribute change map {fid: {field_index: value}} ----
        attr_map = {}
        for feature in layer.getFeatures():
            attr_map[feature.id()] = {field_index: upstream_value}

        # ---- (c) Write directly via provider ----
        if not (provider.capabilities() & QgsVectorDataProvider.ChangeAttributeValues):
            print(f"  Warning: Provider for {eca_file} does not support ChangeAttributeValues. Skipping.")
            continue

        success = provider.changeAttributeValues(attr_map)
        if success:
            if upstream_value:
                print(f"  ECA_{suffix}: upstream = '{upstream_value}'")
            else:
                print(f"  ECA_{suffix}: no upstream basins (field written empty).")
        else:
            print(f"  Warning: Could not write values to {eca_file}.")

        # Reload the layer in the QGIS project so the new field is visible
        project = QgsProject.instance()
        # Remove old instance of this layer if already loaded
        layers_in_project = project.mapLayersByName(f"ECA_{suffix}")
        for old_layer in layers_in_project:
            project.removeMapLayer(old_layer.id())
        # Add updated layer
        updated_layer = QgsVectorLayer(shp_path, f"ECA_{suffix}", "ogr")
        if updated_layer.isValid():
            project.addMapLayer(updated_layer)

    # ------------------------------------------------------------------
    # Move the "Collected Points" layer to the top of the layer panel
    # ------------------------------------------------------------------
    root = QgsProject.instance().layerTreeRoot()

    # Find the tree node that corresponds to the Collected Points layer
    collected_node = None
    for node in root.findLayers():
        if node.layer() and node.layer().name() == "Collected Points":
            collected_node = node
            break

    if collected_node:
        # Clone the node, insert at position 0 (top), then remove the original
        cloned_node = collected_node.clone()
        root.insertChildNode(0, cloned_node)
        root.removeChildNode(collected_node)
        print("  'Collected Points' layer moved to the top of the layer panel.")
    else:
        print("  Warning: 'Collected Points' layer not found in the project to reorder.")

    print("Part 5 successfully completed!")


# ==================================================
# Execute all parts
process_basin_delimitation()
calculate_zonal_statistics()
process_basin_difference()
generate_dependency_chains()
add_upstream_attribute()

print("Processing completed successfully! All parts have been executed.")