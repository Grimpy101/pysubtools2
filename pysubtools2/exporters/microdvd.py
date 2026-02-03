import collections
import typing
from ..subtitle.formatting import (
    Bold,
    Color,
    FontFace,
    Formatting,
    Italic,
    PositionClassifier,
    RelativePosition,
    Span,
    TextSize,
    Underline,
)
from ..subtitle.subtitle import Subtitle


def get_control_code(formatting: Formatting):
    code = None
    value = None
    if isinstance(formatting, Bold):
        code = "Y"
        value = "b"
    elif isinstance(formatting, Italic):
        code = "Y"
        value = "i"
    elif isinstance(formatting, Underline):
        code = "Y"
        value = "u"
    elif isinstance(formatting, Color):
        code = "C"
        value = formatting.to_bgr_hex()
    elif isinstance(formatting, FontFace):
        code = "F"
        value = formatting.face
    elif isinstance(formatting, TextSize):
        code = "S"
        value = str(formatting.size)
    elif isinstance(formatting, RelativePosition):
        code = "P"
        if formatting.classifier == PositionClassifier.TOP_CENTER:
            value = "0"
        else:
            value = "1"
    return code, value


class MicroDVDExporter:
    def __init__(self, fps: float = 24.0) -> None:
        self.fps: float = fps

    def to_string(self, subtitle: Subtitle) -> str:
        units: typing.List[str] = []

        subtitle.sort(key=lambda unit: unit.start)

        # TODO: Sometime implement DEFAULT formatting

        units.append("{1}{1}" + str(self.fps))

        for unit in subtitle:
            if len(unit.text) == 0:
                continue
            if unit.start == unit.end:
                continue

            start = unit.start.to_frame(self.fps)
            end = unit.end.to_frame(self.fps)
            lines = collections.deque(unit.text.splitlines())

            global_formattings: collections.defaultdict[str, typing.Set[str]] = (
                collections.defaultdict(set)
            )
            per_line_formattings: collections.defaultdict[
                typing.Tuple[str, int], typing.Set[str]
            ] = collections.defaultdict(set)
            for formatting in unit.formattings:
                code, value = get_control_code(formatting)
                if code is None or value is None:
                    continue

                if isinstance(formatting, Span):
                    if formatting.start > 0 or formatting.end < unit.character_count(
                        True
                    ):
                        line_indices = unit.lines_of_formatting(formatting)
                        for line in line_indices:
                            per_line_formattings[(code, line)].add(value)
                    else:
                        global_formattings[code].add(value)
                else:
                    global_formattings[code].add(value)

            for code, values in global_formattings.items():
                if code.upper() == "Y":
                    values = list(values)
                    values.sort()
                    val = ",".join(values)
                else:
                    val = list(values)[0]
                lines[0] = "{" + f"{code.upper()}:{val}" + "}" + lines[0]

            for (code, line_index), values in per_line_formattings.items():
                if code.lower() == "y":
                    values = list(values)
                    values.sort()
                    val = ",".join(values)
                else:
                    val = list(values)[0]
                lines[line_index] = (
                    "{" + f"{code.lower()}:{val}" + "}" + lines[line_index]
                )

            text = "|".join(lines)
            start_str = "{" + str(start) + "}"
            end_str = "{" + str(end) + "}"
            units.append(start_str + end_str + text)

        output = "\n".join(units)
        return output

    def to_file(
        self, target: typing.Union[typing.IO[str], typing.IO[bytes]], subtitle: Subtitle, encoding: str = "utf-8"
    ) -> None:
        output = self.to_string(subtitle)
        if hasattr(target, "encoding"):
            _ = typing.cast(typing.TextIO, target).write(output)
        else:
            _ =typing.cast(typing.BinaryIO, target).write(output.encode(encoding))
