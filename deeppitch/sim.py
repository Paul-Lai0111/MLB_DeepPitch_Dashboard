"""Forward model for the Physics Lab: build a pitch from what a pitcher controls.

The force model is deliberately the same one the data pipeline inverts:
  * gravity, straight down
  * drag, opposing the flight, a_drag = KD * v^2
  * Magnus lift, perpendicular to the flight, a_M = SPIN_REF * v * omega * efficiency,
    pointed by the spin axis (Statcast convention: 180 deg = pure backspin)
SPIN_REF is the calibration constant measured from 2M real pitches.
Accelerations are held constant over the flight, exactly like Statcast's 9-parameter fit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from deeppitch import physics as ph

KD = 0.00155            # ft^-1, gives ay ~ 28 ft/s^2 at 95 mph, matching Statcast fits
PFX_SCALE = 1 / 0.914   # Statcast pfx vs 0.5*a*t^2 over the y=50 ft -> plate window (measured)


def clock_to_axis(hours: float) -> float:
    """Clock tilt (12:00 = backspin) -> Statcast spin_axis degrees."""
    return (180 + 30 * hours) % 360


def simulate(velo: float, spin: float, eff: float, tilt_hours: float, rel_z: float, rel_x: float,
             ext: float, target_x: float, target_z: float, spin_ref: float, hand: str = "R") -> dict:
    v = velo * 1.46667
    omega = spin * 2 * np.pi / 60
    axis = np.radians(clock_to_axis(tilt_hours))
    v_mid = 0.95 * v
    a_m = spin_ref * v_mid * omega * eff
    ax_m, az_m = a_m * np.sin(axis), -a_m * np.cos(axis)
    ay = KD * v_mid**2
    ax, az = ax_m, az_m - ph.G

    y_rel = 60.5 - ext
    vy = -v
    # time from release to the front of the plate
    disc = vy**2 - 2 * ay * (y_rel - ph.Y_PLATE)
    t = (-vy - np.sqrt(disc)) / ay
    vx_r = (target_x - rel_x - 0.5 * ax * t**2) / t
    vz_r = (target_z - rel_z - 0.5 * az * t**2) / t
    # restate at Statcast's y = 50 ft reference plane
    disc50 = vy**2 - 2 * ay * (y_rel - ph.Y_REF)
    t50 = (-vy - np.sqrt(disc50)) / ay
    row = dict(vx0=vx_r + ax * t50, vy0=vy + ay * t50, vz0=vz_r + az * t50, ax=ax, ay=ay, az=az,
               plate_x=target_x, plate_z=target_z, release_extension=ext)
    one = pd.DataFrame([row])
    vaa, haa = ph.approach_angles(one)
    t_win = float(ph.time_to_y(one["vy0"], one["ay"], ph.Y_PLATE)[0])
    sign = -1.0 if hand == "R" else 1.0
    tr = ph.trajectory(row, n=80)
    return {
        "row": row, "traj": tr,
        "ivb": 0.5 * az_m * t_win**2 * PFX_SCALE * ph.INCH,
        "hb": 0.5 * ax_m * t_win**2 * PFX_SCALE * ph.INCH * sign,
        "vaa": float(vaa[0]), "haa": float(haa[0]), "flight_ms": t * 1000,
        "lift_saved_in": float((tr["z"].iloc[-1] - tr["z_nospin"].iloc[-1]) * ph.INCH),
        "useful_spin": spin * eff, "magnus_g": a_m / ph.G,
    }
