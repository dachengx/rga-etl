# RGA-ETL

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/dachengx/rga-etl/main.svg)](https://results.pre-commit.ci/latest/github/dachengx/rga-etl/main)

Extract, transform, and load the data from an [SRS RGA200](https://www.thinksrs.com/products/rga.htm) to a MySQL database. Residual Gas Analyzer (RGA) is a mass spectrometer to measure the residual gas pressure in vacuum systems.

There is a huge caveat about serial communication settings of the RGA-200. Although the [SRS RGA manual](https://thinksrs.com/downloads/pdfs/manuals/RGAm.pdf) says that the number of stop bit of the RS-232 is 2, it actually should be 1. So in the settings of adpaters and programmable logic controller (PLC), be aware of this.

## PLC used

The PLC used in this repo is [BRX Do-more PLC BX-DM1E-10ER3-D](https://www.automationdirect.com/adc/shopping/catalog/programmable_controllers/brx_plcs_(stackable_micro_brick)/plcs_-a-_cpus/bx-dm1e-10er3-d). Using [Do-more Designer](https://www.automationdirect.com/support/software-downloads?itemcode=Do-more%20Designer), the PLC can be restarted (set to `Program` then `Run` mode) if the PLC mode switch position is at `Terminal`.

## Docker services

All commands, unless emphasized, are running in PowerShell.
After installation of docker from [Docker Website](https://www.docker.com/), run

```
mkdir C:\mysql-data
mkdir C:\grafana-data
```

Check the usable address by `Get-NetIPAddress | Format-Table InterfaceAlias,IPAddress` or (`ipconfig` in `cmd`), and set `MQTT_BROKER` in `docker-compose.tml` as the "Ethernet"'s ip address.

```
docker compose -f "$HOME\rga-etl\docker-compose.yml" up -d
```
or
```
docker compose -f %USERPROFILE%\rga-etl\docker-compose.yml up -d
```
in `cmd`.

Test mosquito sub/pub model

```
docker run -it --rm --network rga-etl_default eclipse-mosquitto mosquitto_sub -h mosquitto -p 1883 -t brx/control/do -v
docker run -it --rm --network rga-etl_default eclipse-mosquitto mosquitto_pub -h mosquitto -p 1883 -t brx/control/do -m 1
```

To connect to grafana, visit `http://localhost:3000/`. To connect to adminer, visit `http://localhost:8090/` with `"server"` set to `mysql`.

To check the log of `mqtt_bridge`, run `docker logs -f mqtt_bridge`.

To setup ES-246 Ethernet to serial adapter, it can be used in two modes:

1. The protocol type should be Telnet. After the adapter connects to the PC by Ethernet cable, the RGA is equivalently connected to a new serial port. This mode needs a [Windows installed software](https://www.brainboxes.com/faq/where-can-i-find-the-windows-drivers-for-my-ethernet-to-serial). The software installs the adapter's driver each time it connects to the PC.
2. The protocol type should be Raw TCP. After the adapter connects to the PC or PLC by Ethernet cable, set the protocol type by via [http://192.168.127.254/serialport1.html](http://192.168.127.254/serialport1.html). Then send and receive data via TCP sockets.

## srsinst.rga

The repo is based on the python wrapped interface for RGA communication. The RGA controlled directly by PC is built on top of it. It is also a good reference of data handling even for PC-PLC setup. Reference: [srsinst.rga](https://github.com/thinkSRS/srsinst.rga) (commit `d02992b68e527aabeea0a8e2f5486bdc4589f438`).

## RGA Operation Controlled Directly from PC

Related codes are in `rga_etl\pc`.

In a nominal operation, the RGA should be controled by a PLC, but directly connecting RGA with PC reduces the complexity during communication and helps understanding how RGA works.

After installing the package by `pip install -e ./ --user`, make sure that the `.local/bin` is in your `PATH` environmental variable by `export PATH="$HOME/.local/bin:$PATH"` if using a Linux, or set the `PATH` environmental variable correspondingly if using a Windows.

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

## RGA Operation Controlled by PC via PLC

Related codes are in `rga_etl\pc_plc`.
