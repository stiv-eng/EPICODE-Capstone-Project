"""Analysis-only enrichment of aligned tyre and suspension source channels."""
from motorsport.ingestion.motec import read_ld
from motorsport.processing.validation import quality_report


def enrich_recording(session,path):
    families={'Tire Temp Core':('tyre_core','C'),'Tire Temp Inner':('temp_i','C'),
              'Tire Temp Middle':('temp_m','C'),'Tire Temp Outer':('temp_o','C'),
              'Tire Pressure':('psi','psi'),'Tire Load':('load','N'),
              'Suspension Travel':('susp','mm')}
    selected={f'{name} {corner}' for name in families for corner in ('FL','FR','RL','RR')}
    _,channels=read_ld(path,selected)
    units=session.metadata.setdefault('channel_units',{})
    for name,(prefix,unit) in families.items():
        for corner in ('FL','FR','RL','RR'):
            source=f'{name} {corner}'
            if source not in channels:
                continue
            channel=channels[source]
            # No resampling: packet alignment must match the adapter's export grid.
            if channel.hz!=session.metadata['export_hz'] or len(channel.values)!=len(session.data) or channel.unit!=unit:
                continue
            canonical=f'{prefix}_{corner.lower()}'
            session.raw[source]=channel.values
            session.data[source]=channel.values
            session.data[canonical]=channel.values
            units[source]=units[canonical]='°C' if unit=='C' else unit
    session.metadata['position_provenance']='World X/Y are not mapped by this view. Telemetry Lap Analysis separately inspects metric Car Coord channels when available; Position is race rank and Car Pos Norm is dimensionless progress.'
    session.raw_quality=quality_report(session.raw)
    session.quality=quality_report(session.data,'elapsed_s')
    return session
