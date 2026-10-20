"""Bounded, numeric-only MoTeC LD reader; never executes source code/pickle.

Structures independently implemented from racingmagick's format notes and
the public motecldparser field specification. Linked offsets are authoritative;
ACGym headers include an eight-byte short name before the channel unit.
"""
from dataclasses import dataclass
from pathlib import Path
import struct

import numpy as np


@dataclass(frozen=True)
class Channel:
    name: str
    unit: str
    hz: int
    values: np.ndarray


def read_ld(path, selected=None):
    path = Path(path)
    if path.stat().st_size > 50_000_000:
        raise ValueError('LD file exceeds the bounded reader limit')
    blob = path.read_bytes()
    if len(blob) < 414 or struct.unpack_from('<I', blob)[0] != 0x40:
        raise ValueError('Invalid/truncated LD header')
    def label(offset, size):
        return blob[offset:offset+size].split(b'\0')[0].decode('latin-1').strip()
    header = {key: label(offset, size) for key, offset, size in [
        ('date',94,16), ('time',126,16), ('driver',158,64),
        ('vehicle',222,64), ('venue',350,64)]}
    pointer = struct.unpack_from('<I', blob, 8)[0]
    channels, seen = {}, set()
    while pointer:
        if pointer in seen or len(seen) >= 2048 or pointer+84 > len(blob):
            raise ValueError('Invalid/cyclic channel pointer')
        seen.add(pointer)
        prev, following, data, count, ident, kind, width, hz, shift, mul, scale, dec = struct.unpack_from('<4I4H4h', blob, pointer)
        if width not in (2,4) or not 1 <= hz <= 10000 or count > 5_000_000 or data+count*width > len(blob) or abs(dec)>12:
            raise ValueError('Invalid LD channel bounds/encoding')
        if kind not in (0,3,5,7):
            raise ValueError('Unsupported LD numeric encoding')
        name, unit = label(pointer+32,32), label(pointer+72,12)
        if name in channels:
            raise ValueError('Duplicate LD channel name')
        if selected is None or name in selected:
            dtype = ('<f' if kind == 7 else '<i') + str(width)
            values = np.frombuffer(blob, dtype=dtype, count=count, offset=data).astype(float)
            if kind != 7:
                values = (values/(scale or 1)*10.**(-dec)+shift)*(mul or 1)
            channels[name] = Channel(name, unit, hz, values)
        pointer = following
    if not seen:
        raise ValueError('LD contains no channels')
    return header, channels
