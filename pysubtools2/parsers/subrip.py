import enum
import io
import os
import typing

from ..subtitle.formatting import (
    Formatting,
    AbsolutePosition,
)
from ..utils import get_file_encoding
from ..subtitle.subtitle import Subtitle, SubtitleUnit
from ..subtitle.time import Time
from .html_parsing import SubtitleHTMLTagParser
from .ssa_control_code_parsing import SubtitleSSATagParser


class SubRipParseException(Exception):
    pass


class SubRipParsingState(enum.Enum):
    INDEX = enum.auto()
    TIME = enum.auto()
    CONTENT = enum.auto()
    BETWEEN_SUBS = enum.auto()


class SubRipParser:
    def __init__(self) -> None:
        self.subtitle: Subtitle = Subtitle()
        self.state: SubRipParsingState = SubRipParsingState.INDEX

        self.start_time: typing.Optional[Time] = None
        self.end_time: typing.Optional[Time] = None

        self.formattings: typing.List[Formatting] = []

        self.raw_text: str = ""
        self.temp_text: str = ""

        self.html_parser: SubtitleHTMLTagParser = SubtitleHTMLTagParser()
        self.ssa_parser: SubtitleSSATagParser = SubtitleSSATagParser()

    @staticmethod
    def _parse_index(line: str) -> typing.Optional[int]:
        try:
            index = int(line)
            return index
        except ValueError:
            return None

    @staticmethod
    def _parse_timestamp(timestamp: str) -> Time:
        h, m, sms = timestamp.split(":", 2)
        separator = "," if "," in sms else "."
        [s, ms] = sms.split(separator, 1)
        ms = ms[:3]
        hours = int(h)
        minutes = int(m)
        seconds = int(s)
        milliseconds = int(ms)
        return Time.from_human_time(milliseconds, seconds, minutes, hours)

    def _parse_absolute_position(self, line: str) -> typing.Optional[AbsolutePosition]:
        x1 = x2 = y1 = y2 = None
        # tail = line.rsplit("  ", 1)[-1]
        coordinates = line.split()
        for coordinate in coordinates:
            if ":" not in coordinate:
                continue

            label, value = coordinate.split(":", 1)
            if label == "X1":
                x1 = int(value)
            elif label == "X2":
                x2 = int(value)
            elif label == "Y1":
                y1 = int(value)
            elif label == "Y2":
                y2 = int(value)

        if x1 is None or x2 is None or y1 is None or y2 is None:
            return None

        self.formattings.append(AbsolutePosition(x1, x2, y1, y2))

    def _formatting_already_exists(self, formatting: Formatting) -> bool:
        for f in self.formattings:
            if isinstance(f, formatting.__class__):
                if f == formatting:
                    return True
        return False

    def _parse_unit_text(self, text: str) -> None:
        text = text.strip()
        self.ssa_parser.feed(text)
        relative_position = self.ssa_parser.get_position()
        if relative_position is not None and not self._formatting_already_exists(
            relative_position
        ):
            self.formattings.append(relative_position)
        text = self.ssa_parser.get_text()

        self.html_parser.feed(text)
        self.html_parser.close()
        self.formattings.extend(
            filter(
                lambda item: not self._formatting_already_exists(item),
                self.html_parser.formattings,
            )
        )
        text = self.html_parser.get_text()

        self.raw_text = text
        self.ssa_parser.clear()
        self.html_parser.clear()

    def _store_unit(self) -> None:
        self.raw_text += self.temp_text
        self._parse_unit_text(self.raw_text)
        if self.start_time and self.end_time:
            unit = SubtitleUnit(
                self.start_time, self.end_time, self.raw_text, list(self.formattings)
            )
            self.subtitle.append(unit)

        # Clean up so we don't have invalid data
        self.start_time = None
        self.end_time = None
        self.raw_text = ""
        self.temp_text = ""
        self.formattings = []

    def _on_index_state(self, line: str):
        index = self._parse_index(line)
        if index is not None:
            self.state = SubRipParsingState.TIME
            if self.start_time and self.end_time:
                self._store_unit()
        else:
            self.temp_text += line + "\n"

    def _on_time_state(self, line: str):
        # times = self._parse_times(line)

        timestamps = line.split("-->", 1)
        if len(timestamps) < 2:
            return

        [start_timestamp, end_timestamp] = timestamps
        self.start_time = SubRipParser._parse_timestamp(start_timestamp)
        self.end_time = SubRipParser._parse_timestamp(end_timestamp)

        upper_end_timestamp = end_timestamp.upper()
        if "X" in upper_end_timestamp:
            absolute_position = self._parse_absolute_position(upper_end_timestamp)
            if absolute_position is not None and not self._formatting_already_exists(
                absolute_position
            ):
                self.formattings.append(absolute_position)

        self.state = SubRipParsingState.CONTENT

    def _on_content_state(self, line: str):
        if len(line) == 0:
            self.temp_text = "\n"
            self.state = SubRipParsingState.INDEX
        else:
            self.raw_text += line + "\n"

    def parse_text(self, srt_text: str) -> Subtitle:
        srt_text = srt_text.replace("\ufeff", "")  # Remove BOM from UTF-8 text

        srt_lines = srt_text.splitlines()

        for line in srt_lines:
            line = line.strip()
            if self.state == SubRipParsingState.INDEX:
                self._on_index_state(line)
            elif self.state == SubRipParsingState.TIME:
                self._on_time_state(line)
            elif self.state == SubRipParsingState.CONTENT:
                self._on_content_state(line)

        if self.start_time and self.end_time:
            self._store_unit()

        return self.subtitle

    def parse_file(
        self,
        file: typing.Any,
        encoding: typing.Optional[str] = None,
    ) -> Subtitle:
        if isinstance(file, typing.BinaryIO):
            wrapper = io.TextIOWrapper(file)
            file_content = wrapper.read()

        elif isinstance(file, typing.TextIO):
            file_content = file.read()

        elif isinstance(file, (str, os.PathLike)):
            if encoding is None:
                encoding = get_file_encoding(file)
            with open(file, "r", encoding=encoding) as f:
                file_content = f.read()
        else:
            raise ValueError(f"Invalid argument for file: {file}")

        subtitle = self.parse_text(file_content)
        return subtitle
