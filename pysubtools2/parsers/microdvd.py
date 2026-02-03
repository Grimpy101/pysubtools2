import collections
import copy
import io
import itertools
import os
import re
import typing
from ..subtitle.formatting import (
    Bold,
    Color,
    FontFace,
    Formatting,
    Italic,
    PositionClassifier,
    TextSize,
    Underline,
    RelativePosition,
)
from ..utils import get_file_encoding
from ..subtitle.subtitle import Subtitle, SubtitleUnit
from ..subtitle.time import Time


SUB_REGEX = re.compile(r"{(?P<start>.*?)}{(?P<end>.*?)}(?P<content>.*)")
CONTROL_CODE_REGEX = re.compile(r"{(.*?)}")


def formattings_from_control_codes(
    code: str, value: str, start: int, end: int
) -> typing.List[Formatting]:
    formattings: typing.List[Formatting] = []
    code = code.lower()

    if code == "y":
        value_lower = value.lower()
        if "i" in value_lower:
            formattings.append(Italic(start, end))
        if "b" in value_lower:
            formattings.append(Bold(start, end))
        if "u" in value_lower:
            formattings.append(Underline(start, end))
    elif code == "c":
        formattings.append(Color.from_bgr_hex(start, end, value))
    elif code == "f":
        formattings.append(FontFace(start, end, value))
    elif code == "s":
        try:
            formattings.append(TextSize(start, end, int(value)))
        except ValueError:
            pass
    elif code == "p":
        if value == "0":
            formattings.append(RelativePosition(PositionClassifier.TOP_CENTER))
    return formattings


class MicroDVDParser:
    def __init__(self, fps: float = 24.0) -> None:
        self.subtitle: Subtitle = Subtitle()
        self.fps: float = fps
        self._is_previous_end_empty: bool = False
        self.default_control_codes: collections.defaultdict[str, typing.Set[str]] = (
            collections.defaultdict(set)
        )
        self.raw_text: str = ""
        self.previous_unit: typing.Optional[SubtitleUnit] = None

    def _parse_content(
        self, content: str
    ) -> typing.Tuple[str, typing.List[Formatting]]:
        clean_lines: typing.List[str] = []
        global_control_codes: collections.defaultdict[str, typing.Set[str]] = (
            collections.defaultdict(set)
        )
        per_line_control_codes: collections.defaultdict[
            typing.Tuple[int, str], typing.Set[str]
        ] = collections.defaultdict(set)
        formattings: typing.List[Formatting] = []

        for c, v in self.default_control_codes.items():
            global_control_codes[c] = v

        lines = content.split("|")
        for i, line in enumerate(lines):
            clean_line = line
            for control_code in CONTROL_CODE_REGEX.finditer(line):
                code = control_code.group(1)
                split = code.split(":")
                if len(split) > 1:
                    identifier = split[0].strip()
                    value = split[1].strip()
                    if identifier.isupper():
                        global_control_codes[identifier].add(value)
                    else:
                        per_line_control_codes[(i, identifier)].add(value)

                clean_line = clean_line.replace("{" + code + "}", "")
            clean_lines.append(clean_line)

        raw_text = "\n".join(clean_lines)

        global_start = 0
        global_end = len(raw_text)
        for code, val in global_control_codes.items():
            if code == "Y":
                for v in val:
                    formatting = formattings_from_control_codes(
                        code, v, global_start, global_end
                    )
                    formattings.extend(formatting)
            else:
                value = list(val)[0]
                formatting = formattings_from_control_codes(
                    code, value, global_start, global_end
                )
                formattings.extend(formatting)

        line_length_accumulate = list(
            itertools.accumulate(map(lambda x: len(x) + 1, clean_lines))
        )
        for (line_index, code), val in per_line_control_codes.items():
            index = line_index - 1
            if index < 0:
                start = 0
                end = line_length_accumulate[0] - 1
            else:
                start = line_length_accumulate[index]
                end = line_length_accumulate[index + 1] - 1

            if code == "Y":
                for v in val:
                    formatting = formattings_from_control_codes(code, v, start, end)
                    formattings.extend(formatting)
            else:
                value = list(val)[0]
                formatting = formattings_from_control_codes(code, value, start, end)
                formattings.extend(formatting)
        return (raw_text, list(formattings))

    def _parse_unit(self, unit_str: str):
        matches = re.match(SUB_REGEX, unit_str)
        if matches is None:
            return

        properties = matches.groupdict()
        start_str = properties.get("start")
        end_str = properties.get("end")
        content = properties.get("content")

        if start_str is None or end_str is None or not start_str.isnumeric():
            return

        start_frame = int(start_str)
        start = Time.from_frame(start_frame, self.fps)
        if self._is_previous_end_empty and self.previous_unit is not None:
            self.previous_unit.end = start

        end_frame = int(end_str) if end_str != "" else None
        self._is_previous_end_empty = end_frame is None

        end = (
            Time.from_frame(end_frame, self.fps)
            if end_frame is not None
            else copy.deepcopy(start) + 8000
        )

        if content is not None:
            raw_text, formattings = self._parse_content(content)
            unit = SubtitleUnit(start, end, raw_text, formattings)
            self.subtitle.append(unit)
            self.previous_unit = unit

    def _parse_default(self, sub_lines: typing.List[str]):
        for line in sub_lines:
            if "{DEFAULT}" not in line:
                continue

            matches = re.match(SUB_REGEX, line)
            if matches is None:
                continue

            properties = matches.groupdict()
            start_str = properties.get("start")
            content = properties.get("content")

            if start_str != "DEFAULT" or content is None:
                continue

            for control_code in CONTROL_CODE_REGEX.finditer(content):
                code = control_code.group(1)

                # We do this just to make sure the codes are valid
                parts = code.split(":")
                if len(parts) <= 1:
                    continue
                identifier = parts[0].strip().lower()
                value = parts[1].strip().lower()
                if identifier not in ["c", "f", "s", "y", "p"]:
                    continue

                self.default_control_codes[identifier].add(value)
            break

    def parse_text(self, sub_text: str, fps_from_file: bool = True) -> Subtitle:
        sub_text = sub_text.replace("\ufeff", "")  # Remove BOM from UTF-8 text
        sub_lines = sub_text.splitlines()

        if fps_from_file:
            # Sometimes, sub files contain FPS as first invisible subtitle
            line = sub_lines[0]
            matches = re.match(SUB_REGEX, line)
            if matches is not None:
                properties = matches.groupdict()
                start_str = properties.get("start")
                end_str = properties.get("end")
                content = properties.get("content")
                if start_str == end_str and content is not None:
                    try:
                        self.fps = float(content)
                    except ValueError:
                        pass

        self._parse_default(sub_lines)

        for line in sub_lines:
            self._parse_unit(line)

        return self.subtitle

    def parse_file(
        self,
        file: typing.Any,
        fps_from_file: bool = True,
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

        subtitle = self.parse_text(file_content, fps_from_file)
        return subtitle
