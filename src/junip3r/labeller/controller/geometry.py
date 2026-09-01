from junip3r.labeller.data.types.abc import Point


def is_inside_image01(p: Point) -> bool:
    x, y = p
    return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0


def clamp_to_image01(p: Point) -> Point:
    x, y = p
    return max(0.0, min(1.0, x)), max(0.0, min(1.0, y))
