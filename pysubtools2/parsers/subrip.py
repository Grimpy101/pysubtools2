import dataclasses
import enum
import html
import html.parser
import io
import os
import typing
import re

from ..subtitle.formatting import (
    Bold,
    Color,
    FontFace,
    Formatting,
    Italic,
    PositionClassifier,
    Span,
    Strikethrough,
    TextSize,
    Underline,
    AbsolutePosition,
    RelativePosition,
)
from ..utils import get_file_encoding
from ..subtitle.subtitle import Subtitle, SubtitleUnit, Time

VALID_HTML_TAGS = ["b", "i", "u", "s", "font"]
HTML_FORMATTING_FACTORIES = {"b": Bold, "i": Italic, "u": Underline, "s": Strikethrough}
SSA_TAG_REGEX = re.compile(r"{\\*([\S:][\S]+)}")


class SubRipParseException(Exception):
    pass


@dataclasses.dataclass()
class TagSpan:
    """
    A helper data class for tracking parsed HTML tags in SubtitleTagParser
    """

    tag: str  # A tag label (e.g. 'b', 'i', 'u', 'font'...)
    attributes: typing.List[
        typing.Tuple[str, typing.Optional[str]]
    ]  # Attributes of the tag ('font' can have size, color, face)
    start: int  # Index in text where the starting tag is
    end: typing.Optional[int]  # Index in text where the closing tag is


class SubtitleHTMLTagParser(html.parser.HTMLParser):
    def __init__(self, *, convert_charrefs: bool = True) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.position: int = 0
        self.text: str = ""

        self.text_parts: typing.List[str] = []
        self.stack: typing.List[TagSpan] = []
        self.spans: typing.List[TagSpan] = []
        self.formattings: typing.List[Formatting] = []

    def handle_starttag(
        self, tag: str, attrs: typing.List[typing.Tuple[str, typing.Optional[str]]]
    ) -> None:
        tag_span = TagSpan(tag, attrs, self.position, None)
        self.stack.append(tag_span)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                span = self.stack.pop(i)
                span.end = self.position
                self.spans.append(span)
                return

        # We return unmatched closing tags back into text
        tag_str = f"</{tag}>"
        self.position += len(tag_str)
        self.text_parts.append(tag_str)

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        self.position += len(data)

    def close(self) -> None:
        super().close()

        # We close remaining open tags
        for span in self.stack:
            if span.tag in VALID_HTML_TAGS:
                span.end = self.position
            self.spans.append(span)

        self.text = "".join(self.text_parts)

        self.formattings = []
        invalid_tags: typing.List[typing.Tuple[int, str]] = []

        for span in self.spans:
            if span.end is None:
                # Unclosed un-recognized tags are treated as invalid
                start_tag = self._build_start_tag(span.tag, span.attributes)
                invalid_tags.append((span.start, start_tag))
            else:
                formattings = self._init_valid_formatting(
                    span.tag, span.attributes, span.start, span.end
                )
                if formattings:
                    self.formattings.extend(formattings)

        # We put invalid tags back into the text
        for position, tag in sorted(invalid_tags, reverse=True):
            tag_length = len(tag)
            self.text = self.text[:position] + tag + self.text[position:]

            # Update indices of affected formatting spans
            for formatting in self.formattings:
                if isinstance(formatting, Span):
                    if formatting.start >= position:
                        formatting.start += tag_length
                        formatting.end += tag_length
                    elif formatting.end >= position:
                        formatting.end += tag_length

    def clear(self) -> None:
        self.position = 0
        self.text = ""

        self.text_parts = []
        self.stack = []
        self.spans = []
        self.formattings = []

    def get_text(self) -> str:
        return self.text

    def get_formattings(self) -> typing.List[Formatting]:
        return self.formattings

    @staticmethod
    def _init_valid_formatting(
        tag: str,
        attributes: typing.List[typing.Tuple[str, typing.Optional[str]]],
        start: int,
        end: int,
    ) -> typing.List[Formatting]:
        if tag == "font":
            font = SubtitleHTMLTagParser._font_from_attributes(attributes, start, end)
            return font
        else:
            factory = HTML_FORMATTING_FACTORIES.get(tag)
            if factory:
                return [factory(start, end)]
        return []

    @staticmethod
    def _font_from_attributes(
        attributes: typing.List[typing.Tuple[str, typing.Optional[str]]],
        start: int,
        end: int,
    ) -> typing.List[Formatting]:
        formattings: typing.List[Formatting] = []
        for key, value in attributes:
            if not value:
                continue
            key = key.lower()
            if key == "color":
                color = Color.from_string(start, end, value)
                if color:
                    formattings.append(color)
            elif key == "face":
                face = FontFace(start, end, value)
                formattings.append(face)
            elif key == "size":
                try:
                    size = TextSize(start, end, int(value))
                    formattings.append(size)
                except ValueError:
                    pass
        return formattings

    @staticmethod
    def _build_start_tag(
        tag: str, attributes: typing.List[typing.Tuple[str, typing.Optional[str]]]
    ) -> str:
        output = f"<{tag}"
        for attr in attributes:
            if attr[1] is not None:
                output += f' {attr[0]}="{attr[1]}"'
            else:
                output += f" {attr[0]}"
        output += ">"
        return output


class SubtitleSSATagParser:
    def __init__(self) -> None:
        self.text: str = ""
        self.position: typing.Optional[RelativePosition] = None

    def handle_tag(self, tag: str) -> None:
        try:
            index = int(tag.replace("an", ""))
            # We always take only the first position tag
            if self.position is None:
                self.position = RelativePosition(PositionClassifier(index))
        except ValueError as e:
            print(e)
            pass

        # Remove tag from the text
        self.text = self.text.replace("{" + tag + "}", "")

    def feed(self, text: str) -> None:
        for match in SSA_TAG_REGEX.finditer(text):
            tag = match.group(1)
            if tag.startswith("an") and tag[2:].isdigit():
                self.handle_tag(tag)
        self.text = SSA_TAG_REGEX.sub("", text)

    def clear(self) -> None:
        self.text = ""
        self.position = None

    def get_text(self) -> str:
        return self.text

    def get_position(self) -> typing.Optional[RelativePosition]:
        return self.position


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

        self.html_parser = SubtitleHTMLTagParser()
        self.ssa_parser = SubtitleSSATagParser()

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
        #tail = line.rsplit("  ", 1)[-1]
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

        if None in (x1, x2, y1, y2):
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
        #times = self._parse_times(line)
        
        timestamps = line.split("-->", 1)
        if len(timestamps) < 2:
            return
        
        [start_timestamp, end_timestamp] = timestamps
        self.start_time = SubRipParser._parse_timestamp(start_timestamp)
        self.end_time = SubRipParser._parse_timestamp(end_timestamp)
        
        upper_end_timestamp = end_timestamp.upper()
        if 'X' in upper_end_timestamp:
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
        file: typing.Union[str, os.PathLike, typing.IO],
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
