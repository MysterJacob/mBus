import re
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Union
from threading import Lock

class BusException(Exception):
    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return str(self)

class RailAlready(BusException):
    '''Exception thrown when rail with provided name does already exist'''

class RailAlreadyBound(BusException):
    '''Exception thrown when rail with given name is already bound to module'''

class RailNotFound(BusException):
    '''Exception thrown when rail with given name is not found in module'''

class InvalidRailName(BusException):
    '''Exception thrown when rail name does not meet the criteria'''

class GroupAlreadyExists(BusException):
    '''Exception thrown when group with provided name does already exist'''

class InvalidGroupName(BusException):
    '''Exception thrown when group name not meeting the criteria'''

class GroupNotFound(BusException):
    '''Exception thrown when group is not found on target'''

class EndpointNotFound(BusException):
    '''Exception thrown when endpoint is not found on target'''

class EndpointGroupCollision(BusException):
    '''Exception thrown when endpoint is colliding with existing group'''

class EndpointAlreadyExists(BusException):
    '''Exception thrown when endpoint is reinitialized with the same nae for second time'''

class InvalidEnpointParameter(BusException):
    '''Exception thrown trying to use parameter that is not compatibile with given endpoint type'''

class MissingEndpointParameter(BusException):
    '''Missing parameter for given type of endpoint'''

class InvalidFieldValueType(BusException):
    '''Field is set with variable type different from the field type'''

class InvalidEndpointType(BusException):
    '''Exception thrown when provided endpoint type is not valid'''

class CanNotCreateEndpointOnRail(BusException):
    '''Exception thrown when user tries to create endpoint on rail'''

class InvalidEnpointName(BusException):
    '''Exception thrown when endpoint name not meeting criteria'''

class MissingArgumentException(BusException):
    '''Endpoint triggered with missing required argument'''

class UnknownArgument(BusException):
    '''Endpoint triggered with extra argument'''

class InvalidArgument(BusException):
    '''Endpoint triggered with invalid argument'''

class FireTriggerFailed(BusException):
    '''Trigger fire failed'''

class CallEventFailed(BusException):
    '''Event call failed'''

class ActionInvalidRType(BusException):
    '''Return value type does not math provided type'''

class SettingFieldFailed(BusException):
    '''Setting a field failed'''

class InvalidTrigger(BusException):
    '''Trying to fire something that is not a trigger'''

class InvalidEvent(BusException):
    '''Trying to call something that is not a event'''

class InvalidAction(BusException):
    '''Trying to call something that is not a action'''

class InvalidField(BusException):
    '''Trying to set/get something that is not a field'''

class GettingFieldFailed(BusException):
    '''Getting a field failed'''

RAIL_NAME_REGEX = '^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9]|_)*$'
def isRailNameInvalid(railName : str) -> bool:
    return re.fullmatch(RAIL_NAME_REGEX, railName) is None

GROUP_NAME_REGEX = '^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9])*$'
def isGroupNameInvalid(railName : str) -> bool:
    return re.fullmatch(GROUP_NAME_REGEX, railName) is None

@dataclass
class busEndpoint:
    endpointName : str

@dataclass
class busTrigger(busEndpoint):
    endpointDelegate : Callable
    arguments : dict[str, type]

@dataclass
class busEvent(busEndpoint):
    endpointDelegates : list[Callable]

@dataclass
class busField(busEndpoint):
    type : type
    value : Any

@dataclass
class busAction(busEndpoint):
    endpointDelegate : Callable
    arguments : dict[str, type]
    rtype : type

