"""Model feature names shared by the training pipeline and the app (no ML imports here)."""

FEATURES = [
    "release_speed", "release_spin_rate", "spin_eff", "ivb", "hb",
    "release_extension", "release_pos_z", "release_side", "arm_angle",
    "ssw_deg", "velo_diff", "ivb_diff", "hb_diff", "pitch_type_code", "same_hand",
]
FEATURE_LABELS = {
    "release_speed": ("Velocity", "球速"), "release_spin_rate": ("Spin rate", "轉速"),
    "spin_eff": ("Spin efficiency", "旋轉效率"), "ivb": ("Induced vertical break", "誘發垂直位移"),
    "hb": ("Horizontal break", "水平位移"), "release_extension": ("Extension", "延伸距離"),
    "release_pos_z": ("Release height", "出手高度"), "release_side": ("Release side", "出手側向位置"),
    "arm_angle": ("Arm angle", "手臂角度"), "ssw_deg": ("Seam-shifted wake", "縫線偏移尾流"),
    "velo_diff": ("Velo gap vs fastball", "與速球球速差"), "ivb_diff": ("Rise gap vs fastball", "與速球垂直位移差"),
    "hb_diff": ("Run gap vs fastball", "與速球水平位移差"), "pitch_type_code": ("Pitch type", "球種"),
    "same_hand": ("Same-hand matchup", "同側對決"),
}
