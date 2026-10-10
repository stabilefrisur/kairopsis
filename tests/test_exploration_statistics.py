"""Independent hand-worked numerical oracles, including exact sample evidence."""

from copy import deepcopy
import json
from math import exp, pi, sqrt

import pytest

from kairopsis.exploration_statistics import summarize


def row(identifier, symbol="A", day=1, **values):
    return {"id": identifier, "symbol": symbol, "date": f"2026-10-{day:02}", "values": values}


def cell(result, left, right):
    return next(item for item in result["cells"] if item["left"] == left and item["right"] == right)


def test_history_uses_raw_rows_and_preserves_missing_values_without_mutation():
    rows = [row("late", day=3, spread=5), row("early", day=1, spread=0), row("gap", day=2, spread=None)]
    original = deepcopy(rows)
    result = summarize("history", rows, {"axes": ["spread"]})
    assert rows == original
    trace = result["traces"][0]
    assert trace["y"] == [0, None, 5]
    assert [data[0] for data in trace["customdata"]] == ["early", "gap", "late"]
    assert trace["connectgaps"] is False
    assert "title" not in result["layout"]["xaxis"]


def test_history_preserves_units_and_forces_separate_aligned_scales_for_mixed_fields():
    rows = [row("a", day=1, spread=100, duration=3), row("b", day=2, spread=120, duration=4)]
    result = summarize("history", rows, {"axes": ["spread", "duration"], "units": {"spread": "bp", "duration": "years"}})
    assert [trace["name"] for trace in result["traces"]] == ["A · spread (bp)", "A · duration (years)"]
    assert [trace["yaxis"] for trace in result["traces"]] == ["y", "y2"]
    assert result["layout"]["yaxis"]["title"] == "spread (bp)"
    assert result["layout"]["yaxis2"]["title"] == "duration (years)"
    assert result["layout"]["xaxis2"]["matches"] == "x"
    assert "title" not in result["layout"]["xaxis2"]
    assert result["layout"]["grid"]["rows"] == 2
    assert result["algorithm"]["scale_policy"] == "independent-aligned"


def test_history_can_overlay_comparable_fields_or_split_same_field_by_symbol():
    rows = [row("a", "A", spread=10, yield_bp=20), row("b", "B", spread=30, yield_bp=40)]
    overlay = summarize("history", rows, {"axes": ["spread", "yield_bp"], "units": {"spread": "bp", "yield_bp": "bp"}})
    assert all(trace["yaxis"] == "y" for trace in overlay["traces"])
    assert overlay["layout"]["yaxis"]["title"] == "bp" and "grid" not in overlay["layout"]
    split = summarize("history", rows, {"axes": ["spread"], "units": {"spread": "bp"}, "history_layout": "small_multiples"})
    assert [trace["yaxis"] for trace in split["traces"]] == ["y", "y2"]
    assert split["layout"]["grid"]["rows"] == 2
    unknown = summarize("history", rows, {"axes": ["spread", "yield_bp"]})
    assert unknown["algorithm"]["scale_policy"] == "independent-aligned"


def test_ols_hand_worked_slope_intercept_residuals_and_r_squared():
    # Centered X=[-1,0,1]; centered Y=[-2/3,1/3,1/3].
    # Sxy=1, Sxx=2, Syy=2/3; SSE=1/6; R²=3/4.
    rows = [row("zero", x=0, y=1), row("one", x=1, y=2), row("two", x=2, y=2), row("missing", x=None, y=9)]
    result = summarize("scatter", rows, {"axes": ["x", "y"], "descriptive_fit": True, "units": {"x": "years", "y": "bp"}})
    fit = result["fit"]
    assert fit["slope"] == pytest.approx(.5)
    assert fit["intercept"] == pytest.approx(7 / 6)
    assert fit["r_squared"] == pytest.approx(.75)
    assert [item["residual"] for item in fit["residuals"]] == pytest.approx([-1 / 6, 1 / 3, -1 / 6])
    assert fit["row_ids"] == result["paired_row_ids"] == ["zero", "one", "two"]
    assert fit["units"] == {"x": "years", "y": "bp"}
    assert all(not item["extrapolation"] for item in fit["residuals"])


