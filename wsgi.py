from flask import Flask
from flask import flash, render_template, request, redirect, send_from_directory, jsonify
import MySQLdb
import os
from datetime import datetime, timedelta
from collections import OrderedDict
import json

application = Flask(__name__)
config = { "floors": {4: { "ec:fa:bc:e:a6:95_1": "general" , "ec:fa:bc:e:a6:95_2": "general", "ec:fa:bc:e:a6:95_3": "glass", "ec:fa:bc:e:a6:95_4": "paper" }}}
ra_config = { "floors": {4: { "b8:27:eb:54:2c:38_1": "general" }}}

@application.route("/")
def index():	
    templateData = get_template_data()
    return render_template('index.html', **templateData)

@application.route("/ra")
def ra_index():
    templateData = get_ra_template_data()
    return render_template('ra_index.html', **templateData)

@application.route('/date/', methods=['POST'])
def get_graph_data():
    time_scale = request.form.get("time_scale", "month")
    if time_scale == "month":
        min_date = datetime.now() - timedelta(days=48)
    elif time_scale == "week":
        min_date = datetime.now() - timedelta(days=25)
    elif time_scale == "3_days":
        min_date = datetime.now() - timedelta(days=21)
    else:
        min_date = datetime.now() - timedelta(days=19)
    data = get_template_data(min_date)
    data = {"time_scale": json.dumps(data)}
    data = jsonify(data)
    return data

@application.route('/static/<path:path>')
def send_ota(path):
    return send_from_directory('static', path)

def get_ra_template_data(date=None):
    templateData = {}
    templateData['ra_config'] = ra_config
    user = "remote-admin"
    passwd = "Some-pass!23"
    dbhost = os.environ["MYSQL_SERVICE_HOST"]
    dbname = "room-availability"
    db = MySQLdb.connect(host=dbhost, user=user, passwd=passwd, db=dbname)
    cur = db.cursor()
#        cur.execute("""SELECT * FROM `sensor_data` WHERE timestamp < '2018-08-06 09:38:40' ORDER BY timestamp DESC LIMIT 200""")
    if date is None:
        mysql_string = "SELECT * FROM `sensor_data` ORDER BY timestamp DESC LIMIT 200"
    else:
        mysql_string = "SELECT * FROM `sensor_data` WHERE timestamp > '{}' ORDER BY timestamp DESC".format(date)
    cur.execute(mysql_string)
    dbdata = cur.fetchall()
    parsed_data = OrderedDict()
    for (id, mac_id, data, datetime_object) in dbdata:
        date_time = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
        print date_time
        if date_time in parsed_data:
            parsed_data[date_time].update({ mac_id: { "data": data }})
        else:
            parsed_data.update({ date_time: { mac_id: { "data": data }}})
        print parsed_data[date_time]
    filtered_data = OrderedDict()
    for i in parsed_data:
        if len(parsed_data[i]) == 4:
            filtered_data.update({i: parsed_data[i]})
    templateData['busyness_data'] = OrderedDict(sorted(filtered_data.items()))
    return templateData

def get_template_data(date=None):
    templateData = {}
    templateData['config'] = config
    user = "remote-admin"
    passwd = "Some-pass!23"
    dbhost = os.environ["MYSQL_SERVICE_HOST"]
    dbname = "smart-recycling-bins"
    db = MySQLdb.connect(host=dbhost, user=user, passwd=passwd, db=dbname)        
    cur = db.cursor()
#        cur.execute("""SELECT * FROM `sensor_data` WHERE timestamp < '2018-08-06 09:38:40' ORDER BY timestamp DESC LIMIT 200""")
    if date is None:
        mysql_string = "SELECT * FROM `sensor_data` ORDER BY timestamp DESC LIMIT 200"
    else:
        mysql_string = "SELECT * FROM `sensor_data` WHERE timestamp > '{}' ORDER BY timestamp DESC".format(date)
    cur.execute(mysql_string)
    data = cur.fetchall()
    parsed_data = OrderedDict()
    for (id, mac_id, distance, datetime_object) in data:
        date_time = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
        if date_time in parsed_data:
            parsed_data[date_time].update({ mac_id: { "distance": distance }})
        else:
            parsed_data.update({ date_time: { mac_id: { "distance": distance }}})
    filtered_data = OrderedDict()
    for i in parsed_data:
        if len(parsed_data[i]) == 4:
            filtered_data.update({i: parsed_data[i]})
    templateData['distance_data'] = OrderedDict(sorted(filtered_data.items()))
    return templateData
    
if __name__ == "__main__":
    application.run(debug=True)