@dataclass
class busGroup:
    groupName : str
    groups : dict[str, 'busGroup']
    endpoints : dict[str, busEndpoint]

    def __hash__(self) -> int:
        return hash(self.groupName)

    def getGroup(self, groupName : str) -> 'busGroup':
        if not groupName in self.groups.keys():
            raise GroupNotFound(f'Group {groupName} is not found in group {self.groupName}')

        return self.groups[groupName]

    def getEndpoint(self, endpointName : str) -> busEndpoint:
        if not endpointName in self.endpoints.keys(): 
            raise EndpointNotFound(f'Endpoint {endpointName} is not found in group {self.groupName}')

        return self.endpoints[endpointName]

    def createGroup(self, groupName : str) -> None:
        if groupName in self.groups.keys():
            raise GroupAlreadyExists(f'Group {groupName} exists in group {self.groupName}')

        if isGroupNameInvalid(groupName):
            raise InvalidGroupName(f'Group name {groupName} is not vaild name for group')

        newGroup = busGroup(groupName, {}, {})
        self.groups[groupName] = newGroup

    def __checkParameters(self, endpointParameters : dict, requiredParameters : set, allParameters : set):
        endpointParametersKeys = set(endpointParameters.keys())

        difference = requiredParameters - endpointParametersKeys
        if len(difference) != 0:
            raise MissingEndpointParameter(f"Argument {difference.pop()} is missing form endpoint parameters.")

        difference = endpointParametersKeys - allParameters
        if len(difference) != 0:
            raise InvalidEnpointParameter(f"Argument {difference.pop()} is invalid for given endpoint type.")

    def __checkParametersForTrigger(self, endpointParameters : dict):
        requiredParameters = set(["responder", "arguments"])
        allParameters = set(["responder", "arguments"])

        return self.__checkParameters(endpointParameters, requiredParameters, allParameters)

    def __checkParametersForEvent(self, endpointParameters : dict):
        requiredParameters = set(["responders"])
        allParameters = set(["responders"])

        return self.__checkParameters(endpointParameters, requiredParameters, allParameters)

    def __checkParametersForField(self, endpointParameters : dict):
        requiredParameters = set(["type", "value"])
        allParameters = set(["type", "value"])

        return self.__checkParameters(endpointParameters, requiredParameters, allParameters)

    def __checkParametersForAction(self, endpointParameters : dict):
        requiredParameters = set(["responder", "arguments", "rtype"])
        allParameters = set(["responder", "arguments", "rtype"])

        return self.__checkParameters(endpointParameters, requiredParameters, allParameters)

    def __createTriggerEndpoint(self, endpointName, endpointParameters):
        self.__checkParametersForTrigger(endpointParameters)
        trigger = busTrigger(endpointName, endpointParameters["responder"], endpointParameters["arguments"])
        self.endpoints[endpointName] = trigger

    def __createEventEndpoint(self, endpointName, endpointParameters):
        self.__checkParametersForEvent(endpointParameters)
        responders = endpointParameters["responders"]

        if isinstance(responders, Callable):
            responders = [responders]

        event = busEvent(endpointName, responders)
        self.endpoints[endpointName] = event

    def __createFieldEndpoint(self, endpointName, endpointParameters):
        self.__checkParametersForField(endpointParameters)

        fieldType = endpointParameters["type"]
        fieldValue = endpointParameters["value"]
        if not isinstance(fieldValue, fieldType):
            raise InvalidFieldValueType(f'Value of type {type(fieldValue)} is not compatibile with type {fieldType}')

        field = busField(endpointName, fieldType, fieldValue)
        self.endpoints[endpointName] = field

    def __createActionEndpoint(self, endpointName, endpointParameters):
        self.__checkParametersForAction(endpointParameters)

        action = busAction(
            endpointName,
            endpointParameters["responder"],
            endpointParameters["arguments"],
            endpointParameters["rtype"]
        )
        self.endpoints[endpointName] = action

    def createEndpoint(self, endpointName : str, endpointType : str, endpointParameters):
        if endpointName in self.endpoints:
            raise EndpointAlreadyExists(f'Endpoint already exists in group {self.groupName}')

        if endpointName in self.groups:
            raise EndpointGroupCollision(f'Endpoint collides with group {endpointName} in group {self.groupName}')

        match endpointType:
            case 'trigger':
                self.__createTriggerEndpoint(endpointName, endpointParameters)
            case 'event':
                self.__createEventEndpoint(endpointName, endpointParameters)
            case 'field':
                self.__createFieldEndpoint(endpointName, endpointParameters)
            case 'action':
                self.__createActionEndpoint(endpointName, endpointParameters)
            case _:
                raise InvalidEndpointType(f'Invalid enpoint type {endpointType}')

