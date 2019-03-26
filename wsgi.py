from flask import Flask
from flask import flash, render_template, request, redirect, send_from_directory, jsonify
import MySQLdb
import os
from datetime import datetime, timedelta
from collections import OrderedDict
import json

application = Flask(__name__)
sensorMac = "b8:27:eb:54:2c:38"
config = {"height": 80, "floors": {4: {"ec:fa:bc:e:a6:95_1": "general", "ec:fa:bc:e:a6:95_2": "general", "ec:fa:bc:e:a6:95_3": "glass", "ec:fa:bc:e:a6:95_4": "paper"}}}
ra_config = {"floors": {4: {sensorMac: "general"}}}

@application.route("/")
def index():	
    templateData = get_template_data()
    return render_template('index.html', **templateData)


@application.route("/ra")
def ra():
    templateData = get_ra_template_data()
    return render_template('roomavailability.html', **templateData)


@application.route("/rs")
def rs():
    templateData = get_ra_template_data()
    return render_template('roomstatus.html', **templateData)


def from_date(time_scale):
    # WIP: while sensors are offline, we are using old data
    # datetime_now = datetime.now()
    datetime_now = datetime(2018, 9, 23, 10, 13, 13)
    if time_scale == "month":
        min_date = datetime_now - timedelta(days=30)
    elif time_scale == "week":
        min_date = datetime_now - timedelta(days=7)
    elif time_scale == "3_days":
        min_date = datetime_now - timedelta(days=3)
    else:
        min_date = datetime_now - timedelta(days=1)
    return min_date


@application.route('/ra/date/', methods=['POST'])
def get_ra_graph_data():
    time_scale = request.form.get("time_scale", "month")
    data = get_ra_template_data(from_date(time_scale))
    data = {"time_scale": json.dumps(data)}
    data = jsonify(data)
    return data


@application.route('/date/', methods=['POST'])
def get_graph_data():
    time_scale = request.form.get("time_scale", "month")
    data = get_template_data(from_date(time_scale))
    data = {"time_scale": json.dumps(data)}
    data = jsonify(data)
    return data


@application.route('/static/<path:path>')
def send_ota(path):
    return send_from_directory('static', path)


def get_ra_template_data(date=None):
    template_data = {'ra_config': ra_config}
    user = "remote-admin"
    passwd = "Some-pass!23"
    db_host = os.environ["MYSQL_SERVICE_HOST"]
    db_name = "room-availability"
    db = MySQLdb.connect(host=db_host, user=user, passwd=passwd, db=db_name)
    cur = db.cursor()
    if date is None:
        mysql_string = "SELECT * FROM `sensor_data` ORDER BY timestamp DESC LIMIT 20"
    else:
        mysql_string = "SELECT * FROM `sensor_data` WHERE timestamp > '{}' ORDER BY timestamp DESC".format(date)
    cur.execute(mysql_string)
    db_data = cur.fetchall()
    parsed_data = OrderedDict()
    for (id, mac_id, data, datetime_object) in db_data:
        date_time = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
        if date_time in parsed_data:
            parsed_data[date_time].update({mac_id: {"data": data}})
        else:
            parsed_data.update({ date_time: {mac_id: {"data": data}}})
    filtered_data = OrderedDict()
    for i in parsed_data:
       #if len(parsed_data[i]) == 1:
        filtered_data.update({i: parsed_data[i]})
    data_dictionary = OrderedDict(sorted(filtered_data.items()))
    if data_dictionary.get(next(reversed(data_dictionary))).get(sensorMac).get('data') == 1.0:
        template_data['status'] = "RoomIsBusy"
    else:
        template_data['status'] = "RoomIsFree"
    template_data['busyness_data'] = data_dictionary
    return template_data


def get_template_data(date=None):
    templateData = {'config': config}
    user = "remote-admin"
    passwd = "Some-pass!23"
    bin_height = config["height"]
    db_host = os.environ["MYSQL_SERVICE_HOST"]
    db_name = "smart-recycling-bins"
    db = MySQLdb.connect(host=db_host, user=user, passwd=passwd, db=db_name)
    cur = db.cursor()
#        cur.execute("""SELECT * FROM `sensor_data` WHERE timestamp < '2018-08-06 09:38:40' ORDER BY timestamp DESC LIMIT 200""")
    mac_ids = "('{}')".format("','".join(config['floors'][4].keys()))
    if date is None:
        mysql_string = "SELECT * FROM `sensor_data` WHERE `macid` IN {} ORDER BY timestamp DESC LIMIT 1000".format(mac_ids)
    else:
        mysql_string = "SELECT * FROM `sensor_data` WHERE timestamp > '{}' AND `macid` IN {} ORDER BY timestamp DESC".format(date, mac_ids)
    cur.execute(mysql_string)
    data = cur.fetchall()
    parsed_data = OrderedDict()
    fallback_values = {}
    for (id, mac_id, distance, datetime_object) in data:
        # if sensor reported value above 5 cm - record the value so we can fall back to last "good" one in case it's below 5
        if distance > 5:
            fallback_values[mac_id] = distance
        else:
            distance = fallback_values[mac_id]

        date_time = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
        # reserve the height with bin height from config
        trash_height = bin_height - distance
        if trash_height < 0:
            trash_height = 0
        if date_time in parsed_data:
            parsed_data[date_time].update({mac_id: {"trash_height": trash_height}})
        else:
            parsed_data.update({date_time: {mac_id: {"trash_height": trash_height}}})
    filtered_data = OrderedDict()
    for i in parsed_data:
        if len(parsed_data[i]) == 4:
            filtered_data.update({i: parsed_data[i]})

    templateData['distance_data'] = OrderedDict(sorted(filtered_data.items()))
    return templateData


@application.route("/db")
def db_records():
    user = "remote-admin"
    passwd = "Some-pass!23"
    db_host = os.environ["MYSQL_SERVICE_HOST"]
    db_name = "smart-recycling-bins"
    db = MySQLdb.connect(host=db_host, user=user, passwd=passwd, db=db_name)
    cur = db.cursor()
    mysql_string = "SELECT * FROM `sensor_data` ORDER BY timestamp DESC LIMIT 100"
    cur.execute(mysql_string)
    data = cur.fetchall()
    return render_template('db.html', data=data)


if __name__ == "__main__":
    application.run(debug=True)
