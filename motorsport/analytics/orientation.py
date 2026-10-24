"""Recorded visualization only: verified planar heading or guarded local atan2.

No function here is imported by the ML layer. A next packet used for retrospective
direction never enters any causal predictive feature or source frame.
"""
import numpy as np
from .timebase import numeric
from .position import position_adjacency


def transform_heading(angle,unit,zero_vector,positive_rotation,handedness,display_transform=None):
    """Physical CW/CCW convention -> displayed mathematical XY radians.

    zero_vector is expressed in the source planar axes. A left-handed planar
    basis reverses physical rotation. The explicit matrix supports axis swaps
    or reflections; the current source-coordinate map uses the identity matrix.
    The icon artwork points along mathematical +X before rotation.
    """
    if unit not in ('deg','rad') or positive_rotation not in ('ccw','cw') or handedness not in ('right','left'):
        raise ValueError('Incomplete or unsupported heading convention')
    zero=np.asarray(zero_vector,dtype=float)
    matrix=np.eye(2) if display_transform is None else np.asarray(display_transform,dtype=float)
    if zero.shape!=(2,) or not np.isfinite(zero).all() or np.linalg.norm(zero)==0:
        raise ValueError('Invalid heading zero vector')
    if matrix.shape!=(2,2) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix))<1e-12 or not np.isfinite(angle):
        raise ValueError('Invalid heading transform/value')
    theta=np.deg2rad(angle) if unit=='deg' else angle
    theta*= (1 if positive_rotation=='ccw' else -1)*(1 if handedness=='right' else -1)
    direction=matrix @ (np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]]) @ zero)
    return float(np.arctan2(direction[1],direction[0]))


def vehicle_orientation(frame,position,metadata,adjacency=None):
    """Position is a row offset, never an index label or a simplified vertex."""
    if not 0<=position<len(frame):
        raise IndexError('Selected packet is outside the frame')
    xy=np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]
    if not np.isfinite(xy[position]).all():
        return None,'Orientation unavailable: missing position.'
    convention=metadata.get('planar_heading',{})
    required={'channel','unit','zero_vector','positive_rotation','handedness','coordinate_columns','provenance'}
    if (convention.get('verified') is True and required<=set(convention)
            and convention['coordinate_columns']==['pos_x','pos_y'] and convention['provenance']
            and metadata.get('channel_units',{}).get(convention['channel'])==convention['unit']):
        angle=numeric(frame,convention['channel'])[position]
        try:
            theta=transform_heading(angle,convention['unit'],convention['zero_vector'],
                                    convention['positive_rotation'],convention['handedness'])
            return theta,'Orientation from verified measured heading.'
        except (ValueError,TypeError):
            pass  # An unknown/missing measurement falls back visibly, never guessed.
    edges=position_adjacency(frame)[0] if adjacency is None else adjacency
    lengths=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    moving=lengths[np.isfinite(lengths)&(lengths>0)&edges]
    finite_xy=xy[np.isfinite(xy)]
    epsilon=max(1e-12,32*np.finfo(float).eps*max(float(np.abs(finite_xy).max()),1),
                float(np.median(moving))*1e-6 if len(moving) else 0.)
    if position<len(frame)-1 and edges[position]:
        a,b=position,position+1
        label='Orientation estimated from trajectory (forward difference).'
    elif position>0 and edges[position-1]:
        a,b=position-1,position
        label='Orientation estimated from trajectory (backward difference at fragment end).'
    else:
        return None,'Orientation unavailable: isolated sample or trajectory boundary.'
    delta=xy[b]-xy[a]
    if np.linalg.norm(delta)<=epsilon:
        return None,'Orientation unavailable: stationary or near-zero movement.'
    return float(np.arctan2(delta[1],delta[0])),label
