from junip3r.labeller.controller.geometry import clamp_to_image01, is_inside_image01


# --- is_inside_image01 ------------------------------------------------------------

def test_is_inside_image01_true_for_a_point_within_bounds():
    assert is_inside_image01((0.5, 0.5)) is True


def test_is_inside_image01_true_on_the_boundary():
    assert is_inside_image01((0.0, 0.0)) is True
    assert is_inside_image01((1.0, 1.0)) is True


def test_is_inside_image01_false_when_either_axis_is_outside():
    assert is_inside_image01((-0.1, 0.5)) is False
    assert is_inside_image01((0.5, 1.1)) is False
    assert is_inside_image01((-0.1, 1.1)) is False


# --- clamp_to_image01 -------------------------------------------------------------

def test_clamp_to_image01_leaves_a_point_within_bounds_unchanged():
    assert clamp_to_image01((0.3, 0.7)) == (0.3, 0.7)


def test_clamp_to_image01_clamps_each_axis_independently():
    assert clamp_to_image01((-0.5, 1.5)) == (0.0, 1.0)
    assert clamp_to_image01((1.5, -0.5)) == (1.0, 0.0)


def test_clamp_to_image01_clamps_a_point_beyond_a_corner_to_that_corner():
    assert clamp_to_image01((-2.0, -2.0)) == (0.0, 0.0)
    assert clamp_to_image01((2.0, 2.0)) == (1.0, 1.0)
