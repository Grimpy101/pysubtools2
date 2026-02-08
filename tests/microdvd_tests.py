import glob
import json
import os
import pathlib
import random
import string
import time
import typing
import unittest

from pysubtools2.exporters.microdvd import MicroDVDExporter
from pysubtools2.parsers.microdvd import MicroDVDParser
from pysubtools2.subtitle.time import Time


def _generate_random_subtitle_test(units_count: int) -> str:
    output: typing.List[str] = []
    letters = string.ascii_letters
    for i in range(units_count):
        start = Time(i * 1000 + 25)
        end = start + 1000
        content = random.choices(letters, k=100)
        if len(content) > 50:
            content.insert(len(content) // 2, "|")
        content = "".join(content)

        start_str = str(start.to_frame(25))
        end_str = str(end.to_frame(25))

        output.extend(["{" + start_str + "}" + "{" + end_str + "}" + content])
    return "".join(output)


class TestMicroDVDParsing(unittest.TestCase):
    def test_for_files(self) -> None:
        sub_data_path = os.path.join(
            os.path.dirname(__file__), "data", "sub", "*.sub"
        )
        files = filter(lambda x: not x.endswith('_gt.sub'), glob.glob(sub_data_path))
        for file in files:
            file = pathlib.Path(file)

            parser = MicroDVDParser(25)
            exporter = MicroDVDExporter(25)

            subtitle = parser.parse_file(file)

            # JSON part
            json_subtitle = subtitle.to_json()
            json_file = file.with_suffix(".json")
            if json_file.exists():
                with open(json_file, "r", encoding="utf-8") as f:
                    json_content = json.load(f)
                assert json_content == json_subtitle
            else:
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(json_subtitle, f, ensure_ascii=False, indent=1)

            # Check ground truth
            sub_string = exporter.to_string(subtitle)
            gt_path = file.with_name(file.stem + "_gt.sub")
            with open(gt_path, "r", encoding="utf-8") as f:
                original_string = f.read()
                self.assertListEqual(
                    sub_string.splitlines(),
                    original_string.splitlines()
                )

    def test_parsing_speed(self) -> None:
        subtitles: typing.List[str] = []
        for _ in range(10):
            subtitle_str = _generate_random_subtitle_test(10000)
            subtitles.append(subtitle_str)

        start = time.perf_counter()
        for subtitle_str in subtitles:
            parser = MicroDVDParser()
            _ = parser.parse_text(subtitle_str)
        end = time.perf_counter()
        print(f"Took {end - start} s")
