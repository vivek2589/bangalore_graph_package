import pandas as pd
import networkx as nx
import re
from difflib import get_close_matches
from typing import Optional, Dict, Any

def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = str(name).lower().strip()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = name.replace(" rd", " road").replace(" st", " street")
    name = name.replace(" blvd", " boulevard").replace(" ave", " avenue")
    name = name.replace("mg ", "m g ")
    return name

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("/", "_")
    )
    return df

def build_osm_graph(place_name: str = "Bangalore, India", network_type: str = "drive") -> nx.Graph:
    import osmnx as ox
    G = ox.graph_from_place(place_name, network_type=network_type)
    G_simple = nx.Graph(G)
    largest_cc = max(nx.connected_components(G_simple), key=len)
    return G_simple.subgraph(largest_cc).copy()
def map_traffic_by_name(
    G: nx.Graph,
    df: pd.DataFrame,
    name_col: str = "road_intersection_name",
    vol_col: str = "traffic_volume",
    agg: str = "mean",
    verbose: bool = False
) -> nx.Graph:
    """
    Map traffic data from dataset to OSMnx graph edges using road/intersection names.
    Includes alias dictionary and fuzzy matching for Bangalore roads.
    """

    # --- Alias dictionary for Bangalore roads ---
    ROAD_ALIASES = {
        "mg rd": "mg road",
        "m g rd": "mg road",
        "m g road": "mg road",
        "outer ring rd": "outer ring road",
        "orr": "outer ring road",
        "bellary rd": "ballari road",
        "blr rd": "ballari road",
        "hosur rd": "hosur road",
        "bannerghatta rd": "bannerghatta road",
        "old madras rd": "old madras road",
        "airport rd": "airport road",
    }

    if name_col not in df.columns:
        raise KeyError(f"Missing column: {name_col}")
    if vol_col not in df.columns:
        raise KeyError(f"Missing column: {vol_col}")

    # Normalize dataset names
    def normalize_and_alias(name: str) -> str:
        n = normalize_name(name)
        return ROAD_ALIASES.get(n, n)

    df["_norm_name"] = df[name_col].apply(normalize_and_alias)

    # Aggregate metrics
    agg_func = {vol_col: agg}
    for col in ["average_speed", "congestion_level"]:
        if col in df.columns:
            agg_func[col] = agg

    traffic_map = df.groupby("_norm_name").agg(agg_func).to_dict(orient="index")

    unmatched = 0
    for u, v, data in G.edges(data=True):
        # Try name, ref, or highway as identifier
        road_name = data.get("name") or data.get("ref") or data.get("highway")
        if isinstance(road_name, list):
            road_name = road_name[0] if road_name else None
        norm_road = normalize_and_alias(road_name)

        if norm_road in traffic_map:
            metrics = traffic_map[norm_road]
        else:
            candidates = get_close_matches(norm_road, traffic_map.keys(), n=1, cutoff=0.85)
            metrics = (
                traffic_map[candidates[0]]
                if candidates
                else {vol_col: 0.0, "average_speed": 0.0, "congestion_level": 0.0}
            )
            if verbose and road_name and not candidates:
                unmatched += 1
                if unmatched <= 20:  # limit logs
                    print("⚠️ Unmatched OSM road:", road_name, "→ normalized:", norm_road)

        # Assign metrics to edge
        for col, val in metrics.items():
            data[col] = float(val)

    if verbose:
        vals = [d.get(vol_col, 0) for _, _, d in G.edges(data=True)]
        print(
            f"✅ Traffic mapping complete: {sum(v>0 for v in vals)} edges with data "
            f"out of {len(vals)} total."
        )

    return G

def compute_centralities(G: nx.Graph, k: Optional[int] = None) -> Dict[str, Dict[Any, float]]:
    num_nodes = G.number_of_nodes()
    k_param = k if k is not None else min(500, num_nodes)
    bet = nx.betweenness_centrality(G, k=k_param) if k_param < num_nodes else nx.betweenness_centrality(G)
    deg = nx.degree_centrality(G)
    nx.set_node_attributes(G, bet, "betweenness")
    nx.set_node_attributes(G, deg, "degree_centrality")
    return {"betweenness": bet, "degree_centrality": deg}

def export_edge_list_for_gnn(G: nx.Graph, out_csv: str,
                             vol_col: str = "traffic_volume",
                             speed_col: str = "average_speed",
                             cong_col: str = "congestion_level"):
    """
    Export edge list for Graph Neural Network training.
    Each row = (u, v, traffic_volume, average_speed, congestion_level)
    """
    rows = []
    for u, v, data in G.edges(data=True):
        rows.append({
            "u": u,
            "v": v,
            vol_col: data.get(vol_col, 0.0),
            speed_col: data.get(speed_col, 0.0),
            cong_col: data.get(cong_col, 0.0)
        })

    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"✅ Edge list for GNN exported: {out_csv}")
    return out_csv


