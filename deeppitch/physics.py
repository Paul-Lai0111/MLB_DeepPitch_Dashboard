"""
Pitch physics engine.

Everything here is derived from Statcast's 9-parameter trajectory fit:
the ball's velocity (vx0, vy0, vz0) and constant acceleration (ax, ay, az)
at y = 50 ft from the back tip of home plate.

Coordinate system (Statcast, catcher's view):
    x  positive toward the catcher's right (first-base side)
    y  positive from the plate toward the pitcher
    z  positive up
`az` already contains gravity (about -32.17 ft/s^2 plus Magnus lift).

All functions are vectorised over numpy arrays / pandas Series.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

G = 32.174                 # ft/s^2
Y_REF = 50.0               # Statcast reference plane (ft from plate)
Y_PLATE = 17.0 / 12.0      # front edge of home plate (ft)
DECISION_TIME = 0.175      # s before the plate: last moment a hitter can still start/abort a swing
BALL_RADIUS_FT = 0.1208    # 2.9 in diameter
INCH = 12.0

FASTBALLS = {"FF", "SI", "FC"}
PITCH_FAMILIES = {
    "FF": "fastball", "SI": "fastball", "FC": "fastball",
    "SL": "breaking", "ST": "breaking", "SV": "breaking", "CU": "breaking",
    "KC": "breaking", "CS": "breaking",
    "CH": "offspeed", "FS": "offspeed", "FO": "offspeed", "SC": "offspeed",
    "KN": "other",
}


def _f(x) -> np.ndarray:
    return np.asarray(x, dtype="float64")


# ---------------------------------------------------------------------------
# Kinematics of the constant-acceleration fit
# ---------------------------------------------------------------------------

def time_to_y(vy0, ay, y_target):
    """Time (s) for the ball to move from y=50 ft to `y_target`.

    Solves 50 + vy0*t + 0.5*ay*t^2 = y_target. vy0 < 0 (toward plate) and
    ay > 0 (drag slows the ball), so the smaller positive root is physical.
    Negative results mean the target lies behind the 50-ft plane (e.g. release).
    """
    vy0, ay = _f(vy0), _f(ay)
    disc = np.maximum(vy0**2 - 2.0 * ay * (Y_REF - _f(y_target)), 0.0)
    return (-vy0 - np.sqrt(disc)) / ay


def anchor_at_50ft(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Recover (x, z) at y=50 ft by integrating back from the measured plate location."""
    t = time_to_y(df["vy0"], df["ay"], Y_PLATE)
    x50 = _f(df["plate_x"]) - _f(df["vx0"]) * t - 0.5 * _f(df["ax"]) * t**2
    z50 = _f(df["plate_z"]) - _f(df["vz0"]) * t - 0.5 * _f(df["az"]) * t**2
    return x50, z50


def position_at_time(df: pd.DataFrame, t) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ball (x, y, z) in ft at time t (s) after crossing the 50-ft plane."""
    x50, z50 = anchor_at_50ft(df)
    t = _f(t)
    x = x50 + _f(df["vx0"]) * t + 0.5 * _f(df["ax"]) * t**2
    y = Y_REF + _f(df["vy0"]) * t + 0.5 * _f(df["ay"]) * t**2
    z = z50 + _f(df["vz0"]) * t + 0.5 * _f(df["az"]) * t**2
    return x, y, z


def trajectory(row: pd.Series | dict, n: int = 60, from_release: bool = True) -> pd.DataFrame:
    """Sample one pitch's flight path from release to the plate.

    Returns columns t (s since release), x, y, z (ft) and the gravity-only
    "ghost" path the ball would follow with no spin (z_nospin, x_nospin).
    """
    one = pd.DataFrame([dict(row)])
    ext = float(one.get("release_extension", pd.Series([6.2])).iloc[0] or 6.2)
    y_rel = 60.5 - ext if from_release else Y_REF
    t0 = float(time_to_y(one["vy0"], one["ay"], y_rel)[0])
    t1 = float(time_to_y(one["vy0"], one["ay"], Y_PLATE)[0])
    ts = np.linspace(t0, t1, n)
    x50, z50 = anchor_at_50ft(one)
    vx0, vy0, vz0 = (float(one[c].iloc[0]) for c in ("vx0", "vy0", "vz0"))
    ax, ay, az = (float(one[c].iloc[0]) for c in ("ax", "ay", "az"))
    x = x50[0] + vx0 * ts + 0.5 * ax * ts**2
    y = Y_REF + vy0 * ts + 0.5 * ay * ts**2
    z = z50[0] + vz0 * ts + 0.5 * az * ts**2
    # Spinless ghost: same release state, gravity + drag only (drag ~ along y).
    xr = x50[0] + vx0 * t0 + 0.5 * ax * t0**2
    zr = z50[0] + vz0 * t0 + 0.5 * az * t0**2
    vxr, vzr = vx0 + ax * t0, vz0 + az * t0
    dt = ts - t0
    z_ns = zr + vzr * dt - 0.5 * G * dt**2
    x_ns = xr + vxr * dt
    return pd.DataFrame({"t": dt, "x": x, "y": y, "z": z, "x_nospin": x_ns, "z_nospin": z_ns})


# ---------------------------------------------------------------------------
# Approach angles
# ---------------------------------------------------------------------------

def approach_angles(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Vertical and horizontal approach angle (deg) at the front of the plate.

    VAA is negative (ball descending); closer to 0 = flatter.
    HAA is positive toward the first-base side (catcher's right).
    """
    t = time_to_y(df["vy0"], df["ay"], Y_PLATE)
    vx = _f(df["vx0"]) + _f(df["ax"]) * t
    vy = _f(df["vy0"]) + _f(df["ay"]) * t
    vz = _f(df["vz0"]) + _f(df["az"]) * t
    vaa = np.degrees(np.arctan2(vz, -vy))
    haa = np.degrees(np.arctan2(vx, -vy))
    return vaa, haa


