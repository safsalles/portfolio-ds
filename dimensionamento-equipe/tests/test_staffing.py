import pandas as pd
import pytest

from src.config import Premissas, Scenario
from src.staffing import scenario_cost, staffing_plan


def prem(scenarios):
    return Premissas(360, 0.30, tuple(scenarios), 0.30, 2022, 2023)


def fc():
    idx = pd.date_range("2023-03-01", periods=6, freq="h", tz="UTC")
    return pd.Series([0, 10, 50, 100, 200, 400], index=idx, dtype=float)


P = prem([Scenario("80/20", 0.8, 20), Scenario("90/30", 0.9, 30)])


def test_plan_shape():
    plan = staffing_plan(fc(), P)
    assert len(plan) == 6 * 2
    assert set(plan.columns) >= {"hour", "scenario", "calls", "agents_present", "agents_scheduled"}


def test_zero_calls_zero_agents():
    plan = staffing_plan(fc(), P)
    z = plan[plan["calls"] == 0]
    assert (z["agents_present"] == 0).all() and (z["agents_scheduled"] == 0).all()


def test_scheduled_ge_present():
    plan = staffing_plan(fc(), P)
    assert (plan["agents_scheduled"] >= plan["agents_present"]).all()


def test_stricter_target_costs_more_same_window():
    p = prem([Scenario("80/20", 0.8, 20), Scenario("90/20", 0.9, 20)])
    cost = scenario_cost(staffing_plan(fc(), p)).set_index("scenario")
    assert cost.loc["90/20", "agent_hours_present"] >= cost.loc["80/20", "agent_hours_present"]


def test_scenario_cost_sums():
    plan = staffing_plan(fc(), P)
    cost = scenario_cost(plan).set_index("scenario")
    s = plan[plan["scenario"] == "80/20"]
    assert cost.loc["80/20", "agent_hours_present"] == s["agents_present"].sum()
    assert cost.loc["80/20", "peak_scheduled"] == s["agents_scheduled"].max()
