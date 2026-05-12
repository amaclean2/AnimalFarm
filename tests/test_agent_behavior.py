import pytest
from test_cases import TEST_CASES
from conftest import setup_scenario, run_until


@pytest.mark.parametrize("tc", TEST_CASES, ids=[tc.name for tc in TEST_CASES])
def test_scenario(tc):
    world, sim, agent = setup_scenario(tc)
    stop = tc.stop_when or (lambda w, t: False)
    tick = run_until(sim, world, stop, tc.max_ticks)
    assert tc.assert_fn(world, agent, tick), tc.failure_message
