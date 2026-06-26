"""
Copyright (c) 2026-present Ailrid.
Licensed under the Apache License, Version 2.0.
Project: Virid
"""

import inspect

from typing import Any, Callable, Type, Optional, get_origin, get_args

from ..core.interface import SystemContext
from ..core.message import BaseMessage
from ..core.io import MessageWriter


def system(
    message_type: Optional[Type[BaseMessage]] = None,
    priority: int = 0,
    singleton: bool = True,
):
    """
    系统装饰器
    :param message_type: 监听的消息类型 (可选，如果不传会自动从参数的类型注解推断)
    :param priority: 优先级，数值越大越早执行
    :param singleton: 是否为单例模式。True 传入单条消息；False 传入整个消息列表
    """

    # 提前校验 decorator 参数
    if message_type is not None and not (
        isinstance(message_type, type) and issubclass(message_type, BaseMessage)
    ):
        raise TypeError(
            f"[Virid System] TypeError: @System requires a subclass of BaseMessage, got: {message_type}"
        )

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if not params:
            raise ValueError(
                f"[Virid System] Parameter Loss: '{func.__name__}' must have at least one parameter for receiving messages!"
            )

        # 支持泛型解包的参数解析器
        msg_param_name = None
        inferred_msg_type = None
        message_idx = None

        for idx, param in enumerate(params):
            annotation = param.annotation
            if not annotation or annotation == inspect.Parameter.empty:
                continue

            target_type = None
            origin = get_origin(annotation)

            # 如果是泛型列表（如 list[DecreaseMessage] 或 List[DecreaseMessage]）
            if origin is list:
                args = get_args(annotation)
                if (
                    args
                    and isinstance(args[0], type)
                    and issubclass(args[0], BaseMessage)
                ):
                    target_type = args[0]  # 提取出里面的 DecreaseMessage 真实类型
                    message_idx = idx

            # 普通类型
            elif isinstance(annotation, type) and issubclass(annotation, BaseMessage):
                target_type = annotation
                message_idx = idx

            # 如果找到了消息参数
            if target_type is not None:
                if msg_param_name is not None:
                    raise ValueError(
                        f"[Virid System] Multiple Messages: '{func.__name__}' cannot have multiple BaseMessage parameters."
                    )
                msg_param_name = param.name
                inferred_msg_type = target_type

        # 确定最终的消息类型 (装饰器明确指定优先 > 参数类型推断)
        final_message_type = message_type or inferred_msg_type

        if final_message_type is None:
            raise ValueError(
                f"[Virid System] Parameter Loss: Cannot infer message type for '{func.__name__}'. "
                f"Declare via @System(MyMessage) or type hint (e.g., def my_system(msg: MyMessage):)."
            )

        # 运行时警告：类型冲突
        if (
            message_type
            and inferred_msg_type
            and not issubclass(inferred_msg_type, message_type)
        ):
            MessageWriter.warn(
                f"[virid System] Type Mismatch in '{func.__name__}': Decorator expects {message_type.__name__}, "
                f"but parameter expects {inferred_msg_type.__name__}."
            )

        # 给包装后的函数挂载上下文信息
        func.system_context: SystemContext = {  # type: ignore
            "params": [p.annotation for p in params],
            "message_type": final_message_type,
            "method_name": func.__name__,
            "original_method": func,
            "priority": priority,
        }
        func.system_config = {  # type: ignore
            "params": params,
            "message_type": final_message_type,
            "message_idx": message_idx,
            "priority": priority,
            "singleton": singleton,
        }

        return func

    return decorator


def component():
    def bind_component(cls):
        cls.__virid_component__ = True
        return cls

    return bind_component
