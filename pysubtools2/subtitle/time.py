import typing
import typing_extensions


class HumanTime(typing.TypedDict):
    hours: int
    minutes: int
    seconds: int
    milliseconds: int


class Time:
    """A class storing time information in milliseconds. Optionally also holds associated framerate for conversion from/to frames."""

    def __init__(self, milliseconds: int) -> None:
        self.milliseconds: int = milliseconds

    @property
    def human_time(self) -> HumanTime:
        milliseconds = self.milliseconds
        hours = milliseconds // 3600000
        milliseconds = milliseconds - (hours * 3600000)
        minutes = milliseconds // 60000
        milliseconds = milliseconds - (minutes * 60000)
        seconds = milliseconds // 1000
        milliseconds = milliseconds - (seconds * 1000)
        return {
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "milliseconds": milliseconds,
        }

    def to_frame(self, framerate: float) -> int:
        seconds = self.milliseconds / 1000
        frame = int(seconds * framerate)
        return frame

    @classmethod
    def from_human_time(
        cls, milliseconds: int, seconds: int = 0, minutes: int = 0, hours: int = 0
    ) -> "Time":
        milliseconds += hours * 3600000
        milliseconds += minutes * 60000
        milliseconds += seconds * 1000
        return cls(milliseconds)

    @classmethod
    def from_frame(cls, frame: int, framerate: float) -> "Time":
        seconds = frame / framerate
        milliseconds = int(seconds * 1000)
        time = cls.from_human_time(milliseconds)
        return time

    def __unicode__(self) -> str:
        return f"Time({self.milliseconds}ms)"

    @typing_extensions.override
    def __str__(self) -> str:
        return self.__unicode__()

    @typing_extensions.override
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Time):
            raise ValueError(f"Value {value} is not a valid time!")
        return self.milliseconds == value.milliseconds

    def __gt__(self, value: object) -> bool:
        if not isinstance(value, Time):
            raise ValueError(f"Value {value} is not a valid time!")
        return self.milliseconds > value.milliseconds

    def __lt__(self, value: object) -> bool:
        if not isinstance(value, Time):
            raise ValueError(f"Value {value} is not a valid time!")
        return self.milliseconds < value.milliseconds

    def __ge__(self, value: object) -> bool:
        if not isinstance(value, Time):
            raise ValueError(f"Value {value} is not a valid time!")
        return self.milliseconds >= value.milliseconds

    def __le__(self, value: object) -> bool:
        if not isinstance(value, Time):
            raise ValueError(f"Value {value} is not a valid time!")
        return self.milliseconds <= value.milliseconds

    def __add__(self, other: typing.Union[int, float, "Time"]) -> "Time":
        new_milliseconds = self.milliseconds
        if isinstance(other, (int, float)):
            new_milliseconds += int(other)
        elif isinstance(other, Time):
            new_milliseconds += other.milliseconds
        else:
            raise TypeError(f"Cannot add {self} and {other} together!")
        return Time(new_milliseconds)

    def __iadd__(self, other: typing.Union[int, float, "Time"]) -> "Time":
        if isinstance(other, (int, float)):
            self.milliseconds += int(other)
        elif isinstance(other, Time):
            self.milliseconds += other.milliseconds
        else:
            raise TypeError(f"Cannot add {self} and {other} together!")
        return self

    def __sub__(self, other: typing.Union[int, float, "Time"]) -> "Time":
        new_milliseconds = self.milliseconds
        if isinstance(other, (int, float)):
            new_milliseconds -= int(other)
        elif isinstance(other, Time):
            new_milliseconds -= other.milliseconds
        else:
            raise TypeError(f"Cannot subtract {other} from {self}!")

        # Time cannot be smaller than 0 milliseconds
        new_milliseconds = max(0, new_milliseconds)
        return Time(new_milliseconds)

    def __isub__(self, other: typing.Union[int, float, "Time"]) -> "Time":
        if isinstance(other, (int, float)):
            self.milliseconds -= int(other)
        elif isinstance(other, Time):
            self.milliseconds -= other.milliseconds
        else:
            raise TypeError(f"Cannot subtract {other} from {self}!")
        return self

    def __rsub__(self, other: typing.Union[int, float, "Time"]) -> "Time":
        new_milliseconds = self.milliseconds
        if isinstance(other, (int, float)):
            new_milliseconds = int(other) - new_milliseconds
        elif isinstance(other, Time):
            new_milliseconds = other.milliseconds - self.milliseconds
        else:
            raise TypeError(f"Cannot subtract {other} from {self}!")
        return Time(new_milliseconds)

    def __mul__(self, other: typing.Union[int, float]) -> "Time":
        if not isinstance(other, (int, float)):
            raise TypeError(f"Cannot multiply {self} and {other}!")
        new_milliseconds = int(self.milliseconds * other)
        return Time(new_milliseconds)

    def __imul__(self, other: typing.Union[int, float]) -> "Time":
        if not isinstance(other, (int, float)):
            raise TypeError(f"Cannot multiply {self} and {other}!")
        self.milliseconds = int(self.milliseconds * other)
        return self

    __radd__ = __add__
    __rmul__ = __mul__
