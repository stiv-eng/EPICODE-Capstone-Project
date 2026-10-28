from dataclasses import replace

import numpy as np
import pytest

from motorsport.lap_analysis.geometry import GeometryConfig, build_geometry, three_point_curvature


def circle(radius=100., count=2001, clockwise=False):
    theta = np.linspace(0., (-1 if clockwise else 1)*2*np.pi, count)
    return np.c_[radius*np.cos(theta), radius*np.sin(theta)]


def stadium(count=500):
    # CCW, two 300 m straights joined by 50 m-radius semicircles.
    top = np.c_[np.linspace(0, 300, count, endpoint=False), np.full(count, 50.)]
    right_t = np.linspace(np.pi/2, -np.pi/2, count, endpoint=False)
    right = np.c_[300+50*np.cos(right_t), 50*np.sin(right_t)]
    bottom = np.c_[np.linspace(300, 0, count, endpoint=False), np.full(count, -50.)]
    left_t = np.linspace(-np.pi/2, -3*np.pi/2, count+1)
    left = np.c_[50*np.cos(left_t), 50*np.sin(left_t)]
    return np.vstack([top, right, bottom, left])


def test_three_point_formula_straight_collinear_and_degenerate():
    line = np.c_[np.arange(20.), np.zeros(20)]
    k = three_point_curvature(line)
    assert np.isnan(k[[0,-1]]).all() and np.all(k[1:-1]==0)
    duplicate = np.array([[0.,0.],[0.,0.],[1.,0.]])
    assert three_point_curvature(duplicate)[1]==0
    with pytest.raises(ValueError):
        three_point_curvature([[0,0],[1,1]])


@pytest.mark.parametrize('clockwise,sign', [(False,1),(True,-1)])
def test_known_radius_and_turn_sign(clockwise, sign):
    xy = circle(clockwise=clockwise)
    k = three_point_curvature(xy[:-1], closed=True)
    np.testing.assert_allclose(k, sign/100., atol=1e-10)
    g = build_geometry(xy)
    assert g.closed and abs(1/np.median(np.abs(g.curvature))-100) < .1
    assert len(g.sections)==1 and g.sections[0]['kind']=='corner'
    assert g.sections[0]['direction']==('left' if sign>0 else 'right')


def test_default_150m_threshold_is_strict_and_configurable():
    assert GeometryConfig().radius_threshold_m==150.
    assert all(s['kind']=='straight' for s in build_geometry(circle(200.)).sections)
    assert any(s['kind']=='corner' for s in build_geometry(circle(100.)).sections)
    assert all(s['kind']=='straight' for s in build_geometry(circle(100.), GeometryConfig(radius_threshold_m=80.)).sections)


def test_closed_track_partition_and_corner_wrapping():
    xy = stadium()
    # Start in the middle of the right-hand semicircle.
    xy = np.roll(xy[:-1], -750, axis=0)
    xy = np.vstack([xy, xy[0]])
    g = build_geometry(xy)
    corners = [s for s in g.sections if s['kind']=='corner']
    assert len(corners)==2 and any(s['wraps_start_finish'] for s in corners)
    assert sum(s['length_m'] for s in g.sections)==pytest.approx(g.length_m)
    for s in corners:
        assert s['curvature_weighted_apex_proxy'] is not None
        assert s['maximum_curvature_point'] is not None
        local = (s['curvature_weighted_apex_proxy']['s_m']-s['start_s_m']) % g.length_m
        assert 0 <= local <= s['length_m']


def test_weighted_apex_is_invariant_to_speed_and_stationary_sampling():
    xy = stadium(800)
    a = build_geometry(xy)
    # Uneven source density represents varying speed; duplicate positions model
    # an extended stationary interval. Geometry never accepts a duration input.
    indices = np.unique(np.r_[np.arange(0,1600,2),np.arange(1600,len(xy)),len(xy)-1])
    changed = np.repeat(xy[indices], np.where(indices < 1000, 4, 1), axis=0)
    b = build_geometry(changed)
    ca=[s for s in a.sections if s['kind']=='corner']
    cb=[s for s in b.sections if s['kind']=='corner']
    assert len(ca)==len(cb)==2
    np.testing.assert_allclose([s['curvature_weighted_apex_proxy']['s_m'] for s in ca],
                               [s['curvature_weighted_apex_proxy']['s_m'] for s in cb], atol=2.)
    assert b.quality['geometry_duplicate_samples_removed']>0
    assert b.quality['temporal_samples_preserved']==len(changed)


@pytest.mark.parametrize('spacing',[.75,1.5,3.])
def test_spatial_density_and_distance_weighted_centre(spacing):
    g=build_geometry(circle(),GeometryConfig(spacing_m=spacing))
    assert g.sections[0]['curvature_weighted_apex_proxy']['s_m']==pytest.approx(g.length_m/2,abs=.02)


def test_moderate_noise_and_nearly_collinear_values_remain_finite():
    rng=np.random.default_rng(42)
    xy=circle()+rng.normal(0,.005,(2001,2))
    g=build_geometry(xy,GeometryConfig(smoothing_m=15.))
    assert np.isfinite(g.curvature).all()
    assert 95 < 1/np.median(np.abs(g.curvature)) < 105
    line=np.c_[np.arange(100.),np.arange(100.)*1e-12]
    assert np.max(np.abs(three_point_curvature(line)[1:-1]))<1e-12


def test_open_endpoints_are_not_forced_cyclic_and_defects_are_rejected():
    xy=np.c_[np.arange(100.),np.zeros(100)]
    g=build_geometry(xy)
    assert not g.closed and np.isnan(g.curvature[[0,-1]]).all()
    for bad in (np.zeros((30,2)),np.array([[0,0],[1,1],[np.nan,3],[4,4],[5,5]]),xy*100):
        with pytest.raises(ValueError):build_geometry(bad)
    with pytest.raises(ValueError):build_geometry(xy,GeometryConfig(spacing_m=-1.))


def test_lateral_finish_gap_is_not_fabricated_as_a_tight_corner():
    xy=stadium().copy()
    xy[-1,1]+=2.
    g=build_geometry(xy)
    assert g.closed and not g.quality['seam_curvature_available']
    assert any(s['kind']=='boundary' for s in g.sections)
    assert sum(s['length_m'] for s in g.sections)==pytest.approx(g.length_m)
    assert all(s['curvature_weighted_apex_proxy'] is None for s in g.sections if s['kind']=='boundary')
    assert all(s['maximum_curvature_1_m'] is None and s['minimum_radius_m'] is None for s in g.sections if s['kind']=='boundary')
