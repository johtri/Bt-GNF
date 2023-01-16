# Create Bring Your Own Ingest (BYOI) for Paragon Insights
# Example for IOS-XR Model-Driven Telemetry (MDT)

The goal of this work is to extend multi-vendor environment in Paragon Insights and Paragon Pathfinder. Following goals can be achieved:
  - configure IOS-XR to send data into a Kafka bus
  - connect to the kafka bus from Paragon Insights and read "interesting" counters
  - create playbooks and rules acting on that data, draw charts etc.
  - make Pathfinder aware of the SR-TE LSP statistics from IOS-XR devices

### Workflow

 ![Workflow](png/workflow.png)

### Pathfinder Resulting View for SR-TE LSPs

 ![Pathfinder](png/pathfinder-view.png)

### Insights Chart View
 ![Insights](png/insights-view.png)

## Configuration
### Adding IOS-XR config

 Below example creates IOS-XR configuration for sending three sensor-group streams to a *telegraf* collector on 11.254.254.254:57000
 ```cisco
telemetry model-driven
 destination-group DG1
  address-family ipv4 11.254.254.254 port 57000
   encoding self-describing-gpb
   protocol grpc no-tls
  !
 !
 sensor-group cpu
  sensor-path Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring/cpu-utilization
 !
 sensor-group sg1
  sensor-path openconfig-interfaces:interfaces/interface
 !
 sensor-group sg2
  sensor-path Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters
 !
 sensor-group sr-te
  sensor-path Cisco-IOS-XR-infra-xtc-agent-oper:xtc/policy-forwardings/policy-forwarding
 !
 subscription telegraf
  sensor-group-id cpu sample-interval 60000
  sensor-group-id sg2 sample-interval 60000
  sensor-group-id sr-te sample-interval 60000
  destination-id DG1
 !
!
```

### Configuring Telegraf and Kafka on a custom compute resource

In this example, I am using a host with docker and docker-compose to run containers required for *kafka* (message bus) and *telegraf* (MDT collector). Upon receiving MDT streams, telegraf will send them in a certain format to kafka bus. Later, we will read from that kafka bus with Paragon Insights.

[Docker Compose for Telegraf and Kafka](kafka-external/docker-compose.yaml)

[Telegraf configuration file](kafka-external/telegraf.conf)

Docker containers can be then started with ``docker-compose up -d``

## Building BYOI

Log in to a Paragon Insights master node.

### create target directory, download files
```shell
root@paragon-master:/# mkdir /var/local/healthbot/byoi
root@paragon-master:/# cd /var/local/healthbot/byoi
root@paragon-master:/var/local/healthbot/byoi#
```

 Download following into that directory:
   - [BYOI Dockerfile](healthbot_mdtkafkajson_Dockerfile)
   - [BYOI python script](main.py)
   - [BYOI kubernetes manifest](healthbot_mdtkafkajson.yaml.j2)
   - [BYOI JFIT reconfigure script](jfit_reconfigure.sh)

### build docker images
```shell
docker build -t healthbot_mdtkafkajson:1.0.0 -f healthbot_mdtkafkajson_Dockerfile .
docker save healthbot_mdtkafkajson:1.0.0 -o healthbot_mdtkafkajson.tar.gz
export HB_EXTRA_MOUNT2=/var/local/healthbot/byoi/healthbot_mdtkafkajson.yaml.j2
export HB_EXTRA_MOUNT1=/var/local/healthbot/byoi/healthbot_mdtkafkajson.tar.gz
sudo -E ../healthbot load-plugin -i $HB_EXTRA_MOUNT1 -c $HB_EXTRA_MOUNT2
```

### Validate the plugin loaded successfully
```shell
root@paragon-master:/var/local/healthbot/byoi# ../healthbot list-plugins -l
PLUGIN                        IMAGE
mdtkafkajson                  healthbot_mdtkafkajson:1.0.0
```

### Configure plugin in Insights.
This part can be done via UI or via mgd. It's important to configure Kafka Broker as "brokers" parameter (IP:Port) and the "topics" 

```junos
set healthbot ingest byoi custom-plugin mdtkafkajson plugin-name MDT-Kafka-Json
set healthbot ingest byoi custom-plugin mdtkafkajson service-name mdtkafkajson
set healthbot ingest byoi custom-plugin mdtkafkajson parameters brokers value 11.254.254.254:9092
set healthbot ingest byoi custom-plugin mdtkafkajson parameters topics value telegraf
```

## Create Rules and Playbooks in Insights

An example of rules/playbook for CPU stats from MDT is [Rules for CPU Stats](insights.rules).

If you'd want to ingest SR-TE LSP stats which are propagated to pathfinder, this would require change of "controller" set of rules. [Rules for SR-TE LSP](insights.inject.ppf.rules).
**Be careful with those changes, default rules might change over time!** The goal of the modification is to add new sensor to "ctrl-label-switched-path" and "ctrl-label-switched-path-aggregation" which would use BYOI.

## Troubleshooting
### Check that BYOI is running:
```shell
root@paragon-master:/var/local/healthbot/byoi# kubectl get pod -A | grep mdt
healthbot              device-group-controller-0-mdtkafkajson-7d74dfc5b5-975jt           1/1     Running     0          160m
healthbot              device-group-controller-0-mdtkafkajson-terminus-6fb944c6fd945tf   1/1     Running     0          160m
```

### Check InfluxDB values
```shell
root@paragon-master:~# kubectl exec -n healthbot -it influxdb-192-168-122-20-66c769f8bd-brf6p -- influx --precision rfc3339 -database 'hb-default:controller:cisco9k' -execute 'select * from "controller.telemetry/ctrl-label-switched-path-aggregation" order by desc limit 10'
Defaulted container "influxdb" out of: influxdb, init (init), sync (init), sysctl (init), mmap (init)
name: controller.telemetry/ctrl-label-switched-path-aggregation
time                           __device_timestamp__ _instance_id _playbook_name color-id-left-con color-id-right-con elapsed-time lsp-stats-bps lsp-stats-name  lsp-stats-pps stats_received_count tandIngestTimestamp tandTimeOffset to-ip           total-delta-bytes total-delta-packets
----                           -------------------- ------------ -------------- ----------------- ------------------ ------------ ------------- --------------  ------------- -------------------- ------------------- -------------- -----           ----------------- -------------------
2022-07-25T14:58:21.50079507Z  1658761100000000000  ["ctrl1"]    controller                                          120          0             IOS-XR-1        0             2                    1658761101500794775 224ns          IOS-XR-1        0                 0
2022-07-25T14:57:21.416378804Z 1658761040000000000  ["ctrl1"]    controller                                          120          0             IOS-XR-inter-AS 0             2                    1658761041416378504 248ns          IOS-XR-inter-AS 0                 0
2022-07-25T14:56:21.349821758Z 1658760980000000000  ["ctrl1"]    controller                                          120          0             IOS-XR-1        0             2                    1658760981349821387 311ns          IOS-XR-1        0                 0
2022-07-25T14:55:22.278346011Z 1658760920000000000  ["ctrl1"]    controller                                          120          0             IOS-XR-inter-AS 0             2                    1658760922278345784 190ns          IOS-XR-inter-AS 0
```
