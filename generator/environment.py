"""
Environment generator for weather cells and airspace constraint zones.
Airspace zones use Shapely geometries serialized as WKT strings.
"""

from typing import List
import numpy as np
from shapely.geometry import Polygon, Point

from generator.schemas import (
    WeatherCellSchema,
    AirspaceZoneSchema,
    GeographyConfig,
    SizeConfig,
)


def generate_weather_cells(
    size_config: SizeConfig,
    geo_config: GeographyConfig,
    duration_hours: float,
    rng: np.random.Generator,
) -> List[WeatherCellSchema]:
    """Generates synthetic dynamic weather cells."""
    cells: List[WeatherCellSchema] = []

    for i in range(size_config.num_weather_cells):
        weather_id = f"WX-{i + 1:03d}"
        lat = float(rng.uniform(geo_config.lat_min, geo_config.lat_max))
        lon = float(rng.uniform(geo_config.lon_min, geo_config.lon_max))
        radius = float(round(rng.uniform(15.0, 80.0), 1))
        severity = float(round(rng.uniform(0.2, 0.95), 2))
        v_x = float(round(rng.uniform(-10.0, 10.0), 1))
        v_y = float(round(rng.uniform(-10.0, 10.0), 1))

        start_time = float(round(rng.uniform(0.0, max(0.5, duration_hours - 6.0)), 1))
        end_time = float(round(start_time + rng.uniform(4.0, 16.0), 1))

        cells.append(
            WeatherCellSchema(
                weather_id=weather_id,
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                radius_km=radius,
                severity=severity,
                velocity=(v_x, v_y),
                start_time=start_time,
                end_time=end_time,
            )
        )
    return cells


def generate_airspace_zones(
    size_config: SizeConfig,
    geo_config: GeographyConfig,
    duration_hours: float,
    rng: np.random.Generator,
) -> List[AirspaceZoneSchema]:
    """Generates synthetic restricted airspace zones using Shapely geometries."""
    zones: List[AirspaceZoneSchema] = []

    for i in range(size_config.num_airspace_zones):
        zone_id = f"ZONE-{i + 1:03d}"
        center_lat = float(rng.uniform(geo_config.lat_min + 0.5, geo_config.lat_max - 0.5))
        center_lon = float(rng.uniform(geo_config.lon_min + 0.5, geo_config.lon_max - 0.5))
        d_lat = float(rng.uniform(0.2, 0.8))
        d_lon = float(rng.uniform(0.2, 0.8))

        # Create a rectangular polygon for the restricted airspace zone
        poly = Polygon(
            [
                (center_lon - d_lon, center_lat - d_lat),
                (center_lon + d_lon, center_lat - d_lat),
                (center_lon + d_lon, center_lat + d_lat),
                (center_lon - d_lon, center_lat + d_lat),
                (center_lon - d_lon, center_lat - d_lat),
            ]
        )

        start_time = float(round(rng.uniform(0.0, max(0.5, duration_hours - 8.0)), 1))
        end_time = float(round(start_time + rng.uniform(6.0, 20.0), 1))
        restriction_level = float(round(rng.uniform(0.5, 1.0), 2))

        zones.append(
            AirspaceZoneSchema(
                zone_id=zone_id,
                geometry_wkt=poly.wkt,
                start_time=start_time,
                end_time=end_time,
                restriction_level=restriction_level,
            )
        )
    return zones


def is_point_in_airspace(lat: float, lon: float, zone: AirspaceZoneSchema, current_time: float) -> bool:
    """Checks if a given coordinate and time intersects a restricted airspace zone."""
    if not (zone.start_time <= current_time <= zone.end_time):
        return False

    from shapely.wkt import loads
    poly = loads(zone.geometry_wkt)
    point = Point(lon, lat)
    return bool(poly.contains(point))
