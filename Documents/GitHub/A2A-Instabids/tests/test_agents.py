from instabids.agents.factory import get_homeowner_agent


def test_homeowner_has_tools():
    agent = get_homeowner_agent()
    names = {t.name for t in agent.tools}
    assert "create_bid" in names and "get_profile" in names
