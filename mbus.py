import re
import time
import logging
import tomllib
import asyncio
import importlib
import threading
from queue import Queue
from types import CoroutineType
from pydantic import BaseModel
from dataclasses import dataclass
from typing import Any, Callable, Union


class BusException(Exception):
    def __init__(self, message) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return str(self)


class ModuleLoadingError(BusException):
    """Error while loading module"""


class ModuleUnloadingError(BusException):
    """Error while loading module"""


class GroupCreationError(BusException):
    """Error while creating group"""


class EndpointCreationError(BusException):
    """Error while creating endpoint"""


class EndpointeCallError(BusException):
    """Error while calling an endpoint"""


class FieldValueTypeError(BusException):
    """Trying to set value with different type than expected in the field"""


class MissingConfigForModule(BusException):
    """Missing config for a module"""


MODULE_NAME_REGEX = "^([A-Z]|[a-z])([A-Z]|[a-z]|[0-9]|_)*$"


def isModuleNameInvalid(railName: str) -> bool:
    return re.fullmatch(MODULE_NAME_REGEX, railName) is None


GROUP_NAME_REGEX = "^([a-z])([A-Z]|[a-z]|[0-9])*$"


def isGroupNameInvalid(railName: str) -> bool:
    return re.fullmatch(GROUP_NAME_REGEX, railName) is None


class mbusEndpoint:
    name: str
    owner: "mbusModule"

    def probe(self, deep=False):
        return {
            "name": self.name,
            "typeName": self.__class__.__name__,
            "type": "endpoint",
            "owner": self.owner.name,
        }


class busTrigger(mbusEndpoint):
    __callback: Callable

    def __init__(self, name: str, owner: "mbusModule", **kwargs):
        if "callback" not in kwargs:
            raise EndpointCreationError(
                """Missing required argument <callback> for trigger endpoint"""
            )
        callback = kwargs["callback"]
        self.name = name
        self.owner = owner
        self.__callback = callback

    def trigger(self, *args, **kwargs) -> Any:
        try:
            result = self.__callback(*args, **kwargs)
            return result
        except TypeError:
            raise EndpointeCallError(
                f"""Endpoint <{self.name}> called with invalid arguments"""
            )


class busEvent(mbusEndpoint):
    __responders: set[Callable[..., CoroutineType]]

    def __init__(self, name: str, owner: "mbusModule", **kwargs):
        responders = kwargs.get("responders", set())
        self.name = name
        self.owner = owner
        self.__responders = responders

    def addEventListener(self, listener: Callable[..., CoroutineType]):
        self.__responders.add(listener)

    def getResponders(self, *args, **kwargs):
        return self.__responders


class busField(mbusEndpoint):
    __fieldValue: Any
    __fieldType: type
    __onChangeCallbacks: set[Callable]

    def __init__(self, name: str, owner: "mbusModule", **kwargs):
        if "fieldType" not in kwargs:
            raise EndpointCreationError(
                """Missing required argument <fieldType> for trigger endpoint"""
            )
        if "value" not in kwargs:
            raise EndpointCreationError(
                """Missing required argument <value> for trigger endpoint"""
            )

        self.name = name
        self.owner = owner
        self.__onChangeCallbacks = set()
        if "onChangeCallback" in kwargs:
            self.__onChangeCallbacks.add(kwargs["onChangeCallback"])
        self.__fieldType = kwargs["fieldType"]
        self.setValue(kwargs["value"])

    def setValue(self, value: Any):
        if not isinstance(value, self.__fieldType):
            raise FieldValueTypeError(
                f"""Value <{value}> of type <{type(value)}> found, <{self.__fieldType}> expected."""
            )

        self.__fieldValue = value
        self.__makeCallback()

    def __makeCallback(self):
        for callback in self.__onChangeCallbacks:
            callback(self.__fieldValue)

    def addOnChangeCallback(self, callback: Callable):
        self.__onChangeCallbacks.add(callback)

    def getValue(self) -> Any:
        return self.__fieldValue


class mbusGroup:
    groupName: str
    owner: "mbusModule"
    __subBus: dict[str, Union["mbusGroup", "mbusEndpoint"]]

    def __init__(self, owner: "mbusModule", groupName: str) -> None:
        self.owner = owner
        self.groupName = groupName
        self.__subBus = dict()

    def createGroup(self, groupName: str) -> "mbusGroup":
        return groupCreator(self.__subBus, self.owner, groupName)

    def createEndpoint(self, endpointName: str, **kwargs) -> "mbusEndpoint":
        return endpointCreator(
            self.__subBus, self.owner, endpointName, **kwargs
        )

    def get(self, *args, **kwargs):
        return self.__subBus.get(*args, **kwargs)

    def probe(self, deep=False):
        probed: dict[str, Any] = {
            "name": self.groupName,
            "type": self.__class__.__name__,
            "owner": self.owner.name,
        }
        if deep:
            probed["elements"] = {
                name: element.probe() for name, element in self.__subBus.items()
            }

        return probed


