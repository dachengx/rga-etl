FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY rga_etl/ ./rga_etl/

RUN pip install --no-cache-dir .

EXPOSE 8080

STOPSIGNAL SIGINT

CMD ["python", "-m", "rga_etl.pc_plc.mqtt_bridge"]
