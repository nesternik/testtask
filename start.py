import json

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import redis

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:password123@localhost:5432/cars_api"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

redis_instance = redis.Redis(host='localhost', port=6379)


class CarsModel(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String())
    full_name = db.Column(db.String())
    plate_number = db.Column(db.String())

    def __init__(self, model, full_name, plate_number):
        self.model = model
        self.full_name = full_name
        self.plate_number = plate_number

    def __repr__(self):
        return f"<Vehicle {self.id} {self.model} {self.full_name} {self.plate_number}>"


VEHICLES = []

@app.route("/", methods=['GET'])
def hello():
    return "<p>Hello, vehicles!</p>"


@app.route('/ping/', methods=['GET'])
def ping():
    return '{"ping": "pong"}'


@app.route('/vehicles/', methods=['GET', 'POST'])
def handle_vehicles():
    if request.method == 'GET':
        target_plate_number = request.args.get('plate_number', '')
        nearby_radius = request.args.get('nearby_radius', '')
        lng = request.args.get('lng', '')
        lat = request.args.get('lat', '')

        if nearby_radius and lng and lat:
            nearby_radius = float(nearby_radius)
            lng = float(lng)
            lat = float(lat)
            found_vehicles = redis_instance.georadius('vehicles_positions', lng, lat, nearby_radius, 'km', 'WITHDIST', 'WITHCOORD')
            result = []
            for v in found_vehicles:
                vehicle_id = int(v[0])
                print(vehicle_id)
                vehicle = CarsModel.query.get_or_404(vehicle_id)
                result.append(str(vehicle) + ' ' + str(v[1]) + ' ' + str(v[2]))
            return json.dumps(result)
        elif target_plate_number:
            all_cars = CarsModel.query.filter_by(plate_number=target_plate_number)

        else:
            all_cars = CarsModel.query.all()
        results = [
            {
                'id': car.id,
                'model': car.model,
                'full_name': car.full_name,
                'plate_number': car.plate_number
            } for car in all_cars]
        return json.dumps(results)
    elif request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_car = CarsModel(model=data['model'], full_name=data['full_name'], plate_number=data.get('plate_number'))
            db.session.add(new_car)
            db.session.commit()
            return {"message": f"car {new_car.full_name} has been created successfully."}
        else:
            return {"error": "The request payload is not in JSON format"}
    else:
        unsupported_method_error = f'Unsupported HTTP method {request.method}'
        raise ValueError(unsupported_method_error)


@app.route('/vehicles/<vehicle_id>', methods=['GET'])
def get_vehicle_by_id(vehicle_id):
    if vehicle_id is not None:
        return json.dumps(str(CarsModel.query.get_or_404(vehicle_id)))


@app.route('/vehicles/<vehicle_id>/position', methods=['POST'])
def handle_position(vehicle_id):
    if request.is_json:
        position_data = request.get_json()
        lng = position_data.get('Lng')
        lat = position_data.get('Lat')
        redis_instance.geoadd('vehicles_positions', lng, lat, str(vehicle_id))
    return json.dumps({'result': 'Changed the position', 'vehicle_id': vehicle_id})
