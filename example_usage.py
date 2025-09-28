import os
from bangalore_traffic_graph.core import (
    load_csv,
    build_osm_graph,
    map_traffic_by_name,
    compute_centralities,
    export_folium_map,
    export_folium_map_with_time_layers,
    export_kepler_map,
    export_matplotlib_heatmap,
    export_edge_list_for_gnn,
)

def run_example():
    os.makedirs("outputs", exist_ok=True)

    print("Loading dataset...")
    df = load_csv("./input/Banglore_traffic_Dataset.csv")

    print("Building OSM graph for Bangalore...")
    G = build_osm_graph(place_name="Bangalore, India", network_type="drive")

    print("Mapping traffic data to edges...")
    G2 = map_traffic_by_name(G, df, name_col="road_intersection_name", vol_col="traffic_volume")

    print("Computing centralities...")
    compute_centralities(G2)

    print("Exporting Folium single-layer map...")
    export_folium_map(G2, "outputs/bangalore_basic_map.html", weight_attr="traffic_volume")

    print("Exporting Folium multi-layer map...")
    export_folium_map_with_time_layers(
        G2,
        df,
        "outputs/bangalore_time_filtered_map.html",
        time_col="date",
        vol_col="traffic_volume",
        name_col="road_intersection_name",
    )

    print("Exporting Kepler.gl map...")
    export_kepler_map(G2, df, "outputs/bangalore_traffic_kepler.html")

    print("Exporting static Matplotlib heatmap...")
    export_matplotlib_heatmap(G2, "outputs/bangalore_heatmap.png", vol_col="traffic_volume")

    print("Exporting edge list for GNN...")
    export_edge_list_for_gnn(G2, "outputs/bangalore_graph_edges.csv")

    print("\ Done! Check the outputs/ folder for results.")

if __name__ == "__main__":
    run_example()
