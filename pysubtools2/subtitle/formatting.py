import abc
import dataclasses
import enum
import typing
import typing_extensions

from .color import SUPPORTED_COLOR_NAMES


class PositionClassifier(enum.Enum):
    BOTTOM_LEFT = 1
    BOTTOM_CENTER = 2
    BOTTOM_RIGHT = 3
    MIDDLE_LEFT = 4
    MIDDLE_CENTER = 5
    MIDDLE_RIGHT = 6
    TOP_LEFT = 7
    TOP_CENTER = 8
    TOP_RIGHT = 9


@dataclasses.dataclass()
class Span:
    start: int
    end: int

    def encloses(self, i: int) -> bool:
        return self.start <= i <= self.end

    def overlaps(self, other: "Span") -> bool:
        return self.start <= other.end and other.start <= self.end


class HTMLTag(Span):
    def get_html_tag(self, _position: str) -> str:
        raise NotImplementedError

    def get_attributes(self) -> str:
        raise NotImplementedError


class Formatting(abc.ABC):
    def to_json(self) -> typing.Dict[str, typing.Any]:
        raise NotImplementedError()


@dataclasses.dataclass()
class Bold(Formatting, HTMLTag):
    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return "<b>"
        elif position == "end":
            return "</b>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return ""
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'bold',
            'start': self.start,
            'end': self.end
        }

    @typing_extensions.override
    def __str__(self) -> str:
        return f"bold[{self.start}-{self.end}]"


@dataclasses.dataclass()
class Italic(Formatting, HTMLTag):
    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return "<i>"
        elif position == "end":
            return "</i>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return ""
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'italic',
            'start': self.start,
            'end': self.end
        }

    @typing_extensions.override
    def __str__(self) -> str:
        return f"italic[{self.start}-{self.end}]"


@dataclasses.dataclass()
class Underline(Formatting, HTMLTag):
    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return "<u>"
        elif position == "end":
            return "</u>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return ""
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'underline',
            'start': self.start,
            'end': self.end
        }

    @typing_extensions.override
    def __str__(self) -> str:
        return f"underline[{self.start}-{self.end}]"


@dataclasses.dataclass()
class Strikethrough(Formatting, HTMLTag):
    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return "<s>"
        elif position == "end":
            return "</s>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return ""
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'strikethrough',
            'start': self.start,
            'end': self.end
        }

    @typing_extensions.override
    def __str__(self) -> str:
        return f"strikethrough[{self.start}-{self.end}]"


@dataclasses.dataclass()
class Color(Formatting, HTMLTag):
    # In range 0..1
    r: float
    g: float
    b: float
    a: float

    @classmethod
    def from_bgr_hex(cls, start: int, end: int, color_string: str) -> "Color":
        # TODO: See if you can combine this with from_hex
        color_string = color_string.replace("$", "")
        rgb = tuple(int(color_string[i : i + 2], 16) for i in (0, 2, 4))
        b = rgb[0] / 255
        g = rgb[1] / 255
        r = rgb[2] / 255
        return Color(start, end, r, g, b, 1.0)

    @classmethod
    def from_hex(cls, start: int, end: int, color_string: str) -> "Color":
        color_string = color_string.replace("#", "")
        rgb = tuple(int(color_string[i : i + 2], 16) for i in (0, 2, 4))
        r = rgb[0] / 255
        g = rgb[1] / 255
        b = rgb[2] / 255
        return Color(start, end, r, g, b, 1.0)

    @classmethod
    def from_html_name(cls, start: int, end: int, color_name: str) -> "Color":
        rgb = SUPPORTED_COLOR_NAMES[color_name.lower()]
        return Color(start, end, rgb[0], rgb[1], rgb[2], 1.0)

    @classmethod
    def from_string(
        cls, start: int, end: int, color_string: str
    ) -> typing.Optional["Color"]:
        color_string = color_string.strip().lower()
        color = None
        try:
            color = cls.from_hex(start, end, color_string)
        except Exception:
            try:
                color = cls.from_html_name(start, end, color_string)
            except Exception:
                pass
        return color

    def to_hex(self) -> str:
        r = int(self.r * 255.0)
        g = int(self.g * 255.0)
        b = int(self.b * 255.0)
        return f"#{r:02x}{g:02x}{b:02x}"

    def to_bgr_hex(self) -> str:
        r = int(self.r * 255.0)
        g = int(self.g * 255.0)
        b = int(self.b * 255.0)
        return f"${b:02x}{g:02x}{r:02x}"
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'color',
            'start': self.start,
            'end': self.end,
            'color': [self.r, self.g, self.b, self.a]
        }

    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return f'<font color="{self.to_hex()}">'
        elif position == "end":
            return "</font>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return f'color="{self.to_hex()}"'

    @typing_extensions.override
    def __str__(self) -> str:
        return f"color[{self.start}-{self.end}]({self.r},{self.g},{self.b},{self.a})"


@dataclasses.dataclass()
class FontFace(Formatting, HTMLTag):
    face: str

    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return f'<font face="{self.face}">'
        elif position == "end":
            return "</font>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return f'face="{self.face}"'
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'fontface',
            'start': self.start,
            'end': self.end,
            'font': self.face
        }

    @typing_extensions.override
    def __str__(self) -> str:
        return f"fontFace[{self.start}-{self.end}]({self.face})"


@dataclasses.dataclass()
class TextSize(Formatting, HTMLTag):
    size: int

    @typing_extensions.override
    def get_html_tag(self, position: str) -> str:
        if position == "start":
            return f"<font size={self.size}>"
        elif position == "end":
            return "</font>"
        raise ValueError(f"Tag type not valid: {position}")

    @typing_extensions.override
    def get_attributes(self) -> str:
        return f"size={self.size}"
    
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'type': 'textsize',
            'start': self.start,
            'end': self.end,
            'size': self.size
        }

    @typing_extensions.override
    def __str__(self) -> str:
        return f"textSize[{self.start}-{self.end}]({self.size})"


@dataclasses.dataclass()
class Position(Formatting):
    @typing_extensions.override
    def to_json(self) -> typing.Dict[str, typing.Any]:
        if isinstance(self, RelativePosition):
            return {
                'type': 'position',
                'kind': 'relative',
                'position': self.classifier.value
            }
        elif isinstance(self, AbsolutePosition):
            return {
                'type': 'position',
                'kind': 'absolute',
                'position': {
                    'x1': self.x1,
                    'x2': self.x2,
                    'y1': self.y1,
                    'y2': self.y2
                }
            }
        else:
            raise NotImplementedError()
    
    @typing_extensions.override
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Position)


@dataclasses.dataclass()
class RelativePosition(Position):
    classifier: PositionClassifier


@dataclasses.dataclass()
class AbsolutePosition(Position):
    x1: int
    x2: int
    y1: int
    y2: int
