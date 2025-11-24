# RGA-ETL

Extract, transform, and load the data from an SRS RGA200 to a MySQL database.

## Docker services

All commands, unless emphasized, are running in Command Prompt (`cmd`).
After installation of docker from [https://www.docker.com/](Docker Website), run

```
mkdir C:\mysql-data
mkdir C:\grafana-data
```

```
docker compose -f %USERPROFILE%\rga-etl\docker-compose.yml up -d
```

Test mosquito sub/pub model

```
docker run -it --rm eclipse-mosquitto mosquitto_sub -h xxx.xxx.xxx.xxx -t brx/control/do -v
docker run -it --rm eclipse-mosquitto mosquitto_pub -h xxx.xxx.xxx.xxx -t brx/control/do -m 1
```

Replace the ip `xxx.xxx.xxx.xxx` to an available one.

## srsinst.rga

The repo is based on the python wrapped interface for RGA communication. Reference: [srsinst.rga](https://github.com/thinkSRS/srsinst.rga).

## RGA Measurement

After installing the package by `pip install -e ./ --user`, make sure that the `.local/bin` is in your `PATH` environmental variable by `export PATH="$HOME/.local/bin:$PATH"`.

These commands do different operation:

1. `rga_test` runs a self test of RGA connection and MySQL database integrity.
2. `rga_analog_scan` runs an anlog scan and save the result to database.
3. `rga_p_vs_t_scan` runs a pressure vs time scan of one or multiple masses and save the result to database.

Please check the usage of each command by `--help`, e.g. `rga_p_vs_t_scan --help`.

The settings of RGA can be defined in `.env`:

1. `RGA_MODEL` is the model of the RAG, e.g. `RGA200`. This is needed by only by database.
2. `RGA_SERIAL_NUMBER` is the serial number of RGA. This is needed by only by database.
3. `RGA_BAUD_RATE` is the baud rate of the communication of host and RGA via RS-232. This is needed by only by `srsinst.rga`.
4. `RGA_USB_SERIAL_DEVICE_IDENTIFIER` is the device identifier on the host machine. On macOS, it can be `/dev/tty.usbserial-FTEIZFXM`. This is needed by only by `srsinst.rga`.
5. `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DB` are the environmental variable needed by the MySQL database connection.
6. `RGA_INITIAL_MASS`, `RGA_FINAL_MASS`, `RGA_RESOLUTION`, and `RGA_SCAN_SPEED` are the environmental variable needed by the analog scan.
7. `RGA_MASSES`, `RGA_SCAN_TOTAL_TIME` and `RGA_SCAN_TIME_INTERVAL` are the environmental variable needed by the pressure vs time scan.