class mbusModule:
    name: str
    dependencies: set[str] = set()
    logger: logging.Logger
    mbus: "mBus"
    is_loaded: threading.Event
    _configTemplate: Union[type[BaseModel], None] = None
    _createGroup: Callable[[str], "mbusGroup"]
    _createEndpoint: Callable
    _callEvent: Callable
    _setFieldValue: Callable
    _probe: Callable

    def __init__(self, mbus: "mBus", **kwargs) -> None:
        self.mbus = mbus
        self.logger = logging.getLogger(self.name)

        self._createGroup = kwargs["createGroup"]
        self._createEndpoint = kwargs["createEndpoint"]
        self._callEvent = kwargs["callEvent"]
        self._setFieldValue = kwargs["setFieldValue"]
        self._probe = kwargs["probe"]

        self.is_loaded = threading.Event()

        self.__loadConfig(kwargs.get("config", None))

    def __loadConfig(self, config: Union[dict, None]):
        if self._configTemplate is None:
            return
        if config is None:
            raise MissingConfigForModule(
                f"""Missing config for module {self.name}"""
            )

        self._config = self._configTemplate(**config)

    def probe(self, deep=False):
        probed: dict[str, Any] = {
            "name": self.name,
            "typeName": self.__class__.__name__,
            "type": "module",
        }
        if deep:
            probed["elements"] = self._probe()

        return probed

    def safeWait(self, seconds: float):
        start = time.time()
        while time.time() - start < seconds:
            if not self.is_loaded:
                return

    def load(self):
        pass

    def unload(self):
        pass


def groupCreator(moduleGroups, owner: mbusModule, groupName: str):
    if isGroupNameInvalid(groupName):
        raise GroupCreationError(
            f"""Name <{groupName}> is invalid name for group"""
        )
    if groupName in moduleGroups:
        raise GroupCreationError(
            f"""Name <{groupName}> is already present on the bus"""
        )

    newGroup = mbusGroup(owner, groupName)

    moduleGroups[groupName] = newGroup

    return newGroup


def endpointCreator(
    moduleGroups, owner: mbusModule, endpointName: str, **kwargs
):
    if isGroupNameInvalid(endpointName):
        raise EndpointCreationError(
            f"""Name <{endpointName}> is invalid name for endpoint"""
        )
    if endpointName in moduleGroups:
        raise EndpointCreationError(
            f"""Name <{endpointName}> is already present on the bus"""
        )

    match kwargs.get("type"):
        case "trigger":
            newTrigger = busTrigger(endpointName, owner, **kwargs)
            moduleGroups[endpointName] = newTrigger
            return newTrigger
        case "event":
            newEvent = busEvent(endpointName, owner, **kwargs)
            moduleGroups[endpointName] = newEvent
            return newEvent
        case "field":
            newField = busField(endpointName, owner, **kwargs)
            moduleGroups[endpointName] = newField
            return newField

        case None:
            raise EndpointCreationError(
                """Missing required field <type> in endpoint creation"""
            )
        case _:
            raise EndpointCreationError(
                f"""Unknown endpoint type <{kwargs["type"]}>"""
            )


@dataclass
class EventQueueElement:
    event: busEvent
    args: tuple
    kwargs: dict


