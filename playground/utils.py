from typing import Any, List


def find_pyobjc_method(obj: Any, text: str) -> List[str]:
    return [m for m in dir(obj) if text in m]
