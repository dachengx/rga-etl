# Installation and configuration of MQTT broker on Windows

## Installation

Download `mosquitto-2.0.22-install-windows-x64.exe` from [mosquitto website](https://mosquitto.org/download/).

Install `mosquitto-2.0.22-install-windows-x64.exe`.

## Configuration of broker(server) on Windows

Open Command Prompt (`cmd`) and run

```
notepad C:\Users\xudac\mosquitto.conf
```

Write

```
listener 1883 0.0.0.0
allow_anonymous true
```

Save file.

Start MQTT broker by

```
"C:\Program Files\mosquitto\mosquitto.exe" -v -c C:\Users\xudac\mosquitto.conf
```

## Test MQTT publish-subscribe (pub/sub)

Open another `cmd` terminal, run

```
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h 169.254.11.119 -t brx/control/do -v
```

where `169.254.11.119` is the IP address of `Ethernet adapter Ethernet` after running `ipconfig`.

Open the third `cmd` terminal, run

```
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h 169.254.11.119 -t brx/control/do -m 1
```

You should see

```
brx/control/do 1
```

in the second terminal. This means the broker is correctly setup.

## Connect the PLC to PC's MQTT broker

Set the `MQTTClient`'s server address as `169.254.11.119`.
