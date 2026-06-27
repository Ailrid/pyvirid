"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from dataclasses import dataclass
from virid.core import (
    create_virid,
    SingleMessage,
    EventMessage,
    system,
    component,
    MessageWriter,
    ViridApp,
)

# This example demonstrates the basic usage of CCS architecture
app = create_virid()


@component()
@dataclass
class Counter:
    value: int = 0

# Statically bind a composite,
# in which case the virid will be responsible for constructing the global singleton component for you,
# but in this case the Counter cannot have the necessary constructor parameters
app.bind(Counter)


# Here we demonstrate three uses, namely SingleMessage that can be merged, EventMessage that cannot be merged
# And how to carry data in messages
class IncreaseMessage(SingleMessage): ...


class DecreaseMessage(EventMessage): ...


@dataclass
class SetValueMessage(SingleMessage):
    value: int


# If you don't need the content of the message
# you can directly use the messageClass parameter to specify it
@system(message_type=IncreaseMessage, priority=10)
def increment(counter: Counter) -> None:
    counter.value += 1
    MessageWriter.info(f"Increment: {counter.value}")


@system(message_type=DecreaseMessage)
def decrement(counter: Counter) -> None:
    counter.value -= 1
    MessageWriter.info(f"Decrement: {counter.value}")


# Alternatively, you can injection
@system(priority=100)
def set_value(message: SetValueMessage, counter: Counter) -> None:
    counter.value = message.value
    MessageWriter.info(f"Set Value: {counter.value}")


# Due to the parameter requirements for constructing this component, dynamic registration is necessary
@component()
@dataclass
class DynamicCounter:
    value: int

class DynamicBindMessage(EventMessage): ...

class PrintDynamicMessage(EventMessage): ...

@system(message_type=DynamicBindMessage)
def dynamic_bind(app: ViridApp, counter: Counter) -> None:
    # You can directly obtain viridApp to call the spwan method to delay the registration of component instances,
    # but it(DynamicCounter) can only be a global singleton
    # Through this method, you can register a component whose constructor requires parameters
    app.spawn(DynamicCounter(counter.value))
    print("Dynamic Counter Created")


@system(message_type=PrintDynamicMessage)
def use_dynamic_counter(dynamic_counter: DynamicCounter) -> None:
    # If the system is called before registration, it will cause an error, like those
    # ✖ [Virid Error] Global Error Caught:
    # Details: [Virid Container] Unbound: No binding found for DynamicCounter
    # Context: [virid Dispatcher]: System Error.
    # SystemName: use_dynamic_counter
    # MessageName: PrintDynamicMessage
    # MessageData: PrintDynamicMessage()

    print(f"Dynamic Counter Value: {dynamic_counter.value}")


app.register(increment)
app.register(decrement)
app.register(set_value)
app.register(dynamic_bind)
app.register(use_dynamic_counter)

# Due to inheriting from SingleMessage, these two messages will be merged within a micro task queue
IncreaseMessage.send()
IncreaseMessage.send()
# Due to inheriting from EventMessage, decay will be executed twice
DecreaseMessage.send()
# Alternatively, you can directly use a Message Writer to send messages
MessageWriter.write(DecreaseMessage())
# The priority of this function is 100, so in terms of priority, setValue will be executed first
# When the constructor in the message has parameters, you can directly fill them into the. send method
SetValueMessage.send(1000)
# In the end, the order of system execution is: setValue ->increase ->decrease ->decrease
# The final count is 0->1000->1001->1000->999

DynamicBindMessage.send()
PrintDynamicMessage.send()
app.tick()


# The final output is those.
# Why does "Dynamic Counter" print earlier than Virid Info?
# Because we used MessageWriter.info for printing,
# Message Writer.info is only executed after the current micro tick ends
# What is tick and what is micro tick?
# Basically, a tick refers to the entire process from a message triggering system execution until all cascading messages are executed
# The new messages sent in a micro tick system will trigger another micro tick
# Message Writer. info actually sends an InfoMessage internally, so these contents will be postponed to the next micro tick execution.
# Therefore, the definition of micro tick is recursive, and the source of recursion is all messages sent before app.tick ()
# @system(message_type=IncreaseMessage, priority=10)
# def increment(counter: Counter) -> None:
#     counter.value += 1
#     MessageWriter.info(f"Increment: {counter.value}")


# Dynamic Counter Created
# Dynamic Counter Value: 999
#  ✔ [Virid Info] Global Info Caught:
#   Details: Set Value: 1000
#  ✔ [Virid Info] Global Info Caught:
#   Details: Increment: 1001
#  ✔ [Virid Info] Global Info Caught:
#   Details: Decrement: 1000
#  ✔ [Virid Info] Global Info Caught:
#   Details: Decrement: 999
