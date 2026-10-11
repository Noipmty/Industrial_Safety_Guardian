"""Python 3.10 运行时兼容垫片。

项目运行环境为 Python 3.10，此处为 3.11+ 标准库能力提供等价实现。
"""

from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - 仅 Python 3.10 触发

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        """``enum.StrEnum``（Python 3.11+）的 3.10 等价实现。"""

        __slots__ = ()
