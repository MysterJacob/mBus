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

| Module | Group+ | Endpoint |
| ------ | ----- | -------- |

#### Name of adress parts
* Module - Defined by the user or automaticly determined
* Group - Created and defined by the user
* Endpoint - Created and defined by the user

## Documentation

### Methods
##### for mBus
| Name | Arguments | Return value | Description |
| :--: | ------------------ | :----------: | :---------- |
| loadModule | module : Module | None | |
| loadModuleFromFile | filename : Path | | |
| unloadModule | name : str | | Unloads given module |
| isModuleLoaded | moduleName : str | isLoaded : bool | Check is module loaded |
| addressExists | address : str | exists : bool | Check if address exists |
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