def test_separate_fit_sample_does_not_fit_displayed_outlier_and_reports_extrapolation():
    fitted = [row("f0", x=0, y=1), row("f1", x=1, y=3), row("f2", x=2, y=5)]
    displayed = [row("evaluation", x=3, y=8)]
    result = summarize("scatter", displayed, {"axes": ["x", "y"], "fit": True, "fit_rows": fitted})
    assert result["row_ids"] == ["evaluation"]
    fit = result["fit"]
    assert fit["sample"] == "separate" and fit["row_ids"] == ["f0", "f1", "f2"]
    assert fit["slope"] == 2 and fit["intercept"] == 1
    assert fit["residuals"] == [{"row_id": "evaluation", "predicted": 7, "residual": 1, "extrapolation": True}]


@pytest.mark.parametrize("rows,reason", [([], "at least two"), ([row("1", x=1, y=2)], "at least two"),
    ([row("1", x=1, y=2), row("2", x=1, y=3)], "constant")])
def test_unavailable_fit_is_honest(rows, reason):
    result = summarize("scatter", rows, {"axes": ["x", "y"], "fit": True})
    assert result["fit"]["slope"] is None
    assert reason in result["fit"]["unavailable_reason"]


def test_panel_requires_explicit_fit_pooling_and_constant_y_has_no_r_squared():
    rows = [row("1", "A", 1, x=1, y=2), row("2", "B", 2, x=2, y=2)]
    options = {"axes": ["x", "y"], "fit": True, "shape": "panel"}
    assert "pooling" in summarize("scatter", rows, options)["fit"]["unavailable_reason"]
    fitted = summarize("scatter", rows, {**options, "allow_pooled_fit": True})["fit"]
    assert fitted["slope"] == 0 and fitted["intercept"] == 2 and fitted["r_squared"] is None


def test_ranked_average_ties_keeps_zero_negative_and_missing_separate():
    rows = [row("a", spread=10, start=2), row("b", spread=10, start=1), row("c", spread=0, start=4),
        row("d", spread=-2, start=3), row("missing", spread=None)]
    result = summarize("ranking", rows, {"axes": ["spread", "start"], "units": {"spread": "bp", "start": "bp"}})
    assert [item["rank"] for item in result["ranks"]] == [1.5, 1.5, 3, 4]
    assert result["traces"][1]["y"] == [2, 1, 4, 3]
    assert [item["row_id"] for item in result["ranks"]] == ["a", "b", "c", "d"]


@pytest.mark.parametrize("units", [{"spread": "bp", "duration": "years"}, {"spread": "bp"}, {}])
def test_ranked_second_field_never_shares_scale_with_incompatible_or_unknown_units(units):
    rows = [row("a", spread=10, duration=2), row("b", spread=20, duration=1)]
    result = summarize("ranking", rows, {"axes": ["spread", "duration"], "units": units})
    assert [(entry["row_id"], entry["rank"], entry["value"]) for entry in result["ranks"]] == [("b", 1, 20), ("a", 2, 10)]
    assert len(result["traces"]) == 1
    assert "duration markers omitted: incompatible or unknown units for the ranking scale" in result["limitations"]


