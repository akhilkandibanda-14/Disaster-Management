import pandas as pd
import numpy as np
import os
import math

# Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# 1. Verify official gauges
print("==================================================")
print("1. VERIFY ALL OFFICIAL GAUGES")
print("==================================================")
coords_path = 'data/raw/indofloods/gauge_coordinates.csv'
df = pd.read_csv(coords_path)

total_gauges = len(df)
valid_coords = df[['Latitude', 'Longitude']].dropna()
duplicate_gauges = df.duplicated(subset=['GaugeID']).sum()
invalid_coords = total_gauges - len(valid_coords)

min_lat, max_lat = df['Latitude'].min(), df['Latitude'].max()
min_lon, max_lon = df['Longitude'].min(), df['Longitude'].max()

print(f"Total official gauges: {total_gauges}")
print(f"Valid coordinate count: {len(valid_coords)}")
print(f"Duplicate GaugeIDs: {duplicate_gauges}")
print(f"Invalid coordinates: {invalid_coords}")
print(f"Geographic bounding box:")
print(f"  Min Latitude: {min_lat:.4f}")
print(f"  Max Latitude: {max_lat:.4f}")
print(f"  Min Longitude: {min_lon:.4f}")
print(f"  Max Longitude: {max_lon:.4f}")


# 2 & 3. India Coverage (Using a grid over the bounding box)
print("\n==================================================")
print("2 & 3. COVERAGE STATISTICS & INDIA COVERAGE")
print("==================================================")
# Create a grid across India (roughly 8N to 37N, 68E to 97E)
india_lats = np.linspace(8.0, 37.0, 100)
india_lons = np.linspace(68.0, 97.0, 100)
grid_lats, grid_lons = np.meshgrid(india_lats, india_lons)
grid_lats = grid_lats.flatten()
grid_lons = grid_lons.flatten()

# Find nearest gauge for each point
gauge_lats = df['Latitude'].values
gauge_lons = df['Longitude'].values
min_distances = []

for lat, lon in zip(grid_lats, grid_lons):
    dist = haversine(lat, lon, gauge_lats, gauge_lons)
    min_distances.append(np.min(dist))

min_distances = np.array(min_distances)

print(f"Sampled Grid Points over India: {len(min_distances)}")
print(f"  Min distance: {np.min(min_distances):.2f} km")
print(f"  Max distance: {np.max(min_distances):.2f} km")
print(f"  Mean distance: {np.mean(min_distances):.2f} km")
print(f"  Median distance: {np.median(min_distances):.2f} km")
print(f"  25th percentile: {np.percentile(min_distances, 25):.2f} km")
print(f"  75th percentile: {np.percentile(min_distances, 75):.2f} km")

print("\nCoverage estimates (Grid points):")
for t in [10, 25, 50, 75, 100]:
    count = np.sum(min_distances <= t)
    pct = count / len(min_distances) * 100
    print(f"  Within {t} km: {count} ({pct:.2f}%)")

print("\nEstimated India coverage (within 50 km): {:.2f}%".format(np.sum(min_distances <= 50) / len(min_distances) * 100))

# 4. Telangana Coverage
print("\n==================================================")
print("4. TELANGANA COVERAGE")
print("==================================================")
# Rough bounding box for Telangana: 15.8N to 19.9N, 77.2E to 81.3E
ts_mask = (df['Latitude'] >= 15.8) & (df['Latitude'] <= 19.9) & (df['Longitude'] >= 77.2) & (df['Longitude'] <= 81.3)
ts_gauges = df[ts_mask]
print(f"Number of INDOFLOODS gauges in/near Telangana: {len(ts_gauges)}")

ts_grid_mask = (grid_lats >= 15.8) & (grid_lats <= 19.9) & (grid_lons >= 77.2) & (grid_lons <= 81.3)
ts_distances = min_distances[ts_grid_mask]
if len(ts_distances) > 0:
    ts_cov_50 = np.sum(ts_distances <= 50) / len(ts_distances) * 100
    print(f"Approximate Telangana area coverage (within 50 km): {ts_cov_50:.2f}%")

# 5. Hyderabad Test
print("\n==================================================")
print("5. HYDERABAD TEST")
print("==================================================")
hyd_lat = 17.3850
hyd_lon = 78.4867
hyd_dist = haversine(hyd_lat, hyd_lon, gauge_lats, gauge_lons)
min_hyd_idx = np.argmin(hyd_dist)
min_hyd_dist = hyd_dist[min_hyd_idx]
hyd_gauge = df.iloc[min_hyd_idx]

print(f"GaugeID: {hyd_gauge['GaugeID']}")
print(f"Gauge latitude: {hyd_gauge['Latitude']}")
print(f"Gauge longitude: {hyd_gauge['Longitude']}")
print(f"Distance km: {min_hyd_dist:.2f}")
print(f"Within 50 km: {'YES' if min_hyd_dist <= 50.0 else 'NO'}")

# 6. Catchment boundary availability
print("\n==================================================")
print("6. CATCHMENT BOUNDARIES")
print("==================================================")
raw_dir = 'data/raw/indofloods'
has_boundaries = any(f.endswith('.shp') or f.endswith('.geojson') or f.endswith('.gpkg') for f in os.listdir(raw_dir))
print(f"Catchment boundaries available in {raw_dir}: {'YES' if has_boundaries else 'NO'}")

# Investigate Catchment limitations via metadata
meta_path = 'data/raw/indofloods/metadata_indofloods.csv'
if os.path.exists(meta_path):
    meta = pd.read_csv(meta_path)
    basins = meta['Basin'].unique() if 'Basin' in meta.columns else []
    print(f"\nRepresented River Basins: {len(basins)} basins")
    print(basins[:5], "..." if len(basins) > 5 else "")
