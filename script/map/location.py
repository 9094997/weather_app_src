import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pyproj import Transformer, CRS
from shapely.geometry import Point, box
import geopandas as gpd
import requests
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from tqdm import tqdm

def download_world_data():
    """Download the world countries shapefile"""
    data_dir = Path("map_data")
    data_dir.mkdir(exist_ok=True)
    
    url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    zip_path = data_dir / "ne_110m_admin_0_countries.zip"
    
    print("Downloading world boundaries data...")
    response = requests.get(url)
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    
    # Unzip the file
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(data_dir)
    
    print("Data downloaded and extracted successfully")
    return data_dir / "ne_110m_admin_0_countries.shp"



def get_location_name(lat, lon, geolocator):
    """Get location name for given coordinates"""
    try:
        time.sleep(0.5)  # Rate limiting 
        location = geolocator.reverse((lat, lon), language='en')
        
        if location and location.raw.get('address'):
            address = location.raw['address']
            
            # Try to get the most relevant name
            name_components = [
                address.get('suburb'),
                address.get('city'),
                address.get('town'),
                address.get('village'),
                address.get('county'),
                address.get('state_district'),
                address.get('state')
            ]
            
            # Use the first non-None value
            return next((name for name in name_components if name), 'Unknown')
            
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Error getting location for {lat}, {lon}")
        return 'Unknown'
    
    return 'Unknown'


def generate_and_visualize_uk_ireland_grid():
    print("Starting grid generation...")
    
    # Initialize geolocator
    geolocator = Nominatim(user_agent="uk_ireland_grid_mapper")
    
    # Define the British National Grid CRS
    bng = CRS('EPSG:27700')
    wgs84 = CRS('EPSG:4326')
    
    # Create transformer objects
    to_wgs84 = Transformer.from_crs(bng, wgs84, always_xy=True)
    
    # Download and load UK and Ireland boundaries
    shapefile_path = download_world_data()
    print("Loading geographical data...")
    world = gpd.read_file(shapefile_path)
    uk_ireland = world[world['NAME'].isin(['United Kingdom', 'Ireland'])]
    uk_ireland = uk_ireland.to_crs(bng)
    
    # Get bounds in meters
    bounds = uk_ireland.total_bounds
    
    # Convert 8 miles to meters
    grid_size = 8 * 1609.34  # 1 mile = 1609.34 meters
    
    # Calculate number of cells in each direction
    x_cells = int(np.ceil((bounds[2] - bounds[0]) / grid_size))
    y_cells = int(np.ceil((bounds[3] - bounds[1]) / grid_size))
    
    grid_cells = []
    
    print(f"Generating grid: {x_cells} x {y_cells} cells")
    total_cells = x_cells * y_cells
    cells_processed = 0
    
    # Generate grid
    for i in range(x_cells):
        for j in range(y_cells):
            cells_processed += 1
            if cells_processed % 100 == 0:
                print(f"Progress: {cells_processed}/{total_cells} cells processed")
                
            # Calculate cell bounds
            x_min = bounds[0] + (i * grid_size)
            y_min = bounds[1] + (j * grid_size)
            center_x = x_min + (grid_size / 2)
            center_y = y_min + (grid_size / 2)
            
            # Create point and check if it intersects with UK/Ireland
            point = Point(center_x, center_y)
            
            if uk_ireland.geometry.contains(point).any():
                
                # Convert center point back to lat/lon
                lon, lat = to_wgs84.transform(center_x, center_y)
                ## IMPORTANT!!! we descide to not get the location name from geolocator as it can be time consuming, we will send the lat and lon to weather api and get the location name from the reposne.
                ##location_name = get_location_name(lat, lon, geolocator)
                
                ## if we want to add the location name to the json in the future then just add it below. 
                grid_cells.append({
                    'latitude': round(lat, 6),
                    'longitude': round(lon, 6)
                })
    
    # Save to JSON
    output = {
        'grid_size_miles': 8,
        'total_cells': len(grid_cells),
        'cells': grid_cells
    }
    
    print(f"Generated {len(grid_cells)} grid cells")
    
    with open('script/map/uk_location_list.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Visualization part
    print("Creating visualization...")
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 15))
    
    # Extract coordinates
    lats = [cell['latitude'] for cell in grid_cells]
    lons = [cell['longitude'] for cell in grid_cells]
    
    # Calculate grid dimensions
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Plot each grid cell
    for cell in grid_cells:
        lat = cell['latitude']
        lon = cell['longitude']
        
        # Convert to plot coordinates
        x = (lon - min_lon) / (max_lon - min_lon)
        y = (lat - min_lat) / (max_lat - min_lat)
        
        # Create rectangle
        rect = Rectangle((x-0.005, y-0.005), 0.01, 0.01, 
                        facecolor='forestgreen', 
                        edgecolor='white',
                        linewidth=0.5)
        ax.add_patch(rect)
    
    # Set plot limits
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)
    
    # Remove axes
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Add total count in top-right corner
    plt.text(0.98, 0.98, f'Total Squares: {len(grid_cells)}', 
             horizontalalignment='right',
             verticalalignment='top',
             transform=ax.transAxes,
             bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
             fontsize=10)
    
    # Add title
    plt.title('UK & Ireland: 8x8 Mile Grid', pad=20, fontsize=14)
    
    # Set background color
    ax.set_facecolor('lightgray')
    fig.patch.set_facecolor('white')
    
    # Add border around the plot
    for spine in ax.spines.values():
        spine.set_visible(True)
    
    # Save the plot
    plt.savefig('script/map/uk_ireland_grid_visualization.png', 
                dpi=300, 
                bbox_inches='tight',
                facecolor='white')
    plt.close()
    
    print("Completed! Files saved: uk_ireland_grid_8mile.json and uk_ireland_grid_visualization.png")

if __name__ == "__main__":
    # Run the combined function
    generate_and_visualize_uk_ireland_grid()
    
    