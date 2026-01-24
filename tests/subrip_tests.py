import json
import os
import random
import string
import time
import typing
import unittest

from pysubtools2.exporters.subrip import SubRipExporter
from pysubtools2.parsers.subrip import SubRipParser
from pysubtools2.subtitle.time import Time
from pysubtools2.utils import get_file_encoding


def _generate_random_subrip_text(units_count: int) -> str:
    output = []
    letters = string.ascii_letters
    for i in range(units_count):
        index = i + 1
        start = Time(i * 1000 + 25)
        end = start + 1000
        content = random.choices(letters, k=100)
        if len(content) > 50:
            content.insert(len(content) // 2, "\n")
        content = "".join(content)

        start_str = SubRipExporter._time_to_string(start)
        end_str = SubRipExporter._time_to_string(end)

        output.extend(
            [str(index), "\n", start_str, " --> ", end_str, "\n", content, "\n\n"]
        )
    return "".join(output)


class TestSubRipParsing(unittest.TestCase):
    def test_for_files(self) -> None:
        srt_data_path = os.path.join(
            os.path.dirname(__file__), "data", "srt", "files.json"
        )
        with open(srt_data_path, "r") as f:
            srt_data: typing.Mapping[str, typing.Any] = json.load(f)

        for file, properties in srt_data.items():
            print(file)

            parser = SubRipParser()
            exporter = SubRipExporter()

            full_filepath = os.path.join(os.path.dirname(srt_data_path), file)
            subtitle = parser.parse_file(full_filepath)

            assert len(subtitle) == properties["units"]

            subrip_string = exporter.to_string(subtitle)
            charset = get_file_encoding(full_filepath)

            assert charset == properties["encoding"]

            gt_path = os.path.join(
                os.path.dirname(srt_data_path), properties["ground_truth"]
            )
            with open(gt_path, "r", encoding="utf-8") as f:
                original_string = f.read()
                if subrip_string != original_string:
                    print(subrip_string)
                assert subrip_string == original_string

    def test_parsing_speed(self) -> None:
        subtitles = []
        for _ in range(10):
            subtitle_str = _generate_random_subrip_text(10000)
            subtitles.append(subtitle_str)
        
        start = time.perf_counter()
        for subtitle_str in subtitles:
            parser = SubRipParser()
            parser.parse_text(subtitle_str)
        end = time.perf_counter()
        print(f"Took {end - start} s")


if __name__ == "__main__":
    unittest.main()
