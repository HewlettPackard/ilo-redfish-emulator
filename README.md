# HPE iLO Redfish Interface Emulator

The HPE iLO Redfish Interface Emulator is based off of Cray's CSM Redfish Interface Emulator (https://github.com/Cray-HPE/csm-redfish-interface-emulator), which is base on DMTF's [Redfish Interface Emulator] (https://github.com/DMTF/Redfish-Interface-Emulator) and can emulate a redfish interface with static and dynamic resources.

Although this project is based on DMTF's Redfish Interface Emulator project, it deviates a bit from DMTF's project's functionality. DMTF's project's dynamic resources are meant to be fully generated and generic. The CSM Redfish Interface Emulator project takes this an uses it to create dynamic resources that sit under a static mockup to emulate specific BMCs.

Static resources are emulated by simply copying a redfish mockup into the ./mockups/<BMC_type> directory and specifying the <BMC_type> in the MOCKUPFOLDER environment variable. The emulator will automatically try to apply known dynamic resources to the mockup such as the AccountService using the [default loader](#default-loader). All other URIs will answer to GET only. For more on static resources see the [Creating a Static Mockup](#creating-static-mockup) section.

Dynamic emulation is accomplished by creating custom python files for each dynamic resource. You can use the [Update Service API](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py) as an example when creating a new dynamic resources.

New BMC types for emulation are created by loading a complete static mockup and overriding the resource URIs that you want to be dynamic.

## Topics:

* [Running the emulator](#running-the-emulator)
    * [Docker](#docker)
    * [Locally](#locally)
    * [Redfish Authorization](#redfish-auth)
* [Creating a new BMC type for emulation](#creating-new-emulator)
    * [Creating a static mockup](#creating-static-mockup)
    * [Creating dynamic resources](#creating-dynamic-resources)
        * [Default Loader](#default-loader)
        * [Creating a New Loader](#creating-new-loader)
        * [Dynamic Resources](#dynamic-resources)
        * [Behavior controls](#behavior-controls)
        * [Templates for dynamic resources](#templates-for-dynamic-resources)
* [Existing static mockups](#existing-static-mockups)
* [Existing dynamic resources](#existing-dynamic-resources)
* [Emulator to Loader Map](#emulator-loader-map)

<a name="running-the-emulator"></a>

## Running the emulator

This emulator can be run locally or as a docker image.

<a name="docker"></a>

### Docker

You can run a predefined emulator using ./Dockerfile and setting the MOCKUPFOLDER environment variable, their ./mockups/<BMC_type>/Dockerfile (i.e. ./mockups/EX325a/Dockerfile), or create a ./mockups/<BMC_type>/Dockerfile in your custom mockup directory.

**NOTE:** 'Dockerfile' assumes your custom static files are in place in the ./mockups/<MyBMC> directory.

**NOTE:** When using the emulator with a custom mockup that does not have a loader specified for it in ./src/api_emulator/resource_manager.py, the generic loader will be used to generate a best guess mockup using known dynamic resources.

Build the docker image.
```
docker build -t bm-sim:latest -f ./Dockerfile .
```

Set a local port for your BMC. 
```
BMC_PORT=5100
```

Set the mockup folder to the BMC type you want to emulate. The default is DL325.
```
export MOCKUPFOLDER=DL325
```

### To build the docker image:
```
docker build -t ilo-emulator:latest .
```

### Run the docker image:
```
docker run -p ${BMC_PORT}:443 -e MOCKUPFOLDER=<BMC_type> --rm ilo-emulator:latest
```

### Run multiple instances of the emulator:
```
docker-compose up --scale <mockup>=<number of instances> -d 
```
#### For example, to run 3 instances of the DL325 emulator and 2 instances of the DL360 emulator:
```
docker-compose up --scale DL325=3 --scale DL360=2 -d
```

### To see the running containers with their assigned ports:
```
docker container ls
```

### To tail a container log:
```
docker-compose logs -f <container name>
```

To stop the emulators:
```
docker-compose down
```

To reset the assigned port in the range, restart the docker daemon:
```
(Ubuntu): sudo systemctl restart docker
(MacOS using Colima): colima restart
```
<a name="locally"></a>

### Locally

This method runs setup.sh which will copy the resources into a new directory, create a virtual environment, install the required packages, and run the emulator.

**NOTE:** When using the emulator with a custom mockup that does not have a loader specified for it in ./src/api_emulator/resource_manager.py, the generic loader will be used to generate a best guess mockup using known dynamic resources.

Set a local port for your BMC
```
BMC_PORT=5100
```

Run the setup.sh script.
```
./setup.sh -p ${BMC_PORT} -m <BMC_type> -w ../<WORK_DIR>
```

This will create a <WORK_DIR> directory outside of your csm-redfish-interface-emulator directory, copy the local csm-redfish-interface-emulator files and directories into the specified workspace directory, and run the emulator. All static mockups in csm-redfish-interface-emulator/mockups will be copied into <WORK_DIR>/api_emulator/redfish/static.

The setup.sh script can also be run without starting the emulator to just prepare the emulator files.
```
./setup.sh -p ${BMC_PORT} -w ../<WORK_DIR> -n
```

**NOTE:** If <WORK_DIR> already exists before running the setup.sh script, it will first get deleted.

<a name="redfish-auth"></a>

### Redfish Authorization

The emulator supports Basic and session authorization (X-Auth-Token). Initial accounts can be created by setting the AUTH_CONFIG environment variable. The expected format is <username>:<password>:<role> where <role> is one of Administrator, Operator, or ReadOnly as defined by DMTF as required default redfish roles.

These roles carry the following redfish privileges as defined by DMTF:
- Administrator
   - Login
   - ConfigureManager
   - ConfigureUsers
   - ConfigureSelf
   - ConfigureComponents
- Operator
   - Login
   - ConfigureSelf
   - ConfigureComponents
- ReadOnly
   - Login
   - ConfigureSelf

Access to the emulators URIs are privilege based and are set per HTTP method for dynamic resources. Static resources (GET only) require Login privileges for access.

Any account specified by AUTH_CONFIG will be also added under the AccountService in the emulated redfish server and, if using the dynamic resource, can be manipulated (Add/Delete/Patch) using the AccountService. Actions under the AccountService will affect the emulator's authorization accounts.

Similarly, session tokens can be created with SessionService actions if the emulator is using the dynamic resource. No sessions exist by default.

By default, if AUTH_CONFIG is empty or an invalid format, the emulator will have 3 accounts created:
- root:root_password:Administrator
- operator:operator_password:Operator
- guest:guest_password:ReadOnly

<a name="creating-new-emulator"></a>

## Creating a new BMC type for emulation

New BMC types can be added for emulation. This can be done by using a completely static mockup or a mix of static and dynamic resources. The following outlines the overall process.

<a name="creating-static-mockup"></a>

### Creating a static mockup

A static mockup is a directory tree that is an exact copy of the desired BMC type's redfish tree starting at the service base, /redfish/v1. Each directory has an index.json file that contains a copy of what is returned by a GET to that resource in the redfish tree. For example:
```
DL325:
- Systems
-- 1
...
--- index.json
-- index.json
- index.json
```

DMTF has a tool that can be run against a real BMC to walk the entire redfish tree and create a mockup, the [Redfish Mockup Creator](https://github.com/DMTF/Redfish-Mockup-Creator).

The Redfish Mockup Creator can be run locally. For example, to create the DL360 mockup, run the Redfish Mockup Creator
```
Redfish-Mockup-Creator> python ./redfishMockupCreator.py --u <username> --p <password> --A basic --r <server ip> -S -D ./DL325
```

**NOTE** Morpheus Bare Metal plugin hints:
* If the password contains special characters, you may need to escape them.
* The Redfish-Mockup-Creator needs to be run against a real BMC that is powered on so it captures the drives.
* Remove Systems/1/Storage/Volumes/1
* Clear the members entry in Systems/1/Storage/Volumes/index.json
* To be recognized by the Morpheus Bare Metal plugin as a simulated server, following need to be modified in the
  static mockup:
    * In Systems/1/index.json, the Model field needs to end with " - SIMULATED"
    * In index.json, the Product field needs to end with " - SIMULATED"

**NOTE:** DMTF's Redfish Mockup Creator only follows "@odata.id", "Uri", or "Members@odata.nextLink" links to go deeper. Because of this "@Redfish.ActionInfo" URIs such as '/redfish/v1/Systems/1/ResetActionInfo' do not get automatically captured. To complete the mockup, they either need to be manually copied or you need to checkout the [Redfish Mockup Creator](https://github.com/DMTF/Redfish-Mockup-Creator) and add 'or item == "@Redfish.ActionInfo"' [here](https://github.com/DMTF/Redfish-Mockup-Creator/blob/master/redfishMockupCreate.py#L284) and [here](https://github.com/DMTF/Redfish-Mockup-Creator/blob/master/redfishMockupCreate.py#L338) before running it.

The static resource tree for a BMC type needs to be placed in csm-redfish-interface-emulator/mockups/<BMC_type> such that the index.json file in ./<BMC_type> is for the resource base, /redfish/v1.

<a name="creating-dynamic-resources"></a>

### Creating dynamic resources

To create an emulator with dynamic resources for a new BMC type you can either:
1) Create no new files and let the default loader, [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/loader.py), use its best guess at selecting the correct dynamic resources for your mockup.
2) Create a <BMC_type>_loader.py file where the functions for setting up the dynamic resources will live. The [hpe_cray_ex235a_loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/hpe_cray_ex235a_loader.py) is an example of this.

A new loader and dynamic resource files may be required if your mockup requires any non-standard modifications that are not handled by the default loader.

<a name="default-loader"></a>

#### Default Loader

The [default loader](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/loader.py) will automatically be used for <BMC_type> not matched in [resource_manager.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/resource_manager.py#L137). It uses a best guess approach to determine which known dynamic resources to use for the mockup depending on which URI's are available in the static mockup. If the default loader can't determine which dynamic resource to use, it will not set one up and that set of URI's will continue to be Static, GET only, resources.

The default loader is the parent Loader python class that is used as the base for all <bmc_type>_loaders.

The Loader class currently sets up dynamic resources for:
- Power Limit (init_power_limit())
    - Generic Power Limit Schema
        - GET/PATCH /redfish/v1/Chassis/{sys_id}/Power
    - HPE Cray EX Power Limit Schema
        - GET/PATCH /redfish/v1/Chassis/{sys_id}/Controls/{control_id}
        - PATCH     /redfish/v1/Chassis/{sys_id}/Controls.Deep
    - Apollo 6500 Power Limit Schema
        - GET  /redfish/v1/Chassis/{sys_id}/Power/AccPowerService/PowerLimit
        - POST /redfish/v1/Chassis/{sys_id}/Power/AccPowerService/PowerLimit/Actions/HpeServerAccPowerLimit.ConfigurePowerLimit
- System Power Actions (init_system_reset())
    - Generic
        - GET      /redfish/v1/Systems/{sys_id}
        - GET/POST /redfish/v1/Systems/{sys_id}/Actions/ComputerSystem.Reset
- Chassis Power Actions (init_chassis_reset())
    - Generic
        - GET      /redfish/v1/Chassis/{chassis_id}
        - GET/POST /redfish/v1/Chassis/{chassis_id}/Actions/Chassis.Reset
- Manager Power Actions (init_manager_reset())
    - Generic
        - GET      /redfish/v1/Managers/{manager_id}
        - GET/POST /redfish/v1/Managers/{manager_id}/Actions/Manager.Reset
- Update Service (init_update_service())
    - Generic
        - GET       /redfish/v1/UpdateService/FirmwareInventory/{target_id}
        - POST      /redfish/v1/UpdateService/SimpleUpdate
        - GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
- Account Service (init_account_service())
    - Generic
        - GET/POST         /redfish/v1/AccountService/Accounts
        - GET/PATCH/DELETE /redfish/v1/AccountService/Accounts/{id}
- Session Service (init_session_service())
    - Generic
        - GET/POST   /redfish/v1/SessionService/Sessions
        - GET/DELETE /redfish/v1/AccountService/Sessions/{id}
- Certificate Service (init_certificate_service())
    - HPE Cray EX Schema
        - POST /redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate
- Manager Network Protocol (init_manager_network_protocol())
    - Generic
        - GET/PATCH /redfish/v1/Managers/{manager_id}/NetworkProtocol
- Event Service (init_event_service())
    - Generic
        - GET/PATCH        /redfish/v1/EventService
        - GET/POST         /redfish/v1/EventService/Subscriptions
        - GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/{sub_id}
- Redfish Event Generation Schemas (get_event_template())
    - Generic
    - Intel
    - Gigabyte
    - HPE Cray
    - Proliant iLO
- Manager Virtual Media
    - Generic
        - GET /redfish/v1/Managers/{manager_id}/VirtualMedia
        - POST /redfish/v1/Managers/{manager_id}/VirtualMedia/{vmedia_id}/Actions/VirtualMedia.InsertMedia
        - POST /redfish/v1/Managers/{manager_id}/VirtualMedia/{vmedia_id}/Actions/VirtualMedia.EjectMedia
- Chassis Drive Secure Erase
    - Generic
        - GET /redfish/v1/Chassis/{chassis_id}/Drives/{drive_id}
        - POST /redfish/v1/Chassis/{chassis_id}/Drives/{drive_id}/Actions/Drive.SecureErase
- System Volume API
    - Generic
        - GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}
        - GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes
        - GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes/{volume_id}
        - POST /redfish/v1/Systems/{system_id}/Storage/{storage_id}
        - DELETE /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes

The Loader class also tries to search the static mockup for serial numbers to randomize them with randomize(). MAC addresses are also modified either with a random MAC or using the Mountain scheme based on the given xname.

<a name="creating-new-loader"></a>

#### Creating a New Loader

A new loader file may be required if your mockup requires any non-standard modifications that are not handled by the default loader. This file is usually named <BMC_type>_loader.py that lives in the ./src/api_emulator directory and contains code to create a subclass of [Loader](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/loader.py).

You can override any of the methods in the Loader class or create new ones to add customizations. [hpe_cray_ex325a_loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/hpe_cray_ex325a_loader.py) is an example of this.

Add a call to your new loader in [resource_manager.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/resource_manager.py#L137)

If you have customizations needed for your new <BMC_type>, you'll likely also need to create new [dynamic resources](#dynamic-resources)

<a name="dynamic-resources"></a>

#### Dynamic Resources

Dynamic resources are the backend handlers for any URI you want to answer to more than just GET requests. They are generally named <resource>_api.py and live in the ./src/api_emulator/redfish directory. For example the generic power control resource is [power_control_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/power_control_api.py) and the HPE Cray EX variant is [hpe_cray_ex_power_control_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/hpe_cray_ex_power_control_api.py).

Your new dynamic resource files should contain classes for the collection (if it isn't a singleton) and members. These classes should be subclasses of flask_restful.Resource to be attached to a URI.

These new subclass should define methods for get(), put(), post(), patch(), and delete(). The 'request' variable comes from flask and contains all of the information about the request (method, payload, path, etc) and can be used within the method.
```
    # HTTP GET
    def get(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = members[ch_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    #
    # Apply power limit to the specified Control
    def patch(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                if 'PowerControl' in raw_dict and 'PowerControl' in members[ch_id] and \
                   raw_dict['PowerControl'] == len(members[ch_id]['PowerControl']):
                    resp = applyPatch(raw_dict['PowerControl'], ch_id)
                else:
                    resp = simple_error_response('Invalid paramters for PATCH', 400)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp
```

For authorization, define method_decorators with entries for each http method specifying auth.auth_required(priv=<required_privilages>) as the decorator. Specify the required redfish privileges that a user would need to perform that type of request on your resource. You can either list all required privileges, 'priv={Privilege.Login, Privilege.ConfigureComponents}' or just the highest one needed, 'priv={Privilege.ConfigureComponents}'. Generally, GETs require 'Privilege.Login' and all others require 'Privilege.ConfigureComponents'. The privileges are listed in [redfish_auth.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/redfish_auth.py) and are those defined in the redfish spec.
```
method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                     'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                     'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                     'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                     'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
```


<a name="behavior-controls"></a>

#### Behavior controls

A few of the existing dynamic resources have 'hidden' config URIs used for configuring response behavior for the dynamic resource on the fly. The [update_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py) file is an example of this. It provides a 'hidden' (not displayed in /redfish/v1/UpdateService/FirmwareInventory['Members']) URI. This URI is used to view (GET) currently configured behavior or set (PATCH) new behavior for the '/redfish/v1/UpdateService/SimpleUpdate' URI. For an emulated EX235a, this looks like:
```
{
  "Id": "UpdateServiceConfigInfo",
  "Name": "UpdateServiceConfig",
  "Description": "Use PATCH operations to set the below values to affect Update Service actions.",
  "Parameters": [
    {
      "DataType": "StringArray",
      "Name": "Fail",
      "Description": "List of targets that will fail update actions.",
      "AllowableValues": [
        "Node0.HPCNet3",
        "BMC",
        "Node0.HPCNet0",
        "FPGA2",
        "Node0.HPCNet1",
        "Node0.AccVBIOS",
        "Bootloader",
        "Node0.HPCNet2",
        "Node0.AccUC",
        "Recovery",
        "FPGA0",
        "Node0.BIOS",
        "FPGA1",
        "Node0.ManagementEthernet"
      ]
    },
    {
      "DataType": "Int",
      "Name": "Hang",
      "Description": "Amount of time in seconds to Hang."
    },
    {
      "DataType": "Int",
      "Name": "UpdateTime",
      "Description": "Amount of time in seconds to for updates to take."
    }
  ],
  "CurrentValues": {
    "UpdateTime": 10,
    "Fail": [
      "BMC"
    ],
    "Hang": 0
  }
}
```
You may wish to create a resource such as this for each of your dynamic resource to make testing more configurable.

<a name="templates-for-dynamic-resources"></a>

#### Templates for dynamic resources

Some dynamic resources such as the EventService generate responses (i.e. Redfish events) that are BMCType specific. Templates are used for these resources. The templates exist in the [src/api_emulator/redfish/templates/](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/redfish/templates) directory. The EX235a emulator uses [hpe_cray_ex_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/cray_events.py) for generating redfish events for the EventService. Which templates to use are generally set by the <BMC_type>_loader.py when response format can vary between BMC type.

<a name="existing-static-mockups"></a>

## Existing static mockup files:
- [DL325](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/mockups/DL325) (ProLiant DL325 Gen10 Plus)
- [DL360](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/mockups/DL360) (ProLiant DL360 Gen10 Plus)
- [EX235a](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/mockups/EX235a) (Bard Peak - is not used my Morpheus Bare Metal plugin, but is kept for reference)

<a name="existing-dynamic-resources"></a>

## Existing dynamic resources:
- Power Control
    - Generic -  [power_control_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/power_control_api.py)
        - GET/PATCH /redfish/v1/Chassis/<system_id>/Power
    - HPE Cray EX - [hpe_cray_ex_power_control_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/hpe_cray_ex_power_control_api.py)
        - GET/PATCH /redfish/v1/Chassis/<system_id>/Controls/<control_id>
        - PATCH     /redfish/v1/Chassis/<system_id>/Controls.Deep
    - Proliant iLO - [proliant_ilo_power_control_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/proliant_ilo_power_control_api.py)
        - GET  /redfish/v1/Chassis/<system_id>/Power/AccPowerService/PowerLimit
        - POST /redfish/v1/Chassis/<system_id>/Power/AccPowerService/PowerLimit/Actions/HpeServerAccPowerLimit.ConfigurePowerLimit
- Computer System Power Actions - [computer_systems_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/computer_systems_api.py)
    - GET /redfish/v1/Systems/<system_id>
    - POST /redfish/v1/Systems/<system_id>/Actions/ComputerSystem.Reset
- Chassis Power Actions - [chassis_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/chassis_api.py)
    - GET      /redfish/v1/Chassis/<chassis_id>
    - GET/POST /redfish/v1/Chassis/<chassis_id>/Actions/Chassis.Reset
- Manager Power Actions - [manager_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/manager_api.py)
    - GET      /redfish/v1/Managers/<manager_id>
    - GET/POST /redfish/v1/Managers/<manager_id>/Actions/Manager.Reset
- Firmware Update - [update_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/update_service_api.py)
    - GET /redfish/v1/UpdateService/FirmwareInventory/<target_id>
    - POST /redfish/v1/UpdateService/SimpleUpdate
    - GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
- EventService - [event_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/event_service_api.py), [event_generator.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/event_generator.py)
    - GET/PATCH        /redfish/v1/EventService
    - GET/POST         /redfish/v1/EventService/Subscriptions
    - GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/<id>
- Event templates
    - Generic - [events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/events.py)
    - Intel - [intel_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/intel_events.py)
    - Gigabyte - [gigabyte_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/gigabyte_events.py)
    - HPE Cray - [hpe_cray_ex_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/hpe_cray_ex_events.py)
    - Proliant iLO - [proliant_ilo_events.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/templates/proliant_ilo_events.py)
- Account Service - [account_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/account_service_api.py)
    - GET/POST         /redfish/v1/AccountService/Accounts
    - GET/PATCH/DELETE /redfish/v1/AccountService/Accounts/<id>
- Session Service - [session_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/session_service_api.py)
    - GET/POST   /redfish/v1/SessionService/Sessions
    - GET/DELETE /redfish/v1/AccountService/Sessions/<id>
- Certificate Service - [hpe_cray_ex_certificate_service_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/hpe_cray_ex_certificate_service_api.py)
    - POST /redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate
- Manager Network Protocol - [manager_network_protocol_api.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/blob/master/src/api_emulator/redfish/manager_network_protocol_api.py)
    - GET/PATCH /redfish/v1/Managers/<manager_id>/NetworkProtocol

<a name="emulator-loader-map"></a>

## Emulator to Loader Map

- public-rackmount1 - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- CMM - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- DL325 - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- EX235a - [ex235a_loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/ex235a_loader.py)
- EX235n - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- EX420 - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- EX425 - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- Gigabyte - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- Intel - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- Slingshot_Switch_Blade - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
- XL675d_A40 - [loader.py](https://github.com/Cray-HPE/csm-redfish-interface-emulator/tree/master/src/api_emulator/loader.py)
