import glob
import os
import pathlib
import unittest

from pysubtools2.parsers.webvtt import WebVTTParser


class TestWebVTTParsing(unittest.TestCase):
    def test_for_files(self) -> None:
        srt_data_path = os.path.join(
            os.path.dirname(__file__), "data", "vtt", "*.vtt"
        )
        files = filter(lambda x: not x.endswith('_gt.vtt'), glob.glob(srt_data_path))
        for file in files:
            print(file)
            file = pathlib.Path(file)
            parser = WebVTTParser()
            subtitle = parser.parse_file(file)
            for sub in subtitle:
                print(sub)