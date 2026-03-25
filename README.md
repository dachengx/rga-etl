# RGA-ETL

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/dachengx/rga-etl/main.svg)](https://results.pre-commit.ci/latest/github/dachengx/rga-etl/main)

Extract, transform, and load the data from an [SRS RGA200](https://www.thinksrs.com/products/rga.htm) to a MySQL database. Residual Gas Analyzer (RGA) is a mass spectrometer to measure the residual gas pressure in vacuum systems.

There is a huge caveat about serial communication settings of the RGA-200. Although the [SRS RGA manual](https://thinksrs.com/downloads/pdfs/manuals/RGAm.pdf) says that the number of stop bit of the RS-232 is 2, it actually should be 1. So in the settings of adapters and programmable logic controller (PLC), be aware of this.

## PLC used

The PLC used in this repo is [BRX Do-more PLC BX-DM1E-10ER3-D](https://www.automationdirect.com/adc/shopping/catalog/programmable_controllers/brx_plcs_(stackable_micro_brick)/plcs_-a-_cpus/bx-dm1e-10er3-d). Using [Do-more Designer](https://www.automationdirect.com/support/software-downloads?itemcode=Do-more%20Designer), the PLC can be restarted (set to `Program` then `Run` mode) if the PLC mode switch position is at `Terminal`.

## Docker services

All commands, unless emphasized, are running in PowerShell.
After installation of docker from [Docker Website](https://www.docker.com/), run

```
mkdir C:\mysql-data
mkdir C:\grafana-data
```

Check the usable address by `Get-NetIPAddress | Format-Table InterfaceAlias,IPAddress` or (`ipconfig` in `cmd`), and set `MQTT_BROKER` in `docker-compose.yml` as the "Ethernet"'s ip address.

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

In a nominal operation, the RGA should be controlled by a PLC, but directly connecting the RGA to the PC reduces the complexity of communication and helps with understanding how the RGA works. The PC communicates with the RGA either over RS-232 (serial mode) or via the ES-246 adapter in Raw TCP mode (tcpip mode), both handled by `srsinst.rga`.

```
PC
    │ RS-232 (serial mode)  or  TCP port 9001 via ES-246 adapter (tcpip mode)
    ▼
RGA (SRS RGA200)
```

### Installation

After installing the package by `pip install -e ./ --user`, make sure that `.local/bin` is in your `PATH` by running `export PATH="$HOME/.local/bin:$PATH"` on Linux, or by adding the corresponding directory to `PATH` on Windows.

### Commands

| Command | Description |
|---|---|
| `rga_test` | Self-test of RGA connection and MySQL database integrity |
| `rga_analog_scan` | Run an analog scan and save the result to the database |
| `rga_p_vs_t_scan` | Run a pressure-vs-time scan of one or multiple masses and save to the database |

Run any command with `--help` for full usage, e.g. `rga_p_vs_t_scan --help`. The `rga_p_vs_t_scan` command also accepts a `--masses` flag to override `RGA_MASSES` from the command line.

During each scan the filament is turned on automatically at the start and turned off at the end. If an unexpected error occurs mid-scan, the filament is turned off before the exception is re-raised.

### Environment variables

All settings are read from `.env` at runtime.

**RGA connection**

| Variable | Default | Description |
|---|---|---|
| `RGA_INTERFACE_TYPE` | `serial` | Connection mode: `serial` for direct RS-232, `tcpip` for ES-246 Raw TCP |
| `RGA_USB_SERIAL_DEVICE_IDENTIFIER` | `/dev/tty.usbserial-FTEIZFXM` | Serial port name (serial mode only). Use `/dev/ttyUSB0` style on Linux or `COM9` style on Windows |
| `RGA_BAUD_RATE` | `28800` | Baud rate for RS-232 (serial mode only) |
| `RGA_IP_ADDRESS` | `192.168.127.254` | IP address of the ES-246 adapter (tcpip mode only) |
| `RGA_PORT` | `9001` | TCP port of the ES-246 adapter (tcpip mode only) |

**Database**

| Variable | Default | Description |
|---|---|---|
| `RGA_MODEL` | `RGA200` | Model name of the RGA, used to identify the instrument in the database |
| `RGA_SERIAL_NUMBER` | `17405` | Serial number of the RGA, stored in the database on first run |
| `MYSQL_HOST` | `127.0.0.1` | MySQL server hostname |
| `MYSQL_PORT` | `3306` | MySQL port |
| `MYSQL_USER` | `rga_user` | MySQL username |
| `MYSQL_PASSWORD` | `rgapw` | MySQL password |
| `MYSQL_DB` | `rga` | MySQL database name |

**Analog scan**

| Variable | Default | Description |
|---|---|---|
| `RGA_INITIAL_MASS` | `1` | First mass in amu |
| `RGA_FINAL_MASS` | `200` | Last mass in amu |
| `RGA_RESOLUTION` | `10` | Steps per amu (10–25) |
| `RGA_SCAN_SPEED` | `3` | Scan speed (0–7) |

**Pressure-vs-time scan**

| Variable | Default | Description |
|---|---|---|
| `RGA_MASSES` | — | Comma-separated list of masses in amu, e.g. `2,18,28,32,44` |
| `RGA_SCAN_TOTAL_TIME` | `60` | Total scan duration in seconds |
| `RGA_SCAN_TIME_INTERVAL` | `5` | Interval between measurements in seconds |

**Other**

| Variable | Default | Description |
|---|---|---|
| `FAKE_EXECUTION` | `0` | Set to `1` to run a dry-run without connecting to the RGA or writing real data |

## RGA Operation Controlled by PC via PLC

Related codes are in `rga_etl\pc_plc`.

In this mode the PC does not communicate with the RGA directly. Instead, the PC publishes MQTT messages to a Mosquitto broker; the PLC subscribes, forwards commands to the RGA over RS-232 via the ES-246 adapter, and publishes the response back. The `mqtt_bridge` service is the glue: it exposes an HTTP API that Grafana (via the `volkovlabs-form-panel` plugin) calls, translates each request into MQTT commands, waits for the PLC response, and writes results to MySQL.

```
Grafana (port 3000)
    │ HTTP POST (port 8080)
    ▼
mqtt_bridge (Docker container)
    │ MQTT pub/sub (port 1883)
    ▼
Mosquitto broker (Docker container)
    │ MQTT
    ▼
PLC (BRX Do-more BX-DM1E-10ER3-D)
    │ RS-232 via ES-246 Ethernet-to-serial adapter (Raw TCP, port 9001)
    ▼
RGA (SRS RGA200)
```

### mqtt_bridge HTTP API

The `mqtt_bridge` service is already declared in `docker-compose.yml` and starts with the rest of the stack. It listens on port `8080` and only accepts `POST` requests with a JSON body. All requests are processed sequentially — a `409` is returned if a scan is already running or a command is in flight.

| Endpoint | Description | Required JSON fields |
|---|---|---|
| `POST /rga_p_vs_t_scan` | Pressure-vs-time scan (runs asynchronously in background) | `MR` (list of masses), `TOTALTIME` (seconds), `TIMEINTERVAL` (seconds) |
| `POST /rga_single_mass_scan` | Single-mass ion current measurement | `MR` (integer mass) |
| `POST /rga_analog_scan` | Full analog scan over a mass range | `INITIAL_MASS`, `FINAL_MASS`, `SCAN_RATE` (0–7), `STEPS_PER_AMU` (10–25) |
| `POST /rga_arbitrary_command` | Send any raw RGA command | `COMMAND` (string), `LENGTH` (int), `WITH_RESULT` (0 or 1), `TIMEOUT` (float) |
| `POST /reset` | Reset the PLC | _(empty body `{}`)_ |

### MQTT topic structure

All topics are prefixed with `plc`. The bridge publishes RGA command parameters as individual topics (e.g. `plc/rga/command`) and then triggers execution by publishing `1` to the action topic. The PLC publishes its response to `plc/response`.

| Direction | Topic | Purpose |
|---|---|---|
| PC → PLC | `plc/rga/generic` | Trigger RGA command execution |
| PC → PLC | `plc/reset` | Trigger PLC reset |
| PC → PLC | `plc/rga/command` | RGA command string (e.g. `MR28\r`) |
| PC → PLC | `plc/rga/length` | Expected response length in bytes |
| PC → PLC | `plc/nocommand` | `1` = skip sending the command (read-only continuation) |
| PLC → PC | `plc/response` | Raw response payload from the RGA |

### Environment variables for `mqtt_bridge`

These are set in `docker-compose.yml` under the `mqtt_bridge` service:

| Variable | Default | Description |
|---|---|---|
| `MQTT_BROKER` | `169.254.11.119` | IP address of the Mosquitto broker (set to the host "Ethernet" IP) |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MYSQL_HOST` | `mysql` | MySQL container hostname |
| `MYSQL_PORT` | `3306` | MySQL port |
| `MYSQL_USER` | `rga_user` | MySQL user |
| `MYSQL_PASSWORD` | `rgapw` | MySQL password |
| `MYSQL_DB` | `rga` | MySQL database name |
