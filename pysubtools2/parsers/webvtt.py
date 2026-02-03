import collections
import enum
import typing

from .html_parsing import SubtitleHTMLTagParser

from ..subtitle.formatting import Formatting

from ..subtitle.time import Time
from ..subtitle.subtitle import Subtitle



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
        parts = timestamp.split(":", 2)
        if len(parts) < 2:
            return None
        
        h, m, sms = "0", "0", "0"
        if len(parts) == 2:
            [m, sms] = parts
        else:
            [h, m, sms] = parts
        [s, ms] = sms.split(".", 1)
        
        try:
            hours = int(h)
            minutes = int(m)
            seconds = int(s)
            milliseconds = int(ms.split()[0])
            return Time.from_human_time(milliseconds, seconds, minutes, hours)
        except ValueError:
            return None
    
    def _parse_times(self, line: str) -> bool:
        parts = line.split("-->", 1)
        if len(parts) < 2:
            return False
        [start_str, end_str] = parts
        start = self._parse_timestamp(start_str.strip())
        end = self._parse_timestamp(end_str.strip())
        if start is None or end is None:
            return False
        
        self.start_time = start
        self.end_time = end
        return True
    
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
        
        positions: collections.defaultdict[str, typing.Optional[str]] = collections.defaultdict(None)
        for p in position_strings:
            try:
                [identifier, value] = p.split(":", 1)
                positions[identifier] = value
            except ValueError:
                pass
        
    
    def _parse_content(self, line: str):
        raise NotImplementedError()
    
    def parse_text(self, vtt_text: str) -> Subtitle:
        raise NotImplementedError()