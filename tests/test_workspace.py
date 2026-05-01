from pathlib import Path

from snapgraph.workspace import Workspace, create_workspace, required_workspace_paths


def test_create_workspace_is_idempotent(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)

    create_workspace(workspace)
    create_workspace(workspace)

    for path in required_workspace_paths(workspace):
        assert path.exists()

    assert (workspace.wiki_dir / "sources").exists()
    assert workspace.index_path.read_text(encoding="utf-8").startswith("# SnapGraph Index")
    assert workspace.log_path.read_text(encoding="utf-8").startswith("# SnapGraph Log")
    assert workspace.schema_agents_path.exists()


def test_create_workspace_does_not_overwrite_existing_index_or_log(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    workspace.index_path.write_text("# Custom Index\n", encoding="utf-8")
    workspace.log_path.write_text("# Custom Log\n", encoding="utf-8")

    create_workspace(workspace)

    assert workspace.index_path.read_text(encoding="utf-8") == "# Custom Index\n"
    assert workspace.log_path.read_text(encoding="utf-8") == "# Custom Log\n"
