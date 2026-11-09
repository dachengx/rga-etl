FROM python:3.11-slim

WORKDIR /app

# Only paho-mqtt is needed, not the full rga_etl dependencies
RUN pip install --no-cache-dir paho-mqtt==2.1.0

COPY rga_etl/__init__.py ./rga_etl/
COPY rga_etl/pc_plc/__init__.py rga_etl/pc_plc/monitor_recorder.py ./rga_etl/pc_plc/

STOPSIGNAL SIGINT

CMD ["python", "-u", "-m", "rga_etl.pc_plc.monitor_recorder"]
