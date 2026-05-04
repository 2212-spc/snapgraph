from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app
from snapgraph.demo_data import DEMO_WHYS
from snapgraph.focus import focus_graph_for_payload
from snapgraph.ingest import ingest_source
from snapgraph.models import DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID
from snapgraph.spaces import create_graph_space
from snapgraph.workspace import Workspace, create_workspace


def test_focus_graph_for_question_is_local_and_prioritizes_user_guided(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)

    focus = focus_graph_for_payload(
        workspace,
        {"question": "我为什么要从 LLM Wiki 开始？", "space_id": DEFAULT_GRAPH_SPACE_ID},
    )

    assert 0 < len(focus["nodes"]) <= 18
    assert len(focus["edges"]) < 65
    assert focus["evidence_cards"]
    assert focus["evidence_cards"][0]["why_saved_status"] == "user-stated"
    assert focus["confidence_summary"]["user_stated"] >= 1
    assert focus["open_loops"]


def test_focus_graph_respects_space_filter(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    create_graph_space(workspace, name="Product Insights", purpose="product value")
    product = tmp_path / "product.md"
    product.write_text("# Product Memory\n\nProduct value and graph recall.\n", encoding="utf-8")
    ingest_source(
        workspace,
        product,
        why="Product value.",
        space_id="product_insights",
    )

    default_focus = focus_graph_for_payload(
        workspace,
        {"question": "Product Memory", "space_id": DEFAULT_GRAPH_SPACE_ID},
    )
    product_focus = focus_graph_for_payload(
        workspace,
        {"question": "Product Memory", "space_id": "product_insights"},
    )

    assert default_focus["nodes"] == []
    assert product_focus["nodes"]
    assert all(node["graph_space_id"] == "product_insights" for node in product_focus["nodes"])


def test_api_focus_and_ask_return_focus_graph(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    focus = client.post(
        "/api/focus",
        json={"question": "我为什么要从 LLM Wiki 开始？", "space_id": DEFAULT_GRAPH_SPACE_ID},
    )
    ask = client.post(
        "/api/ask",
        json={"question": "我为什么要从 LLM Wiki 开始？", "space_id": DEFAULT_GRAPH_SPACE_ID},
    )

    assert focus.status_code == 200
    assert ask.status_code == 200
    assert 0 < len(focus.json()["nodes"]) <= 18
    assert "focus_graph" in ask.json()
    assert ask.json()["focus_graph"]["evidence_cards"]


def test_api_ingest_returns_capture_review_focus_graph(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/ingest",
        files={"file": ("capture.md", b"# Capture\n\nA capture for routing.\n", "text/markdown")},
        data={"why": "Review capture routing."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_space_id"] == INBOX_GRAPH_SPACE_ID
    assert payload["focus_graph"]["nodes"]
    assert payload["routing_suggestion"]


def _workspace_with_demo_sources(tmp_path: Path) -> Workspace:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    for source_path in sorted(demo_dir.glob("*.md")):
        ingest_source(
            workspace,
            source_path,
            why=DEMO_WHYS.get(source_path.name),
            space_id=DEFAULT_GRAPH_SPACE_ID,
        )
    return workspace
