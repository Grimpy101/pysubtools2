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
    TextSize,
    Underline,
)
from ..subtitle.subtitle import Subtitle


def relative_position_to_identifier(f: Formatting):
    if typing.cast(RelativePosition, f).classifier == PositionClassifier.TOP_CENTER:
        return "0"
    else:
        return "1"


CONTROL_CODE_MAPS: typing.Dict[typing.Type[Formatting], typing.Tuple[str, typing.Callable[[Formatting], str]]] = {
    Bold: ("y", lambda _: "b"),
    Italic: ("y", lambda _: "i"),
    Underline: ("y", lambda _: "u"),
    Color: ("c", lambda f: typing.cast(Color, f).to_bgr_hex()),
    FontFace: ("f", lambda f: typing.cast(FontFace, f).face),
    TextSize: ("s", lambda f: str(typing.cast(TextSize, f).size)),
    RelativePosition: ("p", relative_position_to_identifier)
}


class MicroDVDExporter:
    def __init__(self, fps: float = 24.0) -> None:
        self.fps: float = fps
        
    @staticmethod
    def get_control_code(formatting: Formatting):
        (code, value_fn) = CONTROL_CODE_MAPS.get(formatting.__class__, (None, None))
        if code is None or value_fn is None:
            return None
        return code, value_fn(formatting)

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
                control = MicroDVDExporter.get_control_code(formatting)
                if control is None:
                    continue
                
                code, value = control
                if code != "p":
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
