import os
import typing
import charset_normalizer


class EncodingException(Exception):
    pass


def get_file_encoding(filepath: typing.Union[str, os.PathLike]) -> str:
    matches = charset_normalizer.from_path(filepath)
    best_match = matches.best()
    if best_match is None:
        raise EncodingException(f"Could not detect encoding for file {filepath}")
    return best_match.encoding


def get_bytes_encoding(content: typing.Union[bytes, bytearray]) -> str:
    matches = charset_normalizer.from_bytes(content)
    best_match = matches.best()
    if best_match is None:
        raise EncodingException("Could not detect encoding for provided bytes")
    return best_match.encoding
