# HPE iLO Redfish Interface Emulator

```markdown
The HPE iLO Redfish Interface Emulator emulates various HPE iLO BMCs for testing and development.  
The emulator mimics HPE iLO BMC behavior, allowing application development and testing without access to physical hardware.
This is particularly useful for developers working with the Morpheus HPE Bare Metal plugin, as it enables development and testing of the plugin without needing actual HPE servers.
```

## Topics:

* [Available BMC types](#available-bmc-types)
* [Running the emulator](#running-the-emulator)
  * [Build the docker image](#build-docker-image)
  * [Emulator Configuration](#emulator-configuration)
  * [Running a single instance](#running-single-instance)
  * [Running multiple instances](#running-multiple-instances)
* [Credit](#credit)

<a name="available-bmc-types"></a>

## Available BMC types
The emulator currently supports the following BMC types:
- DL325 (ProLiant DL325 Gen10 Plus)
- DL360 (ProLiant DL360 Gen10 Plus)
- DL380a (ProLiant DL380 Gen11 - w/ 2 Nvidia A40 GPUs)
- ... more to come

<a name="running-the-emulator"></a>

## Running the emulator

The emulator can be run as a docker image or locally.  This README focuses on running the emulator with docker compose, which is the recommended way to run the emulator.

<a name="build-docker-image"></a>

### Build the docker image:
```
docker build -t ilo-emulator:latest .
```

<a name="emulator-configuration"></a>

### Emulator Configuration:
The emulator has 3 configurable parameters that can be set via environment variables.
- `MOCKUP_FOLDER`: Specifies the folder containing the mockup files for the BMC type to emulate. These are the Avalable BMC types listed above.
- `EXTERNAL_PORT`: Specifies the external port on which the emulator will listen for incoming requests. This can be a single port or a port range (ex. 5001-5005).
- `ASYNC_SLEEP`: Specifies the sleep time in seconds for asynchronous operations. This can be used to simulate delays in responses from the BMC.

The defaults for the emulator are set in the .env file as
```
MOCKUP_FOLDER=DL380a
EXTERNAL_PORT=443
ASYNC_SLEEP=0
```

To change the defaults, you can either modify the .env file or set environment variables when running the docker compose command.

<a name="running-single-instance"></a>

### Running a single instance
To run a single emulator instance:
```
source ./env
docker compose up 
```

<a name="running-multiple-instances"></a>

### Running multiple instances
Running multiple instance of the emulator is enabled by creating docker containers with different external ports. The emulator will automatically assign a port in the range specified by EXTERNAL_PORT to each instance of the emulator.
The port range must contain at least as many ports as the number of instances you want to run.
```
EXTERNAL_PORT=<your port range> docker compose up --scale emu=<number of instances> -d 
```
- Example: run 2 instances of the emulator:
```
EXTERNAL_PORT=5001-5002 docker compose up --scale emu=2 -d 
```

### Helpful commands

#### See the running containers with their assigned ports:
```
docker container ls
```

#### Tail a container log:
```
docker-compose logs -f <container name>
```

#### Stop all containers there were started with docker compose:
```
docker-compose down
```

#### To reset the port given from the port range, restart the docker daemon:
```
(Ubuntu): sudo systemctl restart docker
(MacOS using Colima): colima restart
```

<a name="using-with-morpheus"></a>

## How to use with the Morpheus HPE Bare Metal plugin 
When prompted for the iLO IP Address, use the IP address and external port of the emulator container.

For example, if you are running a single emulator with the default port (443), you would use:
```
127.0.0.1  (the port is not required, as 443 is the default port for HTTPS)
```
If you are running multiple instances of the emulator, you would use the IP address of the container and the external port assigned to that instance.
For example, if one of the instances is running on port 5001, you would use:
```
127.0.0.1:5001
```

The emulated iLO's username and password are:
```
Username: root
Password: root_password
```

## Credit
The HPE iLO Redfish Interface Emulator is based on Cray's CSM Redfish Interface Emulator (https://github.com/Cray-HPE/csm-redfish-interface-emulator), which is based on DMTF's [Redfish Interface Emulator] (https://github.com/DMTF/Redfish-Interface-Emulator).