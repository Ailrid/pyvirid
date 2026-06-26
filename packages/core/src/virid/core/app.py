"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

from __future__ import annotations
from .core import Engine
from .container import Container
from typing import Type, Callable, TypeVar, overload, Any, Protocol
from .core.message import BaseMessage, EventMessage, SingleMessage
from .core.interface import TickHook, ExecuteHook, Middleware
from .core.io import MessageWriter
from functools import wraps


def handle_result(res: Any) -> None:
    """统一处理返回值，支持链式反应，平铺列表投递"""
    if res is None:
        return
    # 如果返回的是列表/元组，平铺处理
    messages = res if isinstance(res, (list, tuple)) else [res]

    for m in messages:
        if isinstance(m, BaseMessage):
            MessageWriter.write(m)
        else:
            MessageWriter.warn(
                f"[virid HandleResult] Invalid Return Type: Expected BaseMessage or List[BaseMessage], got {type(m).__name__}. Ignored."
            )


T = TypeVar("T")
F = TypeVar("F", bound=EventMessage, contravariant=True)
H = TypeVar("H", bound=SingleMessage, contravariant=True)
O = TypeVar("O", contravariant=True)


class ViridPlugin(Protocol[O]):
    name: str

    def install(self, app: ViridApp, options: O) -> None: ...


class ViridApp:
    def __init__(self, max_depth: int):
        self.engine = Engine(max_depth)
        self.container = Container()
        self.activate: list[Callable] = [lambda x: x]
        self.installed_plugins = set()

    def on_activate(self, activate: Callable, front: bool = False) -> None:
        if front:
            self.activate.insert(0, activate)
        else:
            self.activate.append(activate)

    def get(self, identifier: Type[T]) -> T:
        return self.container.get(identifier, self.activate)

    def bind(self, identifier, singleton=True):
        self.container.bind(identifier, singleton)

    def tick(self):
        self.engine.tick()

    # def register(
    #     self, message_class: Type[BaseMessage], system_fn: Callable, priority: int = 0
    # ):
    #     self.engine.register(message_class, system_fn, priority)

    def register(
        self,
        func: Callable,
    ):
        system_context = func.system_context  # type: ignore
        system_config = func.system_config  # type: ignore

        params = system_config["params"]
        final_message_type = system_config["message_type"]
        priority = system_config["priority"]
        singleton = system_config["singleton"]
        message_idx = system_config["message_idx"]
        # 闭包缓存变量
        is_initialized = False
        cached_components: list[Any] = [None] * len(params)

        # 根据 singleton 开关，精准重组参数负载
        def build_args(message: Any) -> list:
            """构建函数入参：将消息实体和可能存在的依赖注入按顺序排好"""
            nonlocal is_initialized, cached_components, message_idx

            is_incoming_list = isinstance(message, list)

            # 加工最终要塞给函数对应的参数负载
            if singleton:
                # 单例模式：函数只想要单条消息
                true_message = message[-1] if is_incoming_list else message

                # 运行时类型校验
                if not isinstance(true_message, final_message_type):
                    raise TypeError(
                        f"[virid System] Type Mismatch: Expected {final_message_type.__name__}, but received {type(true_message).__name__}"
                    )
                payload = true_message
            else:
                # 批处理模式：函数想要一个消息列表
                true_messages_list = message if is_incoming_list else [message]

                # 运行时对列表内的元素进行类型校验
                if true_messages_list and not isinstance(
                    true_messages_list[0], final_message_type
                ):
                    raise TypeError(
                        f"[virid System] Type Mismatch: Expected elements of {final_message_type.__name__}, but received {type(true_messages_list[0]).__name__}"
                    )
                payload = true_messages_list

            # 首次命中去容器捞取并缓存所有 Component 单例
            if not is_initialized:
                for idx, param in enumerate(params):
                    if idx != message_idx:
                        # 只有在第一次运行时，才去全局容器里捞
                        inject_instance = self.get(param.annotation)
                        if inject_instance is None:
                            raise RuntimeError(
                                f"[virid System] Unknown Inject Data Types: '{param.name}' ({param.annotation.__name__}) "
                                f"is not registered in the container for '{func.__name__}'!"
                            )
                        cached_components[idx] = inject_instance
                # 标记初始化完成
                is_initialized = True

            # 高频重组参数
            call_args = []
            for idx, param in enumerate(params):
                if idx == message_idx:
                    call_args.append(payload)
                else:
                    # 直接从闭包里的数组中拿
                    call_args.append(cached_components[idx])

            return call_args

        # 包装函数 (同步)
        def wrapped_system(message: EventMessage | list[SingleMessage]):
            # 动态组装参数
            call_args = build_args(message)
            result = func(*call_args)
            # 解析并处理返回值（支持链式反应）
            handle_result(result)

            return result

        wrapped_system.system_context = system_context  # type: ignore

        self.engine.register(final_message_type, wrapped_system, priority)

    def on_before_tick(self, hook: TickHook, front: bool = False):
        self.engine.on_before_tick(hook, front)

    def on_after_tick(self, hook: TickHook, front: bool = False):
        self.engine.on_after_tick(hook, front)

    @overload
    def on_before_execute(
        self,
        message_type: Type[F],
        hook: ExecuteHook[F],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_before_execute(
        self,
        message_type: Type[H],
        hook: ExecuteHook[list[H]],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_before_execute(
        self,
        message_type: Type[BaseMessage],
        hook: ExecuteHook[list[SingleMessage] | EventMessage],
        front: bool = False,
    ) -> None: ...

    def on_before_execute(
        self, message_type: Any, hook: Any, front: bool = False
    ) -> None:
        self.engine.on_before_execute(message_type, hook, front)

    @overload
    def on_after_execute(
        self,
        message_type: Type[F],
        hook: ExecuteHook[F],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_after_execute(
        self,
        message_type: Type[H],
        hook: ExecuteHook[list[H]],
        front: bool = False,
    ) -> None: ...

    @overload
    def on_after_execute(
        self,
        message_type: Type[BaseMessage],
        hook: ExecuteHook[list[SingleMessage] | EventMessage],
        front: bool = False,
    ) -> None: ...

    def on_after_execute(
        self, message_type: Any, hook: Any, front: bool = False
    ) -> None:
        self.engine.on_after_execute(message_type, hook, front)

    def use_middleware(self, middleware: Middleware):
        self.engine.use_middleware(middleware)

    def use(self, plugin: ViridPlugin[O], options: O) -> ViridApp:
        if plugin.name in self.installed_plugins:
            MessageWriter.warn(
                f"[Virid Plugin] Duplicate Installation: Plugin {plugin.name} has already been installed."
            )
            return self

        try:
            plugin.install(self, options)
            self.installed_plugins.add(plugin.name)
        except Exception as e:
            MessageWriter.error(
                e, f"[Virid Container] Activation Hook Failed: {plugin.name}"
            )

        return self
