import enum
import html
import html.parser
import typing

from ..subtitle.formatting import Formatting

from ..subtitle.time import Time
from ..subtitle.subtitle import Subtitle


class VTTHTMLTagParser(html.parser.HTMLParser):
    pass


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
        
        self.html_parser = VTTHTMLTagParser()
    
    def _parse_header(self, line: str):
        raise NotImplementedError()
    
    @staticmethod
    def _parse_timestamp(timestamp: str) -> Time:
        raise NotImplementedError()
    
    def _parse_times(self, line: str) -> typing.Optional[typing.Tuple[Time, Time]]:
        raise NotImplementedError()
    
    def _parse_content(self, line: str):
        raise NotImplementedError()
    
    def parse_text(self, vtt_text: str) -> Subtitle:
        raise NotImplementedError()