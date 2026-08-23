"""Host-side implementation of the Nissan CONSULT diagnostic protocol."""

from .definition import ConsultDefinition, ParamID, ParamTableError
from .frames import FrameLayout, FrameParser, RegisterNotInHeaderError
from .params import BitParam, DualParam, ParamSpec, SingleParam
from .session import ConsultSession, InitializeFailedError
from .transport import CaptureTransport, SerialTransport, Transport

__version__ = "0.2.0"

__all__ = [
    "BitParam",
    "CaptureTransport",
    "ConsultDefinition",
    "ConsultSession",
    "DualParam",
    "FrameLayout",
    "FrameParser",
    "InitializeFailedError",
    "ParamID",
    "ParamSpec",
    "ParamTableError",
    "RegisterNotInHeaderError",
    "SerialTransport",
    "SingleParam",
    "Transport",
]