def flight_time(df: pd.DataFrame) -> np.ndarray:
    """Seconds from release to the front of the plate."""
    y_rel = 60.5 - _f(df["release_extension"])
    return time_to_y(df["vy0"], df["ay"], Y_PLATE) - time_to_y(df["vy0"], df["ay"], y_rel)


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

def arm_side_sign(p_throws) -> np.ndarray:
    """+1 converts catcher-view x into 'arm side positive' for each pitcher."""
    return np.where(np.asarray(p_throws) == "R", -1.0, 1.0)


def movement(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """IVB and arm-side-normalised horizontal break, in inches."""
    sign = arm_side_sign(df["p_throws"])
    return {
        "ivb": _f(df["pfx_z"]) * INCH,
        "hb": _f(df["pfx_x"]) * INCH * sign,          # + = arm side (run), - = glove side (sweep)
        "hb_catcher": _f(df["pfx_x"]) * INCH,
    }


def magnus_acceleration(df: pd.DataFrame) -> np.ndarray:
    """Magnitude (ft/s^2) of the spin-induced acceleration.

    Remove gravity, then remove the component along the velocity (drag).
    What remains is perpendicular to the flight path: the Magnus force.
    Velocity is taken at mid-flight to match the constant-acceleration fit.
    """
    t_mid = 0.5 * time_to_y(df["vy0"], df["ay"], Y_PLATE)
    v = np.c_[_f(df["vx0"]) + _f(df["ax"]) * t_mid,
              _f(df["vy0"]) + _f(df["ay"]) * t_mid,
              _f(df["vz0"]) + _f(df["az"]) * t_mid]
    a = np.c_[_f(df["ax"]), _f(df["ay"]), _f(df["az"]) + G]
    speed = np.linalg.norm(v, axis=1)
    vhat = v / speed[:, None]
    a_drag = (a * vhat).sum(axis=1)
    a_perp = a - a_drag[:, None] * vhat
    return np.linalg.norm(a_perp, axis=1), speed


def spin_efficiency(df: pd.DataFrame, reference: float | None = None) -> tuple[np.ndarray, float]:
    """Share of total spin that is transverse (produces Magnus movement).

    In the low-spin-parameter regime the lift coefficient is linear in spin,
    so Magnus acceleration ~ v * omega_transverse. The ratio
    a_M / (v * omega_total) therefore tracks omega_transverse / omega_total.
    We calibrate the scale so that the 98th percentile of four-seam
    fastballs (near-pure backspin) reads 100%.
    Returns (efficiency 0..1, reference constant used).
    """
    a_m, speed = magnus_acceleration(df)
    omega = _f(df["release_spin_rate"]) * 2 * np.pi / 60.0
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = a_m / (speed * omega)
    if reference is None:
        ff = np.asarray(df["pitch_type"]) == "FF"
        reference = float(np.nanpercentile(ratio[ff], 98))
    eff = np.clip(ratio / reference, 0, 1)
    eff[(_f(df["release_spin_rate"]) < 600) | ~np.isfinite(eff)] = np.nan  # knuckleballs etc.
    return eff, reference


def seam_shifted_wake(df: pd.DataFrame, min_break_in: float = 4.0) -> np.ndarray:
    """Seam-shifted wake as an angle (deg): observed spin axis vs. movement axis.

    Statcast's `spin_axis` is the axis measured by Hawk-Eye. If only Magnus
    acted, the ball would move exactly perpendicular to that axis. The gap
    between where spin says the ball should move and where it actually moved
    is the signature of seam-shifted wake. 30 deg = one hour on a clock face.

    Sign is mirrored for left-handers so both read on the same scale.
    Pitches with tiny total movement get NaN (direction is undefined).
    """
    px, pz = _f(df["pfx_x"]), _f(df["pfx_z"])
    movement_axis = np.degrees(np.arctan2(px, -pz)) % 360
    dev = ((_f(df["spin_axis"]) - movement_axis + 180) % 360) - 180
    dev = dev * np.where(np.asarray(df["p_throws"]) == "L", -1.0, 1.0)
    dev[np.hypot(px, pz) * INCH < min_break_in] = np.nan
    return dev


def axis_to_clock(deg) -> list[str]:
    """Statcast spin axis (deg) -> clock-face tilt, e.g. 180 -> '12:00'."""
    out = []
    for d in np.asarray(deg, dtype="float64"):
        if not np.isfinite(d):
            out.append("—")
            continue
        minutes = ((d - 180) % 360) * 2  # 1 deg = 2 minutes; 180 deg (backspin) = 12:00
        h, m = divmod(int(round(minutes)) % 720, 60)
        out.append(f"{12 if h == 0 else h}:{m:02d}")
    return out


# ---------------------------------------------------------------------------
# Tunneling
# ---------------------------------------------------------------------------

def tunnel_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Consecutive pitch pairs of *different* types within the same at-bat.

    For each pair we compute where the two balls were at the batter's decision
    point (175 ms before the plate) and at the plate. Great tunnels look the
    same at decision time and finish far apart.

    Requires game_pk, at_bat_number, pitch_number.
    """
    d = df.sort_values(["game_pk", "at_bat_number", "pitch_number"]).copy()
    t_plate = time_to_y(d["vy0"], d["ay"], Y_PLATE)
    xd, _, zd = position_at_time(d, t_plate - DECISION_TIME)
    d["x_dec"], d["z_dec"] = xd, zd
    d["x_pl"], d["z_pl"] = _f(d["plate_x"]), _f(d["plate_z"])

    key = ["game_pk", "at_bat_number"]
    prev = d.groupby(key)[["pitch_type", "x_dec", "z_dec", "x_pl", "z_pl"]].shift(1)
    m = prev["pitch_type"].notna() & (prev["pitch_type"] != d["pitch_type"])
    out = pd.DataFrame({
        "pitcher": d.loc[m, "pitcher"],
        "game_year": d.loc[m, "game_year"],
        "prev_type": prev.loc[m, "pitch_type"],
        "pitch_type": d.loc[m, "pitch_type"],
        "tunnel_in": np.hypot(d.loc[m, "x_dec"] - prev.loc[m, "x_dec"], d.loc[m, "z_dec"] - prev.loc[m, "z_dec"]) * INCH,
        "plate_in": np.hypot(d.loc[m, "x_pl"] - prev.loc[m, "x_pl"], d.loc[m, "z_pl"] - prev.loc[m, "z_pl"]) * INCH,
    })
    out["break_tunnel_ratio"] = out["plate_in"] / out["tunnel_in"].clip(lower=1.0)
    return out


# ---------------------------------------------------------------------------
# One call for the pitch-level feature table
# ---------------------------------------------------------------------------

def add_physics(df: pd.DataFrame, spin_reference: float | None = None) -> tuple[pd.DataFrame, float]:
    out = df.copy()
    mv = movement(out)
    out["ivb"], out["hb"] = mv["ivb"], mv["hb"]
    out["vaa"], out["haa"] = approach_angles(out)
    out["flight_time"] = flight_time(out)
    out["spin_eff"], ref = spin_efficiency(out, spin_reference)
    out["ssw_deg"] = seam_shifted_wake(out)
    out["pitch_family"] = out["pitch_type"].map(PITCH_FAMILIES).fillna("other")
    return out, ref