class mBus(object):
    __loadedModules: dict[str, mbusModule]
    __dependedOn: dict[str, set[str]]
    __loadingQueue: set[type[mbusModule]]
    __bus: dict[str, dict[str, Union["mbusGroup", "mbusEndpoint"]]]
    __config: dict[str, Any]
    __onLoadCallbacks: dict[str, set[Callable]]
    __eventQueue: Queue[EventQueueElement]

    def __new__(cls):
        if not hasattr(cls, "singleton"):
            cls.singleton = super(mBus, cls).__new__(cls)
        return cls.singleton

    def __init__(self, eventTimeout=5) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.__loadedModules = dict()
        self.__dependedOn = dict()
        self.__loadingQueue = set()
        self.__onLoadCallbacks = dict()
        self.__eventQueue = Queue()

        self.__bus = dict()
        self.__config = {}
        self.__logger = logging.getLogger("mBus")

        self.__eventTimeout = eventTimeout

        self.__eventThread = threading.Thread(
            target=self.__eventLoop, name="mBus event thread", daemon=True
        )
        self.__eventThread.start()

    def loadConfigFile(self, path: str):
        with open(path, "rb") as f:
            data = tomllib.load(f)
            self.__config = data
        return self.__config

    def loadModule(self, module: type[mbusModule]):
        if isModuleNameInvalid(module.name):
            raise ModuleLoadingError(
                f"""Module <{module.name}> has invalid name"""
            )
        if module in self.__loadingQueue:
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already in loading queue"""
            )
        if self.isModuleLoaded(module.name):
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already loaded"""
            )

        self.__logger.info(f"Loading module <{module.name}>")
        self.__logger.debug(
            f"Module <{module.name} dependencies: {','.join(module.dependencies)}>"
        )

        self.__loadingQueue.add(module)
        self.__tryLoadFromQueue()

    def loadModuleFromFile(self, path: str):
        moduleName = path.split(".")[-1]
        try:
            moduleFile = importlib.import_module(path)
        except ModuleNotFoundError:
            raise ModuleLoadingError(f"""Can not find module from {path}""")

        if not hasattr(moduleFile, moduleName):
            raise ModuleLoadingError(
                f"""File {path} is not a valid mbus module"""
            )

        module = getattr(moduleFile, moduleName)
        self.loadModule(module)

    def __tryLoadFromQueue(self):
        while True:
            loadedModuleNames = set(self.__loadedModules.keys())
            requirementsNotMetCount = 0
            anyLoaded = False
            while len(self.__loadingQueue) > requirementsNotMetCount:
                nextModule = self.__loadingQueue.pop()

                requirementsMet = len(
                    nextModule.dependencies
                ) == 0 or nextModule.dependencies.issubset(loadedModuleNames)

                if not requirementsMet:
                    self.__loadingQueue.add(nextModule)
                    requirementsNotMetCount += 1
                    continue

                self.__loadModule(nextModule)
                anyLoaded = True

            if not anyLoaded:
                break

    def __loadModule(self, module: type[mbusModule]):
        if module.name in self.__loadedModules:
            raise ModuleLoadingError(
                f"""Module <{module.name}> is already loaded"""
            )
        moduleConfig = self.__config.get(module.name, None)
        isDisabled = moduleConfig is not None and moduleConfig.get(
            "disabled", False
        )
        if isDisabled:
            self.__logger.warning(
                f"Not loading {module.name} as it is disabled"
            )
            return

        moduleInstance = module(
            self,
            config=moduleConfig,
            createGroup=lambda groupName: self.__createGroup(
                moduleInstance, groupName
            ),
            createEndpoint=lambda endpointName, **kwargs: self.__createEndpoint(
                moduleInstance, endpointName, **kwargs
            ),
            callEvent=lambda address, *args, **kwargs: self.__callEvent(
                moduleInstance, address, *args, **kwargs
            ),
            callEventAsync=lambda address,
            *args,
            **kwargs: self.__callEventAsync(
                moduleInstance, address, *args, **kwargs
            ),
            setFieldValue=lambda address, value: self.__setValue(
                moduleInstance, address, value
            ),
            probe=lambda: {
                name: element.probe()
                for name, element in self.__bus[module.name].items()
            },
        )
        self.__loadedModules[module.name] = moduleInstance
        self.__bus[module.name] = dict()

        for dependency in module.dependencies:
            if dependency not in self.__dependedOn:
                self.__dependedOn[dependency] = set()
            self.__dependedOn[dependency].add(module.name)

        moduleInstance.mbus = self
        moduleInstance.load()
        moduleInstance.is_loaded.set()

        self.__logger.info(f"Module <{module.name}> has been loaded")

        if module.name not in self.__onLoadCallbacks:
            return

        for onLoadCallback in self.__onLoadCallbacks[module.name]:
            try:
                onLoadCallback()
            except Exception as e:
                self.__logger.error("Error while executing load callback")
                self.__logger.exception(e)

    def __eventLoop(self):
        while True:
            nextEvent = self.__eventQueue.get()

            try:
                asyncio.run(self.__runEvent(nextEvent))
            except asyncio.TimeoutError:
                self.__logger.error(
                    f"Event call <{nextEvent.event.name}> timed out"
                )
            except Exception as e:
                self.__logger.error(
                    f"Error while calling event <{nextEvent.event.name}>"
                )
                self.__logger.exception(e)

    async def __runEvent(self, eventElement: EventQueueElement):
        coroutines = set()
        for responder in eventElement.event.getResponders():
            coroutines.add(responder(*eventElement.args, **eventElement.kwargs))

        await asyncio.wait_for(
            asyncio.gather(*coroutines),
            timeout=self.__eventTimeout,
        )

    def __createGroup(self, module: mbusModule, groupName: str):
        moduleGroups = self.__bus[module.name]
        return groupCreator(moduleGroups, module, groupName)

    def __createEndpoint(self, module: mbusModule, endpointName: str, **kwargs):
        moduleGroups = self.__bus[module.name]
        return endpointCreator(moduleGroups, module, endpointName, **kwargs)

    def __callEvent(self, module: mbusModule, address: str, *args, **kwargs):
        event = self.__getBusElement(module.name + "." + address)
        if not isinstance(event, busEvent):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a event"""
            )

        if event.owner is not module:
            raise EndpointeCallError(
                f"""Event <{address}> has been called not by owning module"""
            )

        self.__eventQueue.put(EventQueueElement(event, args, kwargs))

    async def __callEventAsync(
        self, module: mbusModule, address: str, *args, **kwargs
    ):
        return self.__callEvent(module, address, *args, **kwargs)

    def __setValue(self, module: mbusModule, address: str, value):
        field = self.__getBusElement(module.name + "." + address)
        if not isinstance(field, busField):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a field"""
            )

        if field.owner is not module:
            raise EndpointeCallError(
                f"""Field <{address}> has been set not by owning module"""
            )

        field.setValue(value)

    def isModuleLoaded(self, moduleName: str) -> bool:
        return moduleName in self.__loadedModules

    def unloadModule(self, moduleName: str):
        if not self.isModuleLoaded(moduleName):
            raise ModuleUnloadingError(
                f"""Module <{moduleName}> is not loaded"""
            )

        if moduleName in self.__dependedOn:
            self.__unloadDependencies(moduleName)
            del self.__dependedOn[moduleName]

        module = self.__loadedModules[moduleName]
        module.is_loaded.clear()
        module.unload()

        self.__logger.info(f"Module <{module.name}> has been unloaded")
        del self.__loadedModules[moduleName]
        del self.__bus[moduleName]

    def __unloadDependencies(self, moduleName: str):
        dependedOn = self.__dependedOn[moduleName]
        for dependedModuleName in dependedOn:
            if not self.isModuleLoaded(dependedModuleName):
                continue
            self.unloadModule(dependedModuleName)

    def unloadAll(self):
        modulesNames = set(self.__loadedModules.keys())
        for moduleName in modulesNames:
            if not self.isModuleLoaded(moduleName):
                continue
            self.unloadModule(moduleName)

    def addressExisits(self, address: str) -> bool:
        if len(address) == 0:
            return False

        start = self.__bus
        splited = address.split(".")
        for i, step in enumerate(splited):
            start = start.get(step, None)

            if isinstance(start, mbusEndpoint):
                return i + 1 == len(splited)

            if start is None:
                return False

        return True

    def __getBusElement(
        self, address: str
    ) -> Union["mBus", mbusModule, mbusGroup, mbusEndpoint]:
        splited = address.split(".")

        if len(address) == 0:
            return self

        if len(splited) == 1:
            module = self.__loadedModules.get(splited[0], None)
            if module is None:
                raise EndpointeCallError(f"""Address <{address}> not found""")
            return module

        currentElement = self.__bus

        for step in splited:
            if isinstance(currentElement, mbusEndpoint):
                raise EndpointeCallError(f"""Address <{address}> not found""")

            currentElement = currentElement.get(step, None)

            if currentElement is None:
                raise EndpointeCallError(f"""Address <{address}> not found""")

        return currentElement  # type: ignore

    def fireTrigger(self, address: str, *args, **kwargs) -> Any:
        trigger = self.__getBusElement(address)
        if not isinstance(trigger, busTrigger):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a trigger"""
            )

        return trigger.trigger(*args, **kwargs)

    async def fireTriggerAsync(self, address: str, *args, **kwargs) -> Any:
        return self.fireTrigger(address, *args, **kwargs)

    def addEventListener(
        self, address: str, listener: Callable[..., CoroutineType]
    ):
        event = self.__getBusElement(address)
        if not isinstance(event, busEvent):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a event"""
            )

        event.addEventListener(listener)

    def getValue(self, address: str) -> Any:
        field = self.__getBusElement(address)
        if not isinstance(field, busField):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a field"""
            )

        return field.getValue()

    def addFieldChangeCallback(self, address: str, callback: Callable):
        field = self.__getBusElement(address)
        if not isinstance(field, busField):
            raise EndpointeCallError(
                f"""Endpoint on address <{address}> is not a field"""
            )

        field.addOnChangeCallback(callback)

    def probe(self, deep=False):
        probed: dict[str, Any] = {
            "type": "mbus",
        }
        if deep:
            probed["elements"] = {
                m.name: m.probe() for m in self.__loadedModules.values()
            }

        return probed

    def getLoadedModules(self):
        return set(self.__loadedModules.keys())

    def probeAddress(self, address: str):
        return self.__getBusElement(address).probe(deep=True)

    def addLoadCallback(self, name, callback: Callable):
        if name in self.__loadedModules:
            callback()
            return

        if name not in self.__onLoadCallbacks:
            self.__onLoadCallbacks[name] = set()

        self.__onLoadCallbacks[name].add(callback)
