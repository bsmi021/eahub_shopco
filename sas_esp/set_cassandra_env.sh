#!/bin/bash
export DATASTAX_JARS=/opt/cassandra-java-driver/latest
export DFESP_DATASTAX_JARS=$DATASTAX_JARS/cassandra-driver-core-3.4.0.jar
export DFESP_DATASTAX_JARS=$DFESP_DATASTAX_JARS:$DATASTAX_JARS/lib/slf4j-api-1.7.5.jar
export DFESP_DATASTAX_JARS=$DFESP_DATASTAX_JARS:$DATASTAX_JARS/lib/slf4j-simple-1.7.25.jar
export DFESP_DATASTAX_JARS=$DFESP_DATASTAX_JARS:$DATASTAX_JARS/lib/guava-19.0.jar
export DFESP_DATASTAX_JARS=$DFESP_DATASTAX_JARS:$DATASTAX_JARS/lib/netty-all-4.1.9.Final.jar
export DFESP_DATASTAX_JARS=$DFESP_DATASTAX_JARS:$DATASTAX_JARS/lib/metrics-core-3.2.2.jar