def test_ranked_interval_return_displays_retained_original_endpoints_separately():
    rows = [row("a", "A", spread=10), row("b", "B", spread=-20)]
    rows[0].update(bindings={"spread": "binding-a"}, endpoints={"spread": {"start_value": 100, "end_value": 110,
        "start_date": "2026-09-01", "end_date": "2026-10-01"}})
    rows[1].update(bindings={"spread": "binding-b"}, endpoints={"spread": {"start_value": 200, "end_value": 160,
        "start_date": "2026-09-01", "end_date": "2026-10-01"}})
    result = summarize("ranked", rows, {"axes": ["spread"], "units": {"spread": "%"}, "interval_measure": "return",
        "measure_metadata": {"binding-a": {"unit": "bp"}, "binding-b": {"unit": "bp"}}})
    assert result["traces"][0]["y"] == [10, -20]
    assert result["layout"]["yaxis"]["title"] == "Interval percentage change · spread (%)"
    assert result["paired_endpoints"][0] == {"row_id": "a", "symbol": "A", "ranked_value": 10, "rank": 1,
        "start_value": 100, "end_value": 110, "start_date": "2026-09-01", "end_date": "2026-10-01", "unit": "bp"}
    assert result["traces"][1]["y"] == [100, 200] and result["traces"][2]["y"] == [110, 160]
    assert result["traces"][1]["customdata"][0] == ["a", "A", "2026-09-01", "start"]
    assert result["traces"][2]["customdata"][0] == ["a", "A", "2026-10-01", "end"]
    assert result["layout"]["yaxis2"]["title"] == "Retained start / end levels (bp)"
    assert result["traces"][3]["y"] == [100, 110, None, 200, 160, None]


def test_ranked_missing_endpoint_stays_unavailable_and_never_reconstructs_baseline():
    rows = [row("a", spread=10), row("b", spread=20)]
    rows[0]["endpoints"] = {"spread": {"start_value": None, "end_value": 100}}
    rows[1]["endpoints"] = {"spread": {"start_value": 0, "end_value": 20}}
    result = summarize("ranked", rows, {"axes": ["spread"], "units": {"spread": "bp"}})
    assert result["traces"][0]["y"] == [20, 10]  # Rank by retained difference, not endpoint level.
    assert result["traces"][1]["y"] == [0]
    assert result["paired_endpoints"][1]["start_value"] is None
    assert "1 paired endpoint records unavailable" in result["limitations"]


def test_gaussian_kde_matches_closed_form_at_symmetric_center_and_retains_bandwidth():
    rows = [row(str(index), x=value) for index, value in enumerate([-1, 0, 1])]
    result = summarize("distribution", rows, {"axes": ["x"], "bandwidth": 1, "grid_points": 3})
    group = result["groups"][0]
    assert group["x"] == [-4, 0, 4]
    assert group["density"][1] == pytest.approx((1 + 2 * exp(-.5)) / (3 * sqrt(2 * pi)))
    assert group["bandwidth"] == 1 and group["bandwidth_rule"] == "explicit"
    assert group["row_ids"] == ["0", "1", "2"]
    default = summarize("distribution", rows, {"axes": ["x"]})["groups"][0]
    assert default["bandwidth"] == pytest.approx(3 ** (-.2))  # sample SD is exactly 1.


def test_kde_multiplier_scales_base_bandwidth_once_and_density_matches_formula():
    rows = [row(str(index), x=value) for index, value in enumerate([-1, 0, 1])]
    group = summarize("distribution", rows, {"axes": ["x"], "bandwidth": 1, "bandwidth_multiplier": 2, "grid_points": 3})["groups"][0]
    assert group["base_bandwidth"] == 1 and group["bandwidth_multiplier"] == 2 and group["bandwidth"] == 2
    assert group["density"][1] == pytest.approx((1 + 2 * exp(-.125)) / (6 * sqrt(2 * pi)))
    automatic = summarize("distribution", rows, {"axes": ["x"], "bandwidth_multiplier": .5})["groups"][0]
    assert automatic["bandwidth"] == pytest.approx(.5 * 3 ** (-.2))


@pytest.mark.parametrize("multiplier", [0, -1, float("nan"), float("inf"), True])
def test_invalid_kde_multiplier_is_rejected_even_for_point_samples(multiplier):
    with pytest.raises(ValueError, match="bandwidth_multiplier"):
        summarize("distribution", [row("one", x=1)], {"axes": ["x"], "bandwidth_multiplier": multiplier})


