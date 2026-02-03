import collections
import typing
import typing_extensions

from .formatting import Formatting, Span

from .time import Time


FormattingType = typing.TypeVar("FormattingType")


class SubtitleUnit:
    def __init__(
        self, start: Time, end: Time, text: str, formattings: typing.List[Formatting]
    ) -> None:
        self.start: Time = start
        self.end: Time = end
        self.text: str = text
        self.formattings: typing.List[Formatting] = formattings

    @property
    def duration(self) -> Time:
        return self.end - self.start

    def character_count(self, count_whitespace: bool = False) -> int:
        if not count_whitespace:
            return len("".join(self.text.split()))
        return len(self.text)

    def line_count(self) -> int:
        return len(self.text.splitlines())

    def overlaps(self, other: "SubtitleUnit") -> bool:
        return self.start <= other.end and other.start <= self.end

    def distance(self, other: "SubtitleUnit") -> Time:
        zero_time = Time(0)
        dist1 = max(zero_time, self.start - other.end)
        dist2 = max(zero_time, other.start - self.end)
        return dist1 + dist2

    def get_formatting_by_type(
        self, type: typing.Type[FormattingType]
    ) -> typing.Optional[FormattingType]:
        for formatting in self.formattings:
            if isinstance(formatting, type):
                return formatting
        return None

    def lines_of_formatting(self, formatting: Span) -> typing.List[int]:
        start = formatting.start
        end = formatting.end
        start_line = self.text.count("\n", None, start)
        end_line = start_line + self.text.count("\n", start, end)
        lines = list(range(start_line, end_line + 1))
        return lines
    
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'start': self.start.milliseconds,
            'end': self.end.milliseconds,
            'text': self.text,
            'formattings': [formatting.to_json() for formatting in self.formattings]
        }

    def __unicode__(self) -> str:
        return f"SubtitleUnit[{self.start}][{self.end}][{self.text}]"

    @typing_extensions.override
    def __str__(self) -> str:
        return self.__unicode__()


if typing.TYPE_CHECKING:
    SubtitleList = collections.UserList[SubtitleUnit]
else:
    SubtitleList = collections.UserList


class Subtitle(SubtitleList):
    def to_json(self) -> typing.List[typing.Dict[str, typing.Any]]:
        return [unit.to_json() for unit in self]
    
    def __unicode__(self) -> str:
        return f"Subtitle ({len(self.data)} units)"

    @typing_extensions.override
    def __str__(self) -> str:
        return self.__unicode__()
