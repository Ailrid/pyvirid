"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

import inspect
from typing import Type, TypeVar, Callable, Any
from dataclasses import is_dataclass, fields

T = TypeVar("T")


class Container:
    def __init__(self):
        self.bindings: dict[Type[Any], tuple[Type[Any], bool]] = {}
        self.singletons: dict[Type[Any], Any] = {}
        self.activate_hooks: list[Callable] = [lambda x: x]

    def add_activate_hook(self, activate: Callable, front: bool = False) -> None:
        if front:
            self.activate_hooks.insert(0, activate)
        else:
            self.activate_hooks.append(activate)

    def spawn(self, instance: object):
        """动态注册一个合适的组件实例，接受任何非基础数据类型"""
        # 检查构造函数，此identifier不可有必须传入的参数
        identifier = type(instance)
        # 检查是否已经存在
        if self.bindings.get(identifier, None) is not None:
            raise TypeError(
                f"[Virid Container] Invalid Component: The Class {identifier.__name__} has already been registered."
            )

        self.bindings[identifier] = (identifier, True)
        self.singletons[identifier] = instance

    def bind(self, identifier: Type[T]) -> None:
        """
        注册绑定。
        - to: 映射到的目标类。如果不传，默认绑定到自身（toSelf）
        - singleton: 是否为单例。默认为 False (transient)
        """
        # 检查构造函数，此identifier不可有必须传入的参数
        if self.has_required_init_params(identifier):
            raise TypeError(
                f"[Virid Container] Invalid Component Or Controller: The Class {identifier.__name__} has required parameters in its constructor."
            )

        if getattr(identifier, "__virid_component__", False) is True:  # type: ignore
            self.bindings[identifier] = (identifier, True)
        elif getattr(identifier, "__virid_controller__", False) is True:
            self.bindings[identifier] = (identifier, False)
        else:
            raise TypeError(
                f"[Virid Container] Invalid Component: The Class {identifier.__name__} whit not @Component or @Controller decorator."
            )

    def get(self, identifier: Type[T]) -> T:
        """获取实例，执行激活流水线"""
        if identifier not in self.bindings:
            raise RuntimeError(
                f"[Virid Container] Unbound: No binding found for {identifier.__name__}"
            )

        target_ctor, is_singleton = self.bindings[identifier]

        # 如果是单例
        if is_singleton:
            if identifier not in self.singletons:
                self.singletons[identifier] = self.activate(target_ctor())
            return self.singletons[identifier]

        # 如果是多例
        return self.activate(target_ctor())

    def activate(self, component: Any):
        result = component
        for hook in self.activate_hooks:
            result = hook(result)

        return result

    def has_required_init_params(self, cls: type) -> bool:
        """
        检查一个类（或 dataclass）的构造函数是否包含必填参数。
        如果包含至少一个必填参数，返回 True；否则返回 False。
        """

        if is_dataclass(cls):
            # dataclass 的字段如果没有指定 default 或 default_factory，就是必填的
            from dataclasses import MISSING

            for field in fields(cls):
                # init=False 的字段不需要在构造函数中传入
                if field.init and (
                    field.default is MISSING and field.default_factory is MISSING
                ):
                    return True
            return False

        # 使用 inspect 检查 __init__ 签名
        try:
            signature = inspect.signature(cls.__init__)
        except (ValueError, TypeError):
            return False

        for name, param in signature.parameters.items():
            # 排除 self, *args, **kwargs
            if name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            # 如果参数没有默认值（empty），说明它是必填的
            if param.default is inspect.Parameter.empty:
                return True

        return False
