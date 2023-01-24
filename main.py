#!/usr/bin/python3

from kafka import KafkaConsumer
from requests.exceptions import HTTPError
import requests
import json
import time
import os


tand_host = os.environ.get('TAND_HOST', 'localhost') + ".healthbot"
tand_port = os.environ.get('TAND_PORT', '3000')

# read device, plugin, rule related attributes from config json
with open('/etc/byoi/config.json', 'r') as f:
    config_json = json.load(f)

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
        database = device_item["healthbot-storage"]['database']

        # iterate each measurement
        for measurement_item in device_item['sensor']:
              measurement = measurement_item["measurement"]

              telemetry_msg =  msg.value
              telemetry_msg_json = json.loads(telemetry_msg)

              if "updates" in telemetry_msg_json:
                  content_updates = telemetry_msg_json["updates"]
                  # print(content_updates)
                  for content_updates_individual in content_updates:
                      # print(content_updates_individual)
                      # print(content_updates_individual["Path"])
                      content_source = telemetry_msg_json["source"]
                      # print(content_source)
                      name = content_updates_individual["Path"]
                      # print(name)
                      name1 = name.split('[')[1].split(']')[0].split('=')
                      # print(name1)
                      # print(content_updates_individual["values"])
                      content_fields1 = content_updates_individual["values"]
                      # print (content_fields1)
                      content_fields2 = list(content_fields1.items())[0][1]
                      # print(content_fields2)
                      if content_source == device + ":" + "57400":
                          timestamp = int(time.time()) * 1000000000
                          if isinstance(content_fields2, dict):
                              #    print("Is dic")
                              # add KVs from values
                              metrics = ""
                              for key, value in content_fields2.items():
                                  # print(key,value)
                                  if str(value).isnumeric():
                                      metrics += ',' + str(key) + '=' + str(value)
                                  else:
                                      metrics += ',' + str(key) + '="' + str(value) + '"'

                              # add KVs from name
                              if name1[1].isnumeric():
                                  metrics += ',' + name1[0] + '=' + name1[1]
                              else:
                                  metrics += ',' + name1[0] + '="' + name1[1] + '"'

                              print(metrics[1:])
                              url = 'http://{}:{}/write?db={}'.format(tand_host, tand_port, database)
                              # The line protocol, or the post body will contain a string in the format of:
                              data = '{} {} {}'.format(measurement, metrics[1:], timestamp)
                              x = requests.post(url, data=data)

                          else:
                              # print("Is Str")
                              metrics = ""
                              # add KVs from values
                              for key, value in content_fields1.items():
                                  # print(key)
                                  key_accurate = key.rpartition("/")[-1]
                                  # print(key_accurate)
                                  # print(key,value)
                                  if str(value).isnumeric():
                                      metrics += ',' + str(key_accurate) + '=' + str(value)
                                  else:
                                      metrics += ',' + str(key_accurate) + '="' + str(value) + '"'

                              # add KVs from name
                              if name1[1].isnumeric():
                                  metrics += ',' + name1[0] + '=' + name1[1]
                              else:
                                  metrics += ',' + name1[0] + '="' + name1[1] + '"'

                              print(metrics[1:])
                              url = 'http://{}:{}/write?db={}'.format(tand_host, tand_port, database)
                              # The line protocol, or the post body will contain a string in the format of:
                              data = '{} {} {}'.format(measurement, metrics[1:], timestamp)
                              x = requests.post(url, data=data)

    time.sleep(10)
  except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
  except Exception as err:
        print(f'Other error occurred: {err}')
