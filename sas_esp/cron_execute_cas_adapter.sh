#!/bin/bash

if [ ! -z ${ESPENV_PATH} ] ; then
   PATH=$ESPENV_PATH
else
   ESPENV_PATH=$PATH
fi
#
# set basic variables for ESP
#
DFESP_HOME="/opt/sas/viya/home/SASEventStreamProcessingEngine/current"
LD_LIBRARY_PATH="/opt/sas/viya/home/SASEventStreamProcessingEngine/current/lib:/opt/sas/viya/home/SASFoundation/sasexe":$LD_LIBRARY_PATH
PATH="/opt/sas/viya/home/SASEventStreamProcessingEngine/current/bin:/opt/sas/viya/home/SASEventStreamProcessingEngine/current/bin:/opt/sas/viya/home/SASEventStreamProcessingEngine/current/bin:/opt/sas/viya/home/SASEventStreamProcessingEngine/current/bin:/home/sas/anaconda3/envs/python34/bin:/home/sas/anaconda3/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/opt/sas/viya/home/SASEventStreamProcessingEngine/5.2/bin:/opt/sas/viya/home/SASEventStreamProcessingEngine/5.2/bin:/home/sas/.local/bin:/home/sas/bin":$PATH

export DFESP_HOME LD_LIBRARY_PATH PATH PYTHONPATH ESPENV_PATH

export DFESP_DATASTAX_JARS=/opt/cassandra-java-driver/latest/cassandra-driver-core-3.4.0.jar:/opt/cassandra-java-driver/latest/lib/slf4j-api-1.7.5.jar:/opt/cassandra-java-driver/latest/lib/slf4j-simple-1.7.25.jar:/opt/cassandra-java-driver/latest/lib/guava-19.0.jar:/opt/cassandra-java-driver/latest/lib/netty-all-4.1.9.Final.jar:/opt/cassandra-java-driver/latest/lib/metrics-core-3.2.2.jar

$DFESP_HOME/bin/dfesp_cassandra_publisher -C url=dfESP://10.104.82.212:5994/eahub_shopco_orders_flow/cq1/src_order_summary_rt,keyspace=shopco,table=order_summary_order_id,node=10.104.87.133,selectstatement='select * from shopco.order_summary_order_id',port=19042,publishwithupsert=true,

