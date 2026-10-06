import osmnx as ox
import os

print("Downloading road network for Hyderabad...")
# Use a reasonable place or distance. Let's try "Hyderabad, Telangana, India"
# To avoid a massive timeout or memory issue, graph_from_place is usually good for a city.
G = ox.graph_from_place("Hyderabad, Telangana, India", network_type="drive")

output_dir = "data/raw/roads"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "hyderabad_road_network.graphml")

ox.save_graphml(G, filepath=output_path)

print(f"Graph saved to {output_path}")
print(f"Number of nodes: {len(G.nodes)}")
print(f"Number of edges: {len(G.edges)}")
