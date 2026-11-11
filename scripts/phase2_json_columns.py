"""Stream pandas column-oriented JSON using only the standard library.

Yields (column_name, index_key, scalar_or_record) without materializing a whole
column or archive. Callers select fields explicitly; no Monty object decoding.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path


class JSONStream:
    def __init__(self, stream, block_size=1024 * 1024):
        self.stream, self.block_size = stream, block_size
        self.buffer, self.position, self.eof = "", 0, False
        self.decoder = json.JSONDecoder()

    def more(self):
        block = self.stream.read(self.block_size)
        self.buffer = self.buffer[self.position:] + block
        self.position = 0
        self.eof = not block

    def peek(self):
        while True:
            while self.position < len(self.buffer) and self.buffer[self.position].isspace():
                self.position += 1
            if self.position < len(self.buffer):
                return self.buffer[self.position]
            if self.eof:
                return ""
            self.more()

    def expect(self, token):
        actual = self.peek()
        if actual != token:
            raise ValueError(f"Expected {token!r}, got {actual!r}")
        self.position += 1

    def value(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
                # Numbers need a following delimiter to avoid accepting a partial
                # numeric prefix at a read boundary. Objects/strings are self-delimited.
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if end == len(self.buffer) and not self.eof:
                        self.more()
                        continue
                    if end < len(self.buffer) and self.buffer[end] not in " \r\n\t,}]":
                        if self.eof:
                            raise ValueError("Invalid numeric token")
                        self.more()
                        continue
                self.position = end
                return value
            except json.JSONDecodeError:
                if self.eof:
                    raise
                self.more()


def iter_column_records(path: str | Path, wanted_columns=None):
    """Yield all records from requested columns (None means all columns).

    Other column values are decoded and discarded record-by-record, never used as
    selectors. A requested dict value remains an ordinary dict, not executable data.
    """
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        reader = JSONStream(stream)
        reader.expect("{")
        while reader.peek() != "}":
            column = reader.value()
            reader.expect(":")
            reader.expect("{")
            while reader.peek() != "}":
                key = reader.value()
                reader.expect(":")
                value = reader.value()
                if wanted_columns is None or column in wanted_columns:
                    yield column, key, value
                if reader.peek() != "}":
                    reader.expect(",")
            reader.expect("}")
            if reader.peek() != "}":
                reader.expect(",")
        reader.expect("}")
        if reader.peek():
            raise ValueError("Unexpected content after JSON root")
