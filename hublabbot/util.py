"""Module for utility functions, types, etc."""
from typing import Any, Dict
import re


JsonDict = Dict[str, Any]
"""Type - JSON dict."""
RE_ANSI_ESCAPE = r'\x1B[@-_][0-?]*[ -/]*[@-~]'
"""Regular expression for ANSI escape codes."""


def filter_out_ansi_escape(string: str) -> str:
	"""Filter out ANSI escape codes."""
	return re.sub(RE_ANSI_ESCAPE, '', string)


def set_frozen_attr(obj: object, attr: str, val: Any) -> None:
	"""Assign value to attribute in frozen dataclass."""
	object.__setattr__(obj, attr, val)
