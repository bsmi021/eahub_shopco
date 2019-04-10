echo "creating databases"
call docker exec eahub_shopco_catalog_service_1 python -m catalog.dbmigrate
call docker exec eahub_shopco_customers_service_1 python -m customers.dbmigrate
call docker exec eahub_shopco_warehouse_service_1 python -m warehouse.dbmigrate
call docker exec eahub_shopco_orders_service_1 python -m orders.dbmigrate

echo "creating queues"
call docker exec -it eahub_shopco_rabbit_1 rabbitmqadmin declare queue name=nifi_order_paid durable=true
call docker exec -it eahub_shopco_rabbit_1 rabbitmqadmin declare binding source="command_orders.events" destination_type="queue" destination="nifi_order_paid" routing_key="order_status_changed_to_paid"
