import collections
import enum
import io
import os
import typing

from ..utils import get_file_encoding

from .html_parsing import SubtitleHTMLTagParser

from ..subtitle.formatting import Formatting

from ..subtitle.time import Time
from ..subtitle.subtitle import Subtitle, SubtitleUnit


class WebVTTParsingState(enum.Enum):
    HEADER = enum.auto()
    TIME = enum.auto()
    CONTENT = enum.auto()
    BETWEEN_SUBS = enum.auto()


class WebVTTParser:
    def __init__(self) -> None:
        self.subtitle: Subtitle = Subtitle()
        self.state: WebVTTParsingState = WebVTTParsingState.HEADER

        self.start_time: typing.Optional[Time] = None
        self.end_time: typing.Optional[Time] = None

        self.formattings: typing.List[Formatting] = []

        self.raw_text: str = ""
        self.temp_text: str = ""

        self.html_parser: SubtitleHTMLTagParser = SubtitleHTMLTagParser()

    @staticmethod
    def _parse_timestamp(timestamp: str) -> typing.Optional[Time]:
        parts = timestamp.split(":")
        h, m, sms = "0", "0", "0.0"
        if len(parts) > 2:
            h = parts[0]
            m = parts[1]
            sms = parts[2]
        elif len(parts) > 1:
            h = 0
            m = parts[0]
            sms = parts[1]
        
        sms_parts = sms.split(".", 1)
        if len(sms_parts) > 1:
            s = sms_parts[0]
            ms = sms_parts[1]
        else:
            s = sms_parts[0]
            ms = "0"
        try:
            hours = int(h)
            minutes = int(m)
            seconds = int(s)
            milliseconds = int(ms.split()[0])
            return Time.from_human_time(milliseconds, seconds, minutes, hours)
        except ValueError:
            return None

    @staticmethod
    def _parse_times(line: str) -> typing.Optional[typing.Tuple[Time, Time]]:
        parts = line.split(" --> ", 1)
        if len(parts) < 2:
            return None
        [start_str, end_str] = parts
        end_str = end_str.strip().split()[0]
        start = WebVTTParser._parse_timestamp(start_str.strip())
        end = WebVTTParser._parse_timestamp(end_str.strip())
        if start is None or end is None:
            return None
        return (start, end)

    @staticmethod
    def _parse_line_position(value: str):
        value = value.strip()
        try:
            position_val = int(value.removesuffix("%"))
            if value.endswith("%"):
                ranges = [0, 33, 66]
            else:
                ranges = [0, 10, 20]
            if ranges[0] <= position_val < ranges[1]:
                return 0
            elif ranges[1] <= position_val < ranges[2]:
                return 1
            else:
                return 2
        except ValueError:
            return None

    @staticmethod
    def _parse_position_position(value: str):
        value = value.removesuffix("%")
        try:
            pos = int(value)
            if 0 <= pos < 33:
                return 0
            elif 33 <= pos < 66:
                return 1
            else:
                return 2
        except ValueError:
            return None

    def _parse_positions(self, line: str):
        parts = line.split("-->", 1)
        if len(parts) < 2:
            return
        end_str = parts[1]
        position_strings = end_str.split()[1:]

        positions: collections.defaultdict[str, typing.Optional[str]] = (
            collections.defaultdict(None)
        )
        for p in position_strings:
            try:
                [identifier, value] = p.split(":", 1)
                positions[identifier] = value
            except ValueError:
                pass
    
    def _formatting_already_exists(self, formatting: Formatting) -> bool:
        for f in self.formattings:
            if isinstance(f, formatting.__class__):
                if f == formatting:
                    return True
        return False

    def _parse_content(self, text: str):
        text = text.strip()
        self.html_parser.feed(text)
        self.html_parser.close()
        self.formattings.extend(
            filter(
                lambda item: not self._formatting_already_exists(item),
                self.html_parser.formattings
            )
        )
        text = self.html_parser.get_text()
        self.raw_text = text
        self.html_parser.clear()
    
    def _store_unit(self):
        if self.start_time and self.end_time:
            self.raw_text += self.temp_text
            self._parse_content(self.raw_text)
            unit = SubtitleUnit(
                self.start_time, self.end_time, self.raw_text, self.formattings
            )
            self.subtitle.append(unit)
        self.start_time = None
        self.end_time = None
        self.raw_text = ""
        self.temp_text = ""
        self.formattings = []
    
    def parse_text(self, vtt_text: str) -> Subtitle:
        vtt_text = vtt_text.replace("\ufeff", "")  # Remove BOM from UTF-8 text
        vtt_lines = vtt_text.splitlines()
        
        for line in vtt_lines:
            line = line.strip()
            if line.startswith("NOTE"):
                continue
            
            times = self._parse_times(line)
            if times is not None:
                self.temp_text = "\n".join(self.temp_text.split("\n")[:-1]) # Remove header
                self._store_unit()
                
                self.start_time = times[0]
                self.end_time = times[1]
                continue
            
            self.temp_text = self.temp_text + "\n" + line
        
        if self.start_time and self.end_time:
            self._store_unit()
        
        return self.subtitle
    
    def parse_file(
        self,
        file: typing.Any,
        encoding: typing.Optional[str] = None
    ):
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