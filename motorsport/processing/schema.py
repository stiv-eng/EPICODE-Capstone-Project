"""Canonical units and explicit source profiles; never infer units from maxima."""
from dataclasses import dataclass, field


CANONICAL_UNITS = {
    'elapsed_s': 's', 'lap_id': 'identifier', 'lap_elapsed_s': 's',
    'distance_m': 'm', 'speed_kmh': 'km/h', 'throttle_pct': '%',
    'brake_pct': '%', 'steering': 'source unit', 'rpm': 'rpm', 'gear': 'integer',
    'g_lat': 'source unit', 'g_lon': 'source unit',
    'pos_x': 'source unit', 'pos_y': 'source unit',
}


@dataclass(frozen=True)
class SourceProfile:
    name: str = 'Canonical / units unspecified'
    # Maps CANONICAL target to SOURCE column. Additional source channels survive.
    columns: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)


CANONICAL = SourceProfile()
# Only for the audited attachment, or an explicit user selection. Controls span
# [0, 1]; speed agrees with the velocity norm * 3.6 and time agrees with wall_time.
SUPPLIED_V04 = SourceProfile(
    name='Supplied v0.4 telemetry (audited)',
    columns={'elapsed_s': 'timestamp', 'rpm': 'rpms', 'throttle_pct': 'throttle',
             'brake_pct': 'brake', 'steering': 'steer_angle', 'pos_y': 'pos_z'},
    units={'elapsed_s': 's', 'speed_kmh': 'km/h', 'throttle_pct': 'fraction',
           'brake_pct': 'fraction'},
)
