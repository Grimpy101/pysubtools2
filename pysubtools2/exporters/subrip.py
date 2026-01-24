import collections
import typing

from ..subtitle.time import Time
from ..subtitle.subtitle import Subtitle, SubtitleUnit
from ..subtitle.formatting import (
    AbsolutePosition,
    Bold,
    Color,
    FontFace,
    HTMLTag,
    Italic,
    RelativePosition,
    Strikethrough,
    TextSize,
    Underline,
)


FORMATTING_PRIORITIES: typing.Dict[typing.Type[HTMLTag], int] = {
    TextSize: 0,
    FontFace: 1,
    Color: 2,
    Bold: 3,
    Italic: 4,
    Underline: 5,
    Strikethrough: 6,
}

HTML_TAG_MAPS = {Bold: "b", Italic: "i", Underline: "u", Strikethrough: "s"}


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
    def _construct_content_line(subtitle_unit: SubtitleUnit) -> str:
        text = subtitle_unit.text

        formattings: typing.List[HTMLTag] = list(
            filter(lambda item: isinstance(item, HTMLTag), subtitle_unit.formattings)
        )  # type: ignore

        font_formattings = filter(
            lambda element: isinstance(element, (Color, FontFace, TextSize)),
            formattings,
        )
        other_formattings = filter(
            lambda element: not isinstance(element, (Color, FontFace, TextSize)),
            formattings,
        )

        font_groups: typing.DefaultDict[
            typing.Tuple[int, int], typing.List[HTMLTag]
        ] = collections.defaultdict(list)
        for font in font_formattings:
            font_groups[(font.start, font.end)].append(font)

        html_tags: typing.List[TagSpan] = []
        for formatting in other_formattings:
            html_tags.append(
                {
                    "tag": formatting.get_html_tag("start"),
                    "index": formatting.start,
                    "priority": FORMATTING_PRIORITIES.get(formatting.__class__, 0),
                }
            )
            html_tags.append(
                {
                    "tag": formatting.get_html_tag("end"),
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
        lines = []

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
        self, target: typing.IO, subtitle: Subtitle, encoding: str = "utf-8"
    ) -> None:
        output = self.to_string(subtitle)
        if hasattr(target, "encoding"):
            typing.cast(typing.TextIO, target).write(output)
        else:
            typing.cast(typing.BinaryIO, target).write(output.encode(encoding))
