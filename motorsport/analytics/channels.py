"""Source-aware dynamics and four-corner channel discovery."""
CORNERS = ('fl', 'fr', 'rl', 'rr')
TYRE_FAMILIES = {
    'Core temperature': 'tyre_core', 'Inner temperature': 'temp_i',
    'Middle temperature': 'temp_m', 'Outer temperature': 'temp_o',
    'Pressure': 'psi', 'Wear (source reported)': 'wear',
    'Wheel load': 'load', 'Wheel speed': 'wheel_speed',
}


def corner_channels(frame, prefix):
    return {corner.upper(): f'{prefix}_{corner}' for corner in CORNERS if f'{prefix}_{corner}' in frame}


def signal_unit(session, channel):
    explicit = session.metadata.get('channel_units', {})
    if channel in explicit:
        return explicit[channel]
    from motorsport.processing.schema import CANONICAL_UNITS
    return CANONICAL_UNITS.get(channel, 'source unit')