def test_equal_member_kde_weights_and_effective_sample_are_independent_of_row_counts():
    rows = [row("a1", "A", 1, x=-1), row("a2", "A", 2, x=1), row("b", "B", 1, x=0)]
    group = summarize("distribution", rows, {"axes": ["x"], "weight_policy": "equal_member", "bandwidth": 1,
        "grid_points": 3})["groups"][0]
    assert group["weights"] == [.25, .25, .5]
    assert group["effective_count"] == pytest.approx(8 / 3)
    assert group["density"][1] == pytest.approx((.5 + .5 * exp(-.5)) / sqrt(2 * pi))
    automatic = summarize("distribution", rows, {"axes": ["x"], "weight_policy": "equal_member"})["groups"][0]
    # Weighted variance=.5 / (1-.375)=.8.
    assert automatic["bandwidth"] == pytest.approx(sqrt(.8) * (8 / 3) ** (-.2))


def test_shared_kde_uses_same_explicit_smoothing_and_rejects_incomparable_units():
    rows = [row(str(index), "A" if index < 3 else "B", index + 1, spread=value)
        for index, value in enumerate([-1, 0, 1, 10, 12, 14])]
    result = summarize("distribution", rows, {"axes": ["spread"], "group_by": "symbol", "shared_bandwidth": True,
        "bandwidth": 2, "units": {"spread": "bp"}})
    assert [group["bandwidth"] for group in result["groups"]] == [2, 2]
    assert result["algorithm"]["bandwidth_row_ids"] == [str(index) for index in range(6)]
    assert result["algorithm"]["bandwidth_rule"] == "explicit"
    scaled = summarize("distribution", rows, {"axes": ["spread"], "group_by": "symbol", "shared_bandwidth": True,
        "bandwidth": 2, "bandwidth_multiplier": 3, "units": {"spread": "bp"}})
    assert [group["bandwidth"] for group in scaled["groups"]] == [6, 6]
    assert scaled["algorithm"]["bandwidth"] == 6
    incompatible = [row("a", spread=1, duration=2), row("b", spread=2, duration=3), row("c", spread=3, duration=4)]
    with pytest.raises(ValueError, match="comparable known units"):
        summarize("distribution", incompatible, {"axes": ["spread", "duration"], "shared_bandwidth": True,
            "units": {"spread": "bp", "duration": "years"}})


def test_selected_distribution_value_uses_retained_observation_identity():
    rows = [row("one", x=1), row("two", x=2), row("three", x=3)]
    result = summarize("distribution", rows, {"axes": ["x"], "selected_row_id": "two"})
    assert result["groups"][0]["selected_value"] == 2
    assert result["traces"][-1]["x"] == [2]
    assert result["traces"][-1]["customdata"][0][0] == "two"


def test_distribution_defaults_to_latest_actual_row_per_group_at_cutoff():
    rows = [row("old-a", "A", 1, x=1), row("new-a", "A", 3, x=3), row("b", "B", 2, x=2),
        row("later-request-old-observation", "B", 3, x=20), row("future-a", "A", 4, x=4)]
    rows[3]["dates"] = {"x": "2026-10-01"}
    result = summarize("distribution", rows, {"axes": ["x"], "group_by": "symbol", "as_of": "2026-10-03"})
    assert [(group["group"], group["selected_row_id"], group["selected_value"]) for group in result["groups"]] == [
        ("A", "new-a", 3), ("B", "b", 2)]
    assert all(group["selected_value_policy"] == "latest-retained-finite-row" for group in result["groups"])
    explicit = summarize("distribution", rows, {"axes": ["x"], "selected_value": -99})
    assert explicit["groups"][0]["selected_value"] == -99
    assert "selected_row_id" not in explicit["groups"][0]
    unavailable = summarize("distribution", rows, {"axes": ["x"], "selected_row_id": "absent"})
    assert "selected_value" not in unavailable["groups"][0]


