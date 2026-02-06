import dataclasses
import html.parser
import typing
import typing_extensions

from ..subtitle.formatting import (
    Bold,
    Color,
    FontFace,
    Formatting,
    Italic,
    Strikethrough,
    TextSize,
    Underline,
)


VALID_HTML_TAGS = ["b", "i", "u", "s", "font"]
HTML_FORMATTING_FACTORIES = {"b": Bold, "i": Italic, "u": Underline, "s": Strikethrough}


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

    @typing_extensions.override
    def handle_starttag(
        self, tag: str, attrs: typing.List[typing.Tuple[str, typing.Optional[str]]]
    ) -> None:
        tag_span = TagSpan(tag, attrs, self.position, None)
        self.stack.append(tag_span)

    @typing_extensions.override
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

    @typing_extensions.override
    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        self.position += len(data)

    @typing_extensions.override
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
