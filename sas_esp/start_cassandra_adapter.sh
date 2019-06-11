#!/bin/bash

$DFESP_HOME/bin/dfesp_cassandra_publisher -C url=dfESP://10.104.82.212:5994/eahub_shopco_orders_flow/cq1/src_order_summary_rt,keyspace=shopco,table=order_summary_order_id,node=10.104.87.133,selectstatement='select * from shopco.order_summary_order_id',port=19042,publishwithupsert=true,
