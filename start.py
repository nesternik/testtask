import json
from typing import Dict, Union, Tuple, List, Optional, Any

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from redis_storage import find_vehicles_in_nearby_radius, set_vehicle_position

POSTGRES_HOST = 'localhost'
POSTGRES_PORT = 5432
POSTGRES_USER = 'postgres'
POSTGRES_PASS = 'password123'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:password123@localhost:5432/cars_api"
db = SQLAlchemy(app)
migrate = Migrate(app, db)


VEHICLE_DICT = Dict[str, Union[str, int]]

class CarsModel(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String())
    full_name = db.Column(db.String())
    plate_number = db.Column(db.String())

    def __init__(self, model: str, full_name: str, plate_number: str) -> None:
        self.model = model
        self.full_name = full_name
        self.plate_number = plate_number

    def __repr__(self) -> str:
        return f"Vehicle {self.id} {self.model} {self.full_name} {self.plate_number}"

    def to_dict(self) -> VEHICLE_DICT:
        return {'id': self.id, 'model': self.model, 'full_name': self.full_name, 'plate_number': self.plate_number}


@app.route("/", methods=['GET'])
def hello():
    return "<p>Hello, vehicles!</p>"


@app.route('/ping/', methods=['GET'])
def ping() -> Dict[str, str]:
    return {"ping": "pong"}


@app.route('/vehicles/', methods=['GET', 'POST'])
def handle_vehicles() -> Tuple[Dict[str, Any], int]:
    if request.method == 'GET':
        target_plate_number = request.args.get('plate_number', '')
        nearby_radius = request.args.get('nearby_radius', '')
        lng = request.args.get('lng', '')
        lat = request.args.get('lat', '')

        # GET /vehicles/?nearby_radius=2000&lng=141.2341&lat=19.8761
        if nearby_radius and lng and lat:
            nearby_radius = float(nearby_radius)
            lng = float(lng)
            lat = float(lat)
            nearby_vehicles = find_vehicles_in_nearby_radius(lng=lng, lat=lat, nearby_radius=nearby_radius)
            result = []
            for vehicle_id, distance, coordinates in nearby_vehicles:
                vehicle = get_vehicle_by_id_from_db(vehicle_id=vehicle_id)
                result.append({'vehicle': vehicle.to_dict(), 'distance': distance, 'coordinates': coordinates})
            return {
                       'success': True,
                       'result': result
                   }, 200

        # GET /vehicles/?plate_number=111eee
        elif target_plate_number:
            found_vehicles = get_vehicles_filtered_by_plate_number(target_plate_number)
            return {
                       'success': True,
                       'vehicles': [v.to_dict() for v in found_vehicles]
                   }, 200

        # GET /vehicles/
        else:
            all_vehicles = get_all_vehicles()
            return {
                'success': True,
                'vehicles': [v.to_dict() for v in all_vehicles]
            }, 200
    # POST /vehicles/
    elif request.method == 'POST':
        if not request.is_json:
            return {
                       'success': False,
                       'error': 'The request payload is not in JSON format'
                   }, 406
        data = request.get_json()
        model = data.get('model')
        full_name = data.get('full_name')
        plate_number = data.get('plate_number')
        new_vehicle_id = add_new_vehicle_to_db(model=model, full_name=full_name, plate_number=plate_number)
        return {
                   'success': True,
                   'message': f'Vehicle with id {new_vehicle_id} has been created successfully'
               }, 200
    else:
        return {
                   'success': False,
                   'error': f'Unsupported HTTP method {request.method}'
               }, 405


@app.route('/vehicles/<int:vehicle_id>', methods=['GET'])
def get_vehicle_by_id(vehicle_id: int) -> Tuple[Dict[str, Any], int]:
    vehicle: Optional[CarsModel] = get_vehicle_by_id_from_db(vehicle_id=vehicle_id)
    if vehicle is not None:
        return {
                   'success': True,
                   'vehicle': vehicle.to_dict()
               }, 200
    else:
        return {
                   'success': False,
                   'error': f'Did not find vehicle with id {vehicle_id}'
               }, 404


@app.route('/vehicles/<int:vehicle_id>/position', methods=['POST'])
def handle_position(vehicle_id: int) -> Tuple[Dict[str, Any], int]:
    if request.is_json:
        position_data = request.get_json()
        lng = position_data.get('Lng')
        lat = position_data.get('Lat')
        result = set_vehicle_position(vehicle_id=vehicle_id, lng=lng, lat=lat)
        if result == 0:
            return {
                       'success': True,
                       'message': f'For vehicle {vehicle_id} position was changed successfully'
                   }, 200
        else:
            return {
                       'success': False,
                       'error': f'For vehicle {vehicle_id} result of changing position is: {result}'
                   }, 500
    else:
        return {
                   'success': False,
                   'error': 'only json is supported as input'
               }, 406


def add_new_vehicle_to_db(model: str, full_name: str, plate_number: str) -> int:
    new_car = CarsModel(model=model, full_name=full_name, plate_number=plate_number)
    db.session.add(new_car)
    db.session.commit()
    return new_car.id

def get_vehicles_filtered_by_plate_number(plate_number: str) -> List[CarsModel]:
    found_vehicles = CarsModel.query.filter_by(plate_number=plate_number)
    return found_vehicles

def get_all_vehicles():
    all_vehicles = CarsModel.query.all()
    return all_vehicles

def get_vehicle_by_id_from_db(vehicle_id: int) -> Optional[CarsModel]:
    vehicle = CarsModel.query.get(vehicle_id)
    return vehicle
