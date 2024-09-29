# mBus
#### Async databus for python
---
## Suported endpoint types
- ### Trigger
Simple trigger. Has one responder. Triggered with arguments. Arguments must be strictly defined. May success or fail.
- ### Event
Trigger with multiple responders. Triggered with arguments. Arguments are loosely defined. Does not return any value. 
- ### Field
Simple field. Has type and value. Value can be get or set. May have listeners.
- ### Action
More advanced endpoint. Has one responder. Triggered with arguments. Arguments must be strictly defined. Returns output value.

---
## Design

### Adresses of bus are made of

| Rail | Module | Group+ | Endpoint |
| ---- | ------ | ----- | -------- |

#### Name of adress parts
* Rail - Created and defined by the user
* Module - Defined by the user or automaticly determined
* Group - Created and defined by the user
* Endpoint - Created and defined by the user

## Documentation
### Exceptions
| Name | Raised when | Description |
| :--: | ----------- | :---------- |
| BusReinitialize | Bus is reinitialized with same name for second time |  |
| ModuleExisits | Module is reinitialized with same name for second time |  |
| GroupExists | Group is reinitialized with same name for second time |  |
| EndpointAlreadyExists | Endpoint is reinitialized with same name for second time |  |
| InvalidEndpointParameter | Trying to use parameter that is not compatibile with given type of endpoint |
| InvalidEnpointType | Provided type is not a valid endpoint type |
| InvalidRailName | Rail name not meeting criteria | Rail may contain letters from ``a-z``, numbers ``0-9``, special characters ``_`` |
| InvalidGroupName | Group name not meeting criteria | Group may contain letters from ``a-z``, numbers ``0-9``, special characters ``_`` |
| InvalidEndpointName | Endpoint name not meeting criteria | Group may contain letters from ``a-z``, numbers ``0-9``, special characters ``_`` |
| MissingArgument | Endpoint triggered with missing required argument |  |
| UnknownArgument | Endpoint triggered with extra argument | Extra argument is not presend in endpoint definition | | ProcessingFailed | Processing for endpoint failed | When listener function for endpoint fails to process data |
| FireTriggerFailed | Trigger fire failed |
| CallEventFailed | Calling fire failed |
| SetingFieldFailed | Seting a field failed |
| GettingFieldFailed | Getting a field failed |
| InvalidTrigger | Trying to fire something that is not a trigger |
| InvalidEvent | Trying to call something that is not a event |
| InvalidField | Trying to set or get value of something that is not a field |
| InvalidAction | Trying to call something that is not a action |

### Methods
##### for mBus
| Name | Arguments | Return value | Description |
| :--: | ------------------ | :----------: | :---------- |
| registerRail | railName : str<br>bindToModule : bool = False | None | Creates a rail. If ``bindtoModule`` is set to True all further functions from this module will execute with this rail as default |
| bindModuleToRail | railName : str | None | Binds module to rail |
| createGroup | address : str<br>groupName : str | None | Registers a new group for given address |
| createEndpoint | groupAdress : str<br>endpointName : str<br>endpointType : str<br>responder<br>**endpointParameters| None | Registers a new group for given endpoint |
| fireTrigger | address : str<br>*args<br>**kwargs | success : bool | Fire trigger on endpoint with arguments, returns state |
| fireTriggerAsync | address : str<br>*args<br>**kwargs | success : bool | Asynchronously fire trigger on endpoint with arguments, returns state |
| callEvent | address : str<br>*args<br>**kwargs | None | Call an event on endpoint with arguments |
| callEventAsync | address : str<br>*args<br>**kwargs | None | Asynchronously calls an event on endpoint with arguments |
| addEventListener | address : str<br>listener | None | Add event listener for event at given address |
| setFieldValue | address : str<br>value : Any | None | Sets value for field at given addres |
| setFieldValueAsync | address : str<br>value : Any | None | Asynchronously sets value for field at given addres |
| getFieldValue | address : str | value : Any | Gets value of field at given address |
| getFieldValueAsync | address : str | value : Any | Asynchronously gets value of field at given address |
| callAction | address : str<br>*args<br>**kwargs | value : Any | Call an event on endpoint with arguments |
| callActionAsync | address : str<br>*args<br>**kwargs | value : Any | Asynchronously calls an event on endpoint with arguments |
| getRails | None | rails : list[str] | Get lists of available rails |
