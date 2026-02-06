import collections
import typing

from ..subtitle.time import Time
from ..subtitle.subtitle import Subtitle, SubtitleUnit
from ..subtitle.formatting import (
    AbsolutePosition,
    Bold,
    Color,
    FontFace,
    Formatting,
    Italic,
    Position,
    RelativePosition,
    Strikethrough,
    TextSize,
    Underline,
)


FORMATTING_PRIORITIES: typing.Dict[typing.Type[Formatting], int] = {
    TextSize: 0,
    FontFace: 1,
    Color: 2,
    Bold: 3,
    Italic: 4,
    Underline: 5,
    Strikethrough: 6,
}

HTML_TAG_MAPS: typing.Dict[typing.Type[Formatting], str] = {Bold: "b", Italic: "i", Underline: "u", Strikethrough: "s"}

FORMATTING_HTML_TAGS: typing.Dict[typing.Type[Formatting], str] = {
    Bold: "b",
    Italic: "i",
    Underline: "u",
    Strikethrough: "s",
    TextSize: "font",
    FontFace: "font",
    Color: "font"
}


class TagSpan(typing.TypedDict):
    tag: str
    index: int
    priority: int


class SubRipExporter:
    @staticmethod
    def _construct_index_line(i: int) -> str:
        return str(i)

    @staticmethod
    def _time_to_string(time: Time) -> str:
        human_time = time.human_time
        hours = human_time["hours"]
        minutes = human_time["minutes"]
        seconds = human_time["seconds"]
        millis = human_time["milliseconds"]
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    @staticmethod
    def _construct_time_line(subtitle_unit: SubtitleUnit) -> str:
        start_time = subtitle_unit.start
        end_time = subtitle_unit.end
        absolute_position = subtitle_unit.get_formatting_by_type(AbsolutePosition)

        start_timestamp = SubRipExporter._time_to_string(start_time)
        end_timestamp = SubRipExporter._time_to_string(end_time)

        output = f"{start_timestamp} --> {end_timestamp}"
        if absolute_position:
            output += f"  X1:{absolute_position.x1:03} X2:{absolute_position.x2:03} Y1:{absolute_position.y1:03} Y2:{absolute_position.y2:03}"
        return output
    
    @staticmethod
    def _to_html_tag(formatting: Formatting):
        tag = FORMATTING_HTML_TAGS.get(formatting.__class__)
        attributes: typing.List[str] = []
        if tag is None:
            return None
        
        if isinstance(formatting, FontFace):
            attributes.append(f'face="{formatting.face}"')
        elif isinstance(formatting, TextSize):
            attributes.append(f'size={formatting.size}')
        elif isinstance(formatting, Color):
            attributes.append(f'color="{formatting.to_hex()}"')
        return {
            'tag': tag,
            'attributes': attributes,
            'start': formatting.start,
            'end': formatting.end
        }
    
    @staticmethod
    def _to_ass_tag(formatting: Formatting):
        if isinstance(formatting, RelativePosition):
            return {
                'code': 'an',
                'value': formatting.classifier.value
            }

    @staticmethod
    def _a(subtitle_unit: SubtitleUnit) -> str:
        text = subtitle_unit.text

        html_tags = collections.defaultdict(set)
        ass_tags = {}
        
        for formatting in subtitle_unit.formattings:
            attribs = SubRipExporter._to_html_tag(formatting)
            if attribs is None:
                continue
            html_tags[(attribs['tag'], attribs['start'], attribs['end'])].add(attribs['attributes'])
        
        for formatting in subtitle_unit.formattings:
            attribs = SubRipExporter._to_ass_tag(formatting)
            if attribs is None:
                continue
            ass_tags[attribs['code']] = attribs['value']
        
        

    @staticmethod
    def _construct_content_line(subtitle_unit: SubtitleUnit) -> str:
        text = subtitle_unit.text

        formattings: typing.List[Formatting] = list(
            filter(lambda item: not isinstance(item, Position), subtitle_unit.formattings)
        )

        font_formattings = filter(
            lambda element: isinstance(element, (Color, FontFace, TextSize)),
            formattings,
        )
        other_formattings = filter(
            lambda element: not isinstance(element, (Color, FontFace, TextSize)),
            formattings,
        )

        font_groups: typing.DefaultDict[
            typing.Tuple[int, int], typing.List[Formatting]
        ] = collections.defaultdict(list)

        for font in font_formattings:
            font_groups[(font.start, font.end)].append(font)

        html_tags: typing.List[TagSpan] = []
        for formatting in other_formattings:
            if isinstance(formatting, (*HTML_TAG_MAPS.keys(),)):
                continue

            html_tags.append(
                {
                    "tag": f"<{HTML_TAG_MAPS[formatting.__class__]}>",
                    "index": formatting.start,
                    "priority": FORMATTING_PRIORITIES.get(formatting.__class__, 0),
                }
            )
            html_tags.append(
                {
                    "tag": f"</{HTML_TAG_MAPS[formatting.__class__]}>",
                    "index": formatting.end,
                    "priority": len(FORMATTING_PRIORITIES)
                    - FORMATTING_PRIORITIES.get(formatting.__class__, 0),
                }
            )

        for (start, end), group in font_groups.items():
            group.sort(key=lambda e: e.get_attributes())
            start_tag = "<font"
            for element in group:
                start_tag += " " + element.get_attributes()
            start_tag += ">"

            html_tags.append({"tag": start_tag, "index": start, "priority": 0})
            html_tags.append(
                {"tag": "</font>", "index": end, "priority": len(FORMATTING_PRIORITIES)}
            )

        html_tags.sort(key=lambda item: (item["index"], item["priority"]))

        for tag in reversed(html_tags):
            tag_text = tag["tag"]
            index = tag["index"]
            text = text[:index] + tag_text + text[index:]

        position = subtitle_unit.get_formatting_by_type(RelativePosition)
        if position:
            position_id = position.classifier.value
            text = f"{{\\an{position_id}}}" + text
        return text

    def to_string(self, subtitle: Subtitle) -> str:
        lines: typing.List[str] = []

        subtitle.sort(key=lambda unit: unit.start)

        for i, subtitle_unit in enumerate(subtitle):
            index_line = self._construct_index_line(i + 1)
            time_line = self._construct_time_line(subtitle_unit)
            content_line = self._construct_content_line(subtitle_unit)
            lines.append(index_line)
            lines.append(time_line)
            lines.append(content_line)
            lines.append("")

        output = "\n".join(lines)
        return output

    def to_file(
        self,
        target: typing.Union[typing.IO[str], typing.IO[bytes]],
        subtitle: Subtitle,
        encoding: str = "utf-8",
    ) -> None:
        output = self.to_string(subtitle)
        if hasattr(target, "encoding"):
            _ = typing.cast(typing.TextIO, target).write(output)
        else:
            _ = typing.cast(typing.BinaryIO, target).write(output.encode(encoding))