def test_scatter_marker_area_legend_units_and_invalid_sizes_are_explicit():
    rows = [row("one", x=1, y=2, amount=1), row("four", x=2, y=4, amount=4),
        row("negative", x=3, y=6, amount=-4), row("missing", x=4, y=8, amount=None)]
    result = summarize("scatter", rows, {"axes": ["x", "y"], "size_by": "amount", "units": {"amount": "USD millions", "y": "bp"}})
    sizes = result["traces"][0]["marker"]["size"]
    assert sizes == [15, 30, 9, 9]
    assert sizes[1] ** 2 / sizes[0] ** 2 == 4  # Disk area, not diameter, matches amount ratio.
    assert result["size_legend"]["values"] == pytest.approx([4 / 9, 16 / 9, 4])
    assert result["size_legend"]["sizes"] == [10, 20, 30]
    assert result["size_legend"]["unit"] == "USD millions"
    assert result["sizing"]["invalid_rows"] == [{"row_id": "negative", "reason": "Negative size"},
        {"row_id": "missing", "reason": "Missing/nonfinite size"}]
    assert result["layout"]["yaxis"]["title"] == "y (bp)"


def test_scatter_numeric_colour_and_supplied_attribute_facets_share_color_scale():
    rows = [row("a", x=1, y=2, rating_number=5), row("b", x=2, y=4, rating_number=10),
        row("c", x=3, y=6, rating_number=None)]
    rows[0]["attributes"] = {"sector": "Banks"}
    rows[1]["attributes"] = {"sector": "Utilities"}
    result = summarize("scatter", rows, {"axes": ["x", "y"], "color_by": "rating_number", "facet_by": "sector"})
    assert [item["name"] for item in result["facets"]] == ["Banks", "Utilities", "Unknown"]
    assert [item["row_ids"] for item in result["facets"]] == [["a"], ["b"], ["c"]]
    assert result["traces"][0]["marker"]["color"] == [5]
    assert result["traces"][1]["marker"]["color"] == [10]
    for trace in result["traces"][:2]:
        assert (trace["marker"]["cmin"], trace["marker"]["cmax"]) == (5, 10)
    assert result["traces"][2]["marker"]["color"] == "#999999"
    assert result["colour"]["missing_row_ids"] == ["c"]
    assert result["layout"]["grid"] == {"rows": 2, "columns": 2, "pattern": "independent"}
    assert result["traces"][1]["xaxis"] == "x2"


def test_categorical_colour_uses_supplied_attribute_and_never_provider_parameters():
    rows = [row("a", x=1, y=2), row("b", x=2, y=4)]
    rows[0]["attributes"] = {"sector": "Banks"}
    rows[1]["params"] = {"sector": "Invented"}
    result = summarize("scatter", rows, {"axes": ["x", "y"], "color_by": "sector"})
    assert [trace["name"] for trace in result["traces"]] == ["Banks", "Unknown"]


@pytest.mark.parametrize("values", [[1], [1, 2], [3, 3, 3]])
def test_tiny_constant_kde_remains_source_points(values):
    rows = [row(str(index), x=value) for index, value in enumerate(values)]
    result = summarize("distribution", rows, {"axes": ["x"]})
    assert "unavailable_reason" in result["groups"][0]
    assert result["traces"][0]["mode"] == "markers"
    assert result["traces"][0]["x"] == values
    assert all(data[0] in result["row_ids"] for data in result["traces"][0]["customdata"])


def test_histogram_edges_counts_density_and_drilldown_match_hand_worked_bins():
    rows = [row(str(index), x=value) for index, value in enumerate([0, 1, 2, 3, 4])]
    group = summarize("distribution", rows, {"axes": ["x"], "distribution": "histogram", "bins": [0, 2, 4]})["groups"][0]
    assert group["counts"] == [2, 3]  # x=2 enters second bin; rightmost x=4 is retained.
    assert group["density"] == pytest.approx([.2, .3])
    assert sum(height * width for height, width in zip(group["density"], group["widths"])) == pytest.approx(1)
    assert group["bin_row_ids"] == [["0", "1"], ["2", "3", "4"]]
    with pytest.raises(ValueError, match="cover"):
        summarize("distribution", rows, {"axes": ["x"], "distribution": "histogram", "bins": [1, 4]})


