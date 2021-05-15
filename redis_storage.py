from typing import List, Tuple, Any

import redis


REDIS_HOST = 'localhost'
REDIS_PORT = 6379

redis_instance = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


def find_vehicles_in_nearby_radius(lng: float, lat: float, nearby_radius: float) -> List[Tuple[int, float, Tuple[float, float]]]:
    result: List[Tuple[int, float, Tuple[float, float]]] = []
    found_positioning_records = redis_instance.georadius(
        'vehicles_positions',
        lng,
        lat,
        nearby_radius,
        'km', 'WITHDIST', 'WITHCOORD')
    for record in found_positioning_records:
        vehicle_id = int(record[0])
        distance = float(record[1])
        lng, lat = record[2]
        lng = float(lng)
        lat = float(lat)
        result.append((vehicle_id, distance, (lng, lat)))
    return result


def set_vehicle_position(vehicle_id: int, lng: float, lat: float) -> Any:
    return redis_instance.geoadd('vehicles_positions', lng, lat, str(vehicle_id))