import matplotlib.pyplot as plt

def export_matplotlib_heatmap(G: nx.Graph, out_png: str,
                              vol_col: str = "traffic_volume"):
    """
    Export a simple heatmap of traffic volume on edges using matplotlib.
    """
    import geopandas as gpd
    from shapely.geometry import LineString

    edges = []
    for u, v, data in G.edges(data=True):
        if "geometry" in data:
            geom = data["geometry"]
        else:
            geom = LineString([(G.nodes[u]["x"], G.nodes[u]["y"]),
                               (G.nodes[v]["x"], G.nodes[v]["y"])])
        edges.append({
            "u": u,
            "v": v,
            vol_col: data.get(vol_col, 0.0),
            "geometry": geom
        })

    gdf = gpd.GeoDataFrame(edges, crs="EPSG:4326")

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, column=vol_col, cmap="Reds",
             linewidth=1, legend=True,
             legend_kwds={"label": "Traffic Volume"})
    plt.title("Bangalore Traffic Heatmap")
    plt.savefig(out_png, dpi=150)
    plt.close()

    print(f"✅ Heatmap exported: {out_png}")
    return out_png

def export_folium_map(G: nx.Graph, out_html: str,
                      weight_attr: str = "traffic_volume"):
    """
    Export a simple Folium map with traffic volume styled on edges.
    """
    import folium
    import osmnx as ox

    # Convert graph to GeoDataFrame
    edges_gdf = ox.graph_to_gdfs(G, nodes=False, edges=True)

    # Base map centered on Bangalore
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=12, tiles="cartodbpositron")

    # Add edges colored by traffic volume
    for _, row in edges_gdf.iterrows():
        geom = row

def export_folium_map_with_time_layers(G: nx.Graph, df: pd.DataFrame, out_html: str,
                                       time_col: str = "date",
                                       vol_col: str = "traffic_volume"):
    """
    Export Folium map with separate layers for weekday vs weekend traffic.
    """
    import folium
    import osmnx as ox
    import pandas as pd

    if time_col not in df.columns:
        raise KeyError(f"Missing time column: {time_col}")

    # Parse date to datetime
    df["_date"] = pd.to_datetime(df[time_col], errors="coerce")
    df["_is_weekend"] = df["_date"].dt.dayofweek >= 5

    weekday_df = df[~df["_is_weekend"]]
    weekend_df = df[df["_is_weekend"]]

    # Base map
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=12, tiles="cartodbpositron")

    # Function to add a traffic layer
    def add_layer(sub_df, layer_name, color):
        sub_map = G.copy()
        sub_map = map_traffic_by_name(sub_map, sub_df,
                                      name_col="road_intersection_name",
                                      vol_col=vol_col)
        edges_gdf = ox.graph_to_gdfs(sub_map, nodes=False, edges=True)
        fg = folium.FeatureGroup(name=layer_name)
        for _, row in edges_gdf.iterrows():
            geom = row["geometry"]
            vol = row.get(vol_col, 0.0)
            folium.PolyLine(
                locations=[(y, x) for x, y in geom.coords],
                color=color,
                weight=2,
                opacity=0.7,
                tooltip=f"{layer_name} | {vol_col}: {vol}"
            ).add_to(fg)
        fg.add_to(m)

    # Add weekday and weekend layers
    add_layer(weekday_df, "Weekday Traffic", "red")
    add_layer(weekend_df, "Weekend Traffic", "blue")

    folium.LayerControl().add_to(m)
    m.save(out_html)
    print(f"✅ Multi-layer Folium map exported: {out_html}")
    return out_html

def export_kepler_map(G: nx.Graph, df: pd.DataFrame, out_html: str,
                      vol_col="traffic_volume", name_col="road_intersection_name"):
    from keplergl import KeplerGl
    import geopandas as gpd
    from shapely.geometry import LineString

    edges = []
    for u, v, data in G.edges(data=True):
        if "geometry" in data:
            geom = data["geometry"]
        else:
            geom = LineString([(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])])
        row = {"u": u, "v": v, "geometry": geom}
        row[vol_col] = data.get(vol_col, 0.0)
        for col in ["average_speed", "congestion_level"]:
            if col in data:
                row[col] = data[col]
        edges.append(row)

    edges_gdf = gpd.GeoDataFrame(edges, crs="EPSG:4326")

    map_ = KeplerGl(height=900)
    map_.add_data(data=edges_gdf, name="Bangalore Traffic")

    # ✅ Ensure html is string
    html = map_._repr_html_()
    if isinstance(html, bytes):
        html = html.decode("utf-8")

    # Inject fullscreen CSS
    html = html.replace(
        "<body>",
        "<body style='margin:0;padding:0;overflow:hidden;'>"
        "<div style='position:fixed;top:0;left:0;width:100%;height:100%;'>"
    )
    html = html.replace("</body>", "</div></body>")

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Kepler.gl map exported: {out_html}")
    return out_html


