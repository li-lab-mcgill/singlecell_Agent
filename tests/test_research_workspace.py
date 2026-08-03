from __future__ import annotations

from agents.research_workspace import ResearchWorkspace


def test_research_workspace_reuses_active_state_for_follow_up(tmp_path):
    workspace = ResearchWorkspace(root_dir=tmp_path / "runs", conversation_id="C001")

    first = workspace.resolve_research_state(
        user_message="Find disease-associated CREs.",
        resolved_intent="Find disease-associated CREs in the multiome data.",
        data_summary={"modality": "multiome"},
        session_context={},
    )
    second = workspace.resolve_research_state(
        user_message="Now check whether those CREs overlap GWAS loci.",
        resolved_intent="Check whether the previously identified CREs overlap GWAS loci.",
        data_summary={"modality": "multiome"},
        session_context={},
    )

    assert first.decision["action"] == "create_new"
    assert second.decision["action"] == "continue_active"
    assert second.decision["research_state_id"] == first.decision["research_state_id"]


def test_research_workspace_creates_new_state_for_explicit_new_task(tmp_path):
    workspace = ResearchWorkspace(root_dir=tmp_path / "runs", conversation_id="C001")

    first = workspace.resolve_research_state(
        user_message="Find disease-associated CREs.",
        resolved_intent="Find disease-associated CREs in the multiome data.",
        data_summary={"modality": "multiome"},
        session_context={},
    )
    second = workspace.resolve_research_state(
        user_message="Start a new separate analysis for cell type annotation.",
        resolved_intent="Run a separate cell type annotation analysis.",
        data_summary={"modality": "multiome"},
        session_context={},
    )

    assert second.decision["action"] == "create_new"
    assert second.decision["research_state_id"] != first.decision["research_state_id"]
