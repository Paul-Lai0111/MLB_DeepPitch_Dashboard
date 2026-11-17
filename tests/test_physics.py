import numpy as np
import pandas as pd
import pytest

from deeppitch import physics as ph


def synthetic(**kw):
    """A typical 95 mph four-seamer from a right-hander."""
    base = dict(vx0=6.0, vy0=-138.0, vz0=-6.0, ax=-8.0, ay=29.0, az=-14.0,
                plate_x=0.0, plate_z=2.8, release_extension=6.5,
                pfx_x=-0.6, pfx_z=1.4, p_throws="R", spin_axis=210.0,
                release_spin_rate=2350.0, pitch_type="FF")
    base.update(kw)
    return pd.DataFrame([base])


def test_time_to_plate_is_realistic():
    t = ph.time_to_y(-138.0, 29.0, ph.Y_PLATE)
    assert 0.33 < t < 0.42


def test_trajectory_ends_at_measured_location():
    df = synthetic()
    tr = ph.trajectory(df.iloc[0])
    assert tr["y"].iloc[-1] == pytest.approx(ph.Y_PLATE, abs=1e-6)
    assert tr["z"].iloc[-1] == pytest.approx(2.8, abs=1e-6)
    assert tr["x"].iloc[-1] == pytest.approx(0.0, abs=1e-6)
    assert tr["y"].iloc[0] == pytest.approx(60.5 - 6.5, abs=1e-6)


def test_spin_lifts_fastball_above_gravity_only_path():
    tr = ph.trajectory(synthetic().iloc[0])
    assert tr["z"].iloc[-1] > tr["z_nospin"].iloc[-1] + 0.8  # ~1 ft of "rise"


def test_vaa_negative_and_flatter_when_less_drop():
    steep = ph.approach_angles(synthetic(vz0=-9.0))[0][0]
    flat = ph.approach_angles(synthetic(vz0=-4.0))[0][0]
    assert steep < flat < 0


def test_arm_side_normalisation_mirrors_lefties():
    r = ph.movement(synthetic(pfx_x=-0.6, p_throws="R"))["hb"][0]
    l = ph.movement(synthetic(pfx_x=0.6, p_throws="L"))["hb"][0]
    assert r == pytest.approx(l) and r > 0


def test_ssw_zero_when_movement_matches_spin_axis():
    # pure backspin (180 deg) moving straight up -> no deviation
    dev = ph.seam_shifted_wake(synthetic(spin_axis=180.0, pfx_x=0.0, pfx_z=1.4))
    assert dev[0] == pytest.approx(0.0, abs=1e-9)


def test_ssw_mirrored_for_lefties():
    r = ph.seam_shifted_wake(synthetic(spin_axis=230.0, pfx_x=-1.2, pfx_z=0.6, p_throws="R"))[0]
    l = ph.seam_shifted_wake(synthetic(spin_axis=130.0, pfx_x=1.2, pfx_z=0.6, p_throws="L"))[0]
    assert r == pytest.approx(l)


def test_axis_to_clock():
    assert ph.axis_to_clock([180, 210, 150, 0]) == ["12:00", "1:00", "11:00", "6:00"]


def test_tunnel_pairs_skip_same_type_and_respect_order():
    rows = []
    for n, (pt, px) in enumerate([("FF", 0.0), ("FF", 0.1), ("SL", 0.8)], start=1):
        r = synthetic(pitch_type=pt, plate_x=px).iloc[0].to_dict()
        r.update(game_pk=1, at_bat_number=1, pitch_number=n, pitcher=10, game_year=2024)
        rows.append(r)
    df = pd.DataFrame(rows).sample(frac=1, random_state=0)  # shuffled on purpose
    pairs = ph.tunnel_pairs(df)
    assert len(pairs) == 1
    p = pairs.iloc[0]
    assert (p.prev_type, p.pitch_type) == ("FF", "SL")
    assert p.plate_in == pytest.approx(0.7 * 12, rel=1e-6)
    assert p.tunnel_in < p.plate_in  # paths converge earlier in flight
