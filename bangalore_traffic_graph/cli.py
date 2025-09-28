import click
import os
from .core import (
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

@click.group()
def cli():
    """Bangalore Traffic Graph CLI"""
    pass

@cli.command()
@click.option("--csv", default="Banglore_traffic_Dataset.csv", help="Path to traffic dataset CSV")
@click.option("--output-dir", default="outputs", help="Directory to save outputs")
def run(csv, output_dir):
    """Run the full analysis pipeline"""
    os.makedirs(output_dir, exist_ok=True)

    print("✅ Loading dataset...")
    df = load_csv(csv)

    print("✅ Building OSM graph...")
    G = build_osm_graph("Bangalore, India", "drive")

    print("✅ Mapping traffic data...")
    G2 = map_traffic_by_name(G, df, name_col="road_intersection_name", vol_col="traffic_volume")

    print("✅ Computing centralities...")
    compute_centralities(G2)

    print("✅ Exporting Folium single-layer map...")
    export_folium_map(G2, os.path.join(output_dir, "bangalore_basic_map.html"))

    print("✅ Exporting Folium multi-layer map...")
    export_folium_map_with_time_layers(G2, df, os.path.join(output_dir, "bangalore_time_filtered_map.html"))

    print("✅ Exporting Kepler.gl map...")
    export_kepler_map(G2, df, os.path.join(output_dir, "bangalore_traffic_kepler.html"))

    print("✅ Exporting static Matplotlib heatmap...")
    export_matplotlib_heatmap(G2, os.path.join(output_dir, "bangalore_heatmap.png"))

    print("✅ Exporting edge list for GNN...")
    export_edge_list_for_gnn(G2, os.path.join(output_dir, "bangalore_graph_edges.csv"))

    print("\n🎉 Done! Check the outputs folder for results.")

if __name__ == "__main__":
    cli()
