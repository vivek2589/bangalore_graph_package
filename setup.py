from setuptools import setup, find_packages

setup(
    name="bangalore-traffic-graph",
    version="0.2.0",
    description="Graph-based analysis and visualization of Bangalore traffic",
    author="Vivek Kumar",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.23.0",
        "networkx>=3.0",
        "osmnx>=1.3.0",
        "geopandas>=0.13.0",
        "shapely>=2.0.0",
        "fiona>=1.9.0",
        "pyproj>=3.5.0",
        "rtree>=1.0.0",
        "matplotlib>=3.7.0",
        "folium>=0.14.0",
        "branca>=0.6.0",
        "keplergl>=0.3.2",
        "click>=8.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "bangalore-traffic=bangalore_traffic_graph.cli:cli",
        ],
    },
)
