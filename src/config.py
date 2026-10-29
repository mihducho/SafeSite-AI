"""Doc file cau hinh chung configs/settings.yaml.

Tra ve dict long nhau dung nhu trong file YAML; rieng cac duong dan
(model.weights, paths.*) duoc doi thanh Path tuyet doi tinh tu thu muc goc du
an, de script chay o thu muc nao cung dung.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS = ROOT / "configs" / "settings.yaml"

# Cac khoa bat buoc phai co, de loi cau hinh lo ra ngay khi khoi dong thay vi giua chung.
REQUIRED_KEYS = {
    "model": ["weights", "imgsz", "conf", "iou", "person_class"],
    "ppe": ["items", "required", "min_inside", "upright_min_ratio", "whole_box_region", "contain_thresh",
            "group_max_x_overlap"],
    "checkpoint": ["timeout_s", "min_person_height_px", "top_edge_margin_px", "multi_person_ratio", "min_valid_frames",
                   "present_ratio", "absent_ratio", "snapshot_jpeg_quality"],
    "camera": ["webcam_width", "webcam_height", "first_frame_timeout_s", "reconnect_delay_s", "loop_video", "rotate",
               "url_open_timeout_s", "url_read_timeout_s"],
    "face": ["detector_model", "recognizer_model", "score_threshold", "nms_threshold", "opencv_threads", "enroll_min_score",
             "min_face_px", "multi_min_px", "multi_min_ratio", "quality_full_width_px", "max_vectors",
             "match_threshold", "match_margin", "min_samples", "max_samples", "enroll_long_side"],
    "gate": ["idle_long_side", "idle_max_fps", "trigger_frames", "cooldown_seconds", "empty_seconds",
             "result_display_seconds", "source", "zone_name", "stream_fps", "stream_long_side", "stream_jpeg_quality"],
    "attendance": ["duplicate_minutes", "missing_checkout_hours", "timezone", "default_shift"],
    "web": ["session_hours", "page_size", "max_page_size", "max_upload_mb", "gate_result_seconds"],
    "evaluation": ["sample_fps", "fps_probe_frames", "video_exts", "answer_prefixes", "condition_prefixes"],
    "paths": ["snapshot_dir", "gates_file", "checkpoint_runs", "tracker_config", "eval_videos", "eval_answers",
              "eval_runs", "enroll_images", "face_gallery", "face_thumbs", "gate_runs", "check_images", "face_samples"],
}
ITEM_KEYS = ["class_name", "region", "missing_code"]  # moi mon trong ppe.items


def project_path(p: str | Path) -> Path:
    """Duong dan tuong doi -> tuyet doi theo thu muc goc du an; duong dan tuyet doi giu nguyen."""
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def load_settings(path: str | Path = DEFAULT_SETTINGS) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file cau hinh: {path}")
    with open(path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    for section, keys in REQUIRED_KEYS.items():
        missing = [k for k in keys if k not in settings.get(section, {})]
        if missing:
            raise KeyError(f"File cau hinh {path} thieu {section}.{', '.join(missing)}")
    for name, item in settings["ppe"]["items"].items():
        missing = [k for k in ITEM_KEYS if k not in item]
        if missing:
            raise KeyError(f"File cau hinh {path} thieu ppe.items.{name}.{', '.join(missing)}")
    unknown = [name for name in settings["ppe"]["required"] if name not in settings["ppe"]["items"]]
    if unknown:
        raise KeyError(f"ppe.required co mon chua khai bao trong ppe.items: {unknown}")

    settings["model"]["weights"] = project_path(settings["model"]["weights"])
    for key in ("detector_model", "recognizer_model"):
        settings["face"][key] = project_path(settings["face"][key])
    settings["paths"] = {k: project_path(v) for k, v in settings["paths"].items()}
    return settings