def test_equal_member_histogram_density_uses_weights_instead_of_counts():
    rows = [row("a1", "A", x=0), row("a2", "A", day=2, x=1), row("b", "B", x=4)]
    group = summarize("distribution", rows, {"axes": ["x"], "distribution": "histogram", "bins": [0, 2, 4],
        "weight_policy": "equal_member"})["groups"][0]
    assert group["counts"] == [2, 1]
    assert group["masses"] == [.5, .5] and group["density"] == [.25, .25]


def test_box_type_seven_quartiles_observed_whiskers_and_outlier_rows():
    rows = [row(str(index), x=value) for index, value in enumerate([0, 1, 2, 3, 4, 5, 100])]
    result = summarize("distribution", rows, {"axes": ["x"], "distribution": "box"})
    group = result["groups"][0]
    assert (group["q1"], group["median"], group["q3"]) == (1.5, 3, 4.5)
    assert (group["lower_fence"], group["upper_fence"]) == (-3, 9)
    assert (group["lower_whisker"], group["upper_whisker"]) == (0, 5)
    assert group["outliers"] == [{"row_id": "6", "value": 100}]
    # Plotly receives precomputed quartiles rather than calculating from raw y.
    assert result["traces"][0]["q1"] == [1.5] and "y" not in result["traces"][0]


def test_equal_member_box_uses_documented_weighted_inverse_cdf():
    rows = [row("a1", "A", x=0), row("a2", "A", day=2, x=1), row("b", "B", x=10)]
    group = summarize("distribution", rows, {"axes": ["x"], "distribution": "box", "weight_policy": "equal_member"})["groups"][0]
    assert (group["q1"], group["median"], group["q3"]) == (0, 1, 10)
    assert group["quartile_rule"] == "weighted-inverse-CDF"


def test_time_heatmap_keeps_missing_cells_and_exact_rows():
    rows = [row("a1", "A", 1, spread=10), row("a2", "A", 2, spread=None), row("b1", "B", 1, spread=20)]
    result = summarize("heatmap", rows, {"axes": ["spread"], "heatmap_layout": "time"})
    assert result["z"] == [[10, None], [20, None]]
    assert [item["row_ids"] for item in result["cells"]] == [["a1"], [], ["b1"], []]
    assert "xaxis" not in result["layout"]


def test_field_heatmap_mean_aggregation_and_separate_unit_scales():
    rows = [row("a1", "A", 1, spread=10, duration=2), row("a2", "A", 2, spread=30, duration=4),
        row("b", "B", 1, spread=40, duration=None)]
    result = summarize("heatmap", rows, {"axes": ["spread", "duration"], "heatmap_layout": "fields",
        "units": {"spread": "bp", "duration": "years"}})
    assert result["z"] == [[20, 3], [40, None]]
    assert result["cells"][0]["row_ids"] == ["a1", "a2"]
    assert result["algorithm"]["scale_policy"] == "separate-columns"
    assert len(result["traces"]) == 2
    assert result["traces"][0]["z"] == [[20], [40]] and result["traces"][1]["z"] == [[3], [None]]


def test_pearson_common_and_pairwise_have_exact_distinct_samples():
    rows = [row("r1", "A", x=1, y=4, z=1), row("r2", "B", x=2, y=1, z=2),
        row("r3", "C", x=3, y=3, z=3), row("r4", "D", x=4, y=2, z=None)]
    common = summarize("correlation", rows, {"axes": ["x", "y", "z"]})
    pairwise = summarize("correlation", rows, {"axes": ["x", "y", "z"], "correlation_sample": "pairwise"})
    assert cell(common, "x", "y")["value"] == pytest.approx(-sqrt(3 / 28))
    assert cell(pairwise, "x", "y")["value"] == pytest.approx(-.4)
    assert cell(common, "x", "y")["row_ids"] == ["r1", "r2", "r3"]
    assert cell(pairwise, "x", "y")["row_ids"] == ["r1", "r2", "r3", "r4"]
    assert cell(pairwise, "x", "z")["count"] == 3
    assert all(item["count"] == 3 for item in common["cells"])


