import pytest

from backend.app.llm.client import (
    LLMClient,
    LLMNotConfigured,
    ground_scores,
    keep_known_ids,
    parse_json_content,
    route_model,
)


def test_parse_json_from_fenced_reply():
    parsed = parse_json_content('Here you go:\n```json\n{"keyword": "pizza"}\n```')
    assert parsed["keyword"] == "pizza"


def test_unknown_menu_ids_are_dropped():
    assert keep_known_ids(["v_1", "invented", "v_1"], {"v_1", "v_2"}) == ["v_1"]


def test_groundedness_cannot_exceed_real_ids():
    scores = ground_scores(
        {"groundedness": 1, "dietary_fit": 0.8, "safety": 1, "notes": "ok"},
        cited_item_ids=["v_1", "invented"],
        allowed_item_ids={"v_1"},
    )
    assert scores["groundedness"] == 0.5
    assert scores["dietary_fit"] == 0.8


def test_group_orders_use_the_phd_reasoner():
    assert "claude" in route_model("group lunch", group_size=6)
    assert "llama" in route_model("pizza", group_size=1)


@pytest.mark.asyncio
async def test_missing_api_key_is_explicit():
    client = LLMClient(api_key="")
    with pytest.raises(LLMNotConfigured):
        await client.complete("meta-llama/llama-3.3-70b-instruct", "system", "user")
