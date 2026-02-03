import re
import typing

from ..subtitle.formatting import (
    PositionClassifier,
    RelativePosition,
)

SSA_TAG_REGEX = re.compile(r"{\\*([\S:][\S]+)}")


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
