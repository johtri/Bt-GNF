#!/usr/bin/python3

from kafka import KafkaConsumer
from requests.exceptions import HTTPError
import requests
import json
import time
import os


tand_host = os.environ.get('TAND_HOST', 'localhost')
tand_port = os.environ.get('TAND_PORT', '3000')

# read device, plugin, rule related attributes from config json
with open('/etc/byoi/config.json', 'r') as f:
    config_json = json.load(f)


# take database ID from the first device
database = config_json['hbin']['inputs'][0]['plugin']['config']['device'][0]['healthbot-storage']['database']

#measurement = config_json['hbin']['inputs'][0]['plugin']['config']['device'][0]['sensor'][0]['measurement']
#device = config_json['hbin']['inputs'][0]['plugin']['config']['device'][0]['system-id']

# get the kafka brokers and topics
keyfield = []

for item in config_json['hbin']['inputs'][0]['plugin']['config']['kvs']:
       if item.get('key') == 'brokers':
             brokers = item.get('value')
       if item.get('key') == 'topics':
             topics = item.get('value')

while True:

  try:
    consumer = KafkaConsumer(topics, bootstrap_servers=[brokers])
    # iterate through kafka messages
    for msg in consumer:
      # iterate each device
      for device_item in config_json['hbin']['inputs'][0]['plugin']['config']['device']:
        device = device_item["system-id"]
        # iterate each measurement
        for measurement_item in device_item['sensor']:
              measurement = measurement_item["measurement"]

              telemetry_msg =  msg.value
              telemetry_msg_json = json.loads(telemetry_msg)

              # check if tags tag is in the json stream
              if "tags" in telemetry_msg_json:
                  content_sensor = telemetry_msg_json["name"]
                  content_fields = telemetry_msg_json["fields"]
                  content_tags = telemetry_msg_json["tags"]

                  # check if the device ID is the same as in this plugin instance
                  if content_tags.get('source') == device:
                      timestamp = int(time.time()) * 1000000000
                      metrics = ""
                      # add KVs from values
                      for key,value in content_fields.items():
                        #print(key,value)
                        if str(value).isnumeric():
                            metrics += ',' + str(key) + '=' + str(value)
                        else:
                            metrics += ',' + str(key) + '="' + str(value) + '"'

                      # add KVs from tags
                      for key,value in content_tags.items():
                        # skip some unnecessary keys
                        drop_keys = ("host", "subscription", "path", "source")
                        if str(key) not in drop_keys:
                           if str(value).isnumeric():
                              metrics += ',' + str(key) + '=' + str(value)
                           else:
                              metrics += ',' + str(key) + '="' + str(value) + '"'

                      # print(metrics[1:])
                      # form the right URL for TAND
                      url = 'http://{}:{}/write?db={}'.format(tand_host, tand_port, database)

                      # The line protocol, or the post body will contain a string in the format of:
                      data = '{} {} {}'.format(measurement, metrics[1:], timestamp)
                      x = requests.post(url, data=data)
                      #print('url: ' + url)
                      #print('data: ' + data)
                      #print('metrics: ' + metrics[1:])
                      #print('')
                      #print('HTTP status_code: ' + str(x.status_code))

    time.sleep(10)
  except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
  except Exception as err:
        print(f'Other error occurred: {err}')