@dataclass
class busRail:
    railName : str
    groups : dict[str, busGroup]
    boundModule : Union[str, None]

    def __hash__(self) -> int:
        return hash(self.railName)

    def getGroup(self, groupName : str) -> busGroup:
        if not groupName in self.groups.keys():
            raise GroupNotFound(f'Group {groupName} is not found on rail {self.railName}')

        return self.groups[groupName]

    def createGroup(self, groupName : str) -> None:
        if groupName in self.groups.keys():
            raise GroupAlreadyExists(f'Group {groupName} exists on rail {self.railName}')

        if isGroupNameInvalid(groupName):
            raise InvalidGroupName(f'Group name {groupName} is not vaild name for group')

        newGroup = busGroup(groupName, {}, {})
        self.groups[groupName] = newGroup

class __mBusSingleton:
    def __init__(self) -> None:
        self.__mutex = Lock()
        self.__rails : dict[str, busRail] = {}
        self.__railsBindsToModules : dict[str, busRail] = {}

    def __railExists(self, railName : str):
        return railName in self.__rails.keys()

    def __getRail(self, railName : str):
        if not self.__railExists(railName):
            raise RailNotFound(f'Rail {railName} is not found on bus')
        return self.__rails[railName]

    def __bindModuleToRail(self, railName : str):
        rail = self.__getRail(railName)

        if not self.__rails[railName].boundModule is None:
            raise RailAlreadyBound(f'Rail {railName} is already bound to module {rail.boundModule}')

        moduleName = inspect.stack()[2][0].f_locals['self'].__class__.__name__

        rail.boundModule = moduleName
        self.__railsBindsToModules[moduleName] = rail

    def registerRail(self, railName : str, bindToModule : bool = False) -> None:
        if isRailNameInvalid(railName):
            raise InvalidRailName(f'Rail name {railName} is not vaild name for rail')

        if self.__railExists(railName):
            raise RailAlready(f'Rail name {railName} is already registered')

        newRail = busRail(railName, {}, None)
        self.__rails.update({railName : newRail})

        if bindToModule:
            self.__bindModuleToRail(railName)

    def getRails(self) -> set[str]:
        return set(rail.railName for rail in self.__rails.values())

    def bindModuleToRail(self, railName : str) -> None:
        self.__bindModuleToRail(railName)

    def __getGroupFromAddresses(self, addresses : list[str]) -> busRail | busGroup:
        railName, *groupNames = addresses
        finalElement = self.__getRail(railName)

        for groupName in groupNames:
            finalElement = finalElement.getGroup(groupName)

        return finalElement

    def __getGroupFromAddress(self, address : str) -> busRail | busGroup:
        return self.__getGroupFromAddresses(address.split('.'))

    def __getElementFromAddresses(self, addresses : list[str]) -> busRail | busGroup | busEndpoint:
        railName, *groupNames = addresses
        groupNamesLen = len(groupNames)
        finalElement = self.__getRail(railName)

        if groupNamesLen == 0:
            return finalElement
        elif groupNamesLen == 1:
            return finalElement.getGroup(groupNames[0])

        for groupName in groupNames[:-1]:
            finalElement = finalElement.getGroup(groupName)

        finalElementName = groupNames[-1]

        if finalElementName in finalElement.groups.keys():
            return finalElement.getGroup(finalElementName)

        return finalElement.getEndpoint(finalElementName) #type: ignore

    def __getEnpointFromAddresses(self, addresses : list[str]) -> busEndpoint:
        if len(addresses) <= 2:
            raise EndpointNotFound(f"Enpoint not found on address {'.'.join(addresses)})")

        railName, *groupNames, endpointName = addresses
        finalElement = self.__getRail(railName)

        for groupName in groupNames:
            finalElement = finalElement.getGroup(groupName)

        return finalElement.getEndpoint(endpointName) #type: ignore

    def __getEnpointFromAddress(self, address : str) -> busEndpoint:
        return self.__getEnpointFromAddresses(address.split('.'))

    def __getElementFromAddress(self, address : str) -> busRail | busGroup | busEndpoint:
        return self.__getElementFromAddresses(address.split('.'))

    def createGroup(self, address : str) -> None:
        if address.count('.') == 0:
            raise InvalidGroupName('No group name is provided on address')

        *addresses, newGroupName = address.split('.')

        finalGroup = self.__getGroupFromAddresses(addresses)

        finalGroup.createGroup(newGroupName)

    def createEndpoint(self, groupAddress : str, endpointName : str, endpointType : str, **endpointParameters) -> None:
        targetGroup = self.__getGroupFromAddress(groupAddress)
        if isinstance(targetGroup, busRail):
            raise CanNotCreateEndpointOnRail(f'Can not create endpoint on rail {targetGroup.railName}')

        targetGroup.createEndpoint(endpointName, endpointType, endpointParameters)

    def addressExists(self, address : str) -> bool:
        addressList = address.split('.')
        match len(addressList):
            case 0:
                return False
            case 1:
                return addressList[0] in self.getRails()
            case 2 if not addressList[0] in self.getRails():
                return False
            case 2 if addressList[0] in self.getRails():
                return addressList[1] in self.__getRail(addressList[0]).groups.keys()

        railName, *groupAddress = addressList 
        lastElement = self.__getRail(railName)

        for elementName in groupAddress[:-1]:
            if not elementName in lastElement.groups.keys():
                return False
            lastElement = lastElement.getGroup(elementName)

        lastElementName = groupAddress[-1]

        return lastElementName in lastElement.groups.keys() or lastElementName in lastElement.endpoints.keys() # type: ignore

    def __checkArguments(self, endpointRequiredArguments : dict, endpointArguments : dict):
        endpointArgumentsSet = set(endpointArguments.keys())
        endpointRequiredArgumentsSet = set(endpointRequiredArguments.keys())

        difference = endpointArgumentsSet - endpointRequiredArgumentsSet
        if len(difference) > 0:
            raise UnknownArgument(f"Unknown endpoint argument {difference.pop()}")

        difference = endpointRequiredArgumentsSet - endpointArgumentsSet
        if len(difference) > 0:
            raise MissingArgumentException(f"Missing endpoint argument {difference.pop()}")

        for (name, value) in endpointArguments.items():
            requiredType = endpointRequiredArguments.get(name)
            if requiredType == None: continue
            if not isinstance(value, requiredType):
                raise InvalidArgument(f"Argument {name} is not of type {requiredType}")

    def __fireTriggerWithMutex(self, endpoint : busTrigger, **kwargs) -> bool:

        return endpoint.endpointDelegate(**kwargs)

    def fireTrigger(self, address : str, **kwargs) -> bool:
        endpoint = self.__getEnpointFromAddress(address)
        if not isinstance(endpoint, busTrigger):
            raise InvalidTrigger(f'Invalid trigger {address}')

        self.__checkArguments(endpoint.arguments, kwargs)

        with self.__mutex:
            return self.__fireTriggerWithMutex(endpoint, **kwargs)

    def __callEventWithMutex(self, delegates : list[Callable], **kwargs):

        for delegate in delegates:
            delegate(**kwargs)

    def callEvent(self, address : str, **kwargs):
        endpoint = self.__getEnpointFromAddress(address)

        if not isinstance(endpoint, busEvent):
            raise InvalidEvent(f'Invalid event {address}')

        delegates = endpoint.endpointDelegates

        with self.__mutex:
            self.__callEventWithMutex(delegates, **kwargs)

    def setFieldValue(self, address : str, value : Any):
        endpoint = self.__getEnpointFromAddress(address)

        if not isinstance(endpoint, busField):
            raise InvalidField(f'Invalid field {address}')

        if not isinstance(value, endpoint.type):
            raise InvalidFieldValueType(f"Value {value} is not of type {endpoint.type}")

        with self.__mutex:
            endpoint.value = value

    def getFieldValue(self, address : str) -> Any:
        endpoint = self.__getEnpointFromAddress(address)

        if not isinstance(endpoint, busField):
            raise InvalidField(f'Invalid field {address}')

        with self.__mutex:
            value = endpoint.value

        return value

    def callAction(self, address : str, **kwargs) -> Any:
        endpoint = self.__getEnpointFromAddress(address)

        if not isinstance(endpoint, busAction):
            raise InvalidAction(f'Invalid action {address}')

        self.__checkArguments(endpoint.arguments, kwargs)

        delegate = endpoint.endpointDelegate

        with self.__mutex:
            rvalue = delegate(**kwargs)

        if not isinstance(rvalue, endpoint.rtype):
            raise ActionInvalidRType(f"Returned value is not of type {endpoint.rtype}")

        return rvalue

mbus = __mBusSingleton()