def test_spearman_tied_average_ranks_match_hand_oracle_and_keep_raw_drilldown():
    # X ranks=[1.5,1.5,3,4], Y ranks=[4,2.5,2.5,1].
    # Centered cross-product=-3.75, both squared lengths=4.5 -> -5/6.
    rows = [row(str(i), x=x, y=y) for i, (x, y) in enumerate([(1, 4), (1, 2), (3, 2), (4, 1)])]
    result = summarize("correlation", rows, {"axes": ["x", "y"], "correlation_method": "spearman"})
    target = cell(result, "x", "y")
    assert target["value"] == pytest.approx(-5 / 6)
    assert target["pairs"][0]["x"] == 1 and target["pairs"][0]["y"] == 4
    assert result["algorithm"]["ties"] == "average-rank"


def test_series_correlation_pivots_exact_dates_without_forward_filling():
    rows = [row("a1", "A", 1, spread=1), row("a2", "A", 2, spread=2), row("a3", "A", 3, spread=3),
        row("b1", "B", 1, spread=6), row("b3", "B", 3, spread=2), row("b4", "B", 4, spread=20)]
    result = summarize("correlation", rows, {"axes": ["spread"], "correlation_orientation": "series"})
    target = cell(result, "A", "B")
    assert target["count"] == 2 and target["value"] == pytest.approx(-1)
    assert target["sample_keys"] == ["2026-10-01", "2026-10-03"]
    assert target["row_ids"] == ["a1", "b1", "a3", "b3"]
    assert target["pairs"][0] == {"sample_key": "2026-10-01", "x": 1, "y": 6, "row_ids": ["a1", "b1"]}
    assert result["traces"][0]["customdata"][0][1] == [target["row_ids"], 2]
    pairwise = summarize("correlation", rows, {"axes": ["spread"], "correlation_orientation": "series", "correlation_sample": "pairwise"})
    assert cell(pairwise, "A", "A")["count"] == 3
    assert cell(pairwise, "A", "B")["count"] == 2


def test_correlation_empty_constant_and_nonfinite_cells_never_fabricate_zero():
    rows = [row("a", x=1, y=2, z=None), row("b", x=1, y=3, z=float("inf")), row("c", x=1, y=float("nan"), z=True)]
    result = summarize("correlation", rows, {"axes": ["x", "y", "z"], "correlation_sample": "pairwise"})
    assert cell(result, "x", "y")["value"] is None
    assert cell(result, "x", "y")["unavailable_reason"] == "Constant input"
    assert cell(result, "y", "z")["count"] == 0
    assert cell(result, "y", "z")["unavailable_reason"] == "Fewer than two pairs"
    json.dumps(result, allow_nan=False)


def test_duplicate_sample_identity_is_rejected_instead_of_combined():
    with pytest.raises(ValueError, match="unique"):
        summarize("history", [row("a", x=1), row("a", x=2)])
    with pytest.raises(ValueError, match="one retained row"):
        summarize("correlation", [row("a", x=1), row("b", x=2)], {"axes": ["x"], "correlation_orientation": "series"})


@pytest.mark.parametrize("family", ["history", "scatter", "ranked", "distribution", "heatmap", "correlation"])
def test_every_family_is_strict_json_and_only_uses_retained_source_rows(family):
    rows = [row("retained-a", "A", 1, x=0, y=1), row("retained-b", "B", 2, x=1, y=2), row("retained-c", "C", 3, x=2, y=4)]
    result = summarize(family, rows, {"axes": ["x", "y"], "fit": True})
    assert result["row_ids"] == ["retained-a", "retained-b", "retained-c"]
    json.dumps(result, allow_nan=False)
