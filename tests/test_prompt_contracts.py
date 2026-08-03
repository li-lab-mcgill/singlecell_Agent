import unittest

from prompts import literature_prompts as p


LITERATURE_SUMMARY_KEYS = {
    "title",
    "published",
    "abstract",
    "methods",
    "results",
    "discussion",
    "figure_captions",
}


class LiteraturePromptContractTests(unittest.TestCase):
    def test_literature_prompts_format_contract(self):
        fill = {k: "x" for k in LITERATURE_SUMMARY_KEYS}
        p.LITERATURE_SUMMARY_PROMPT.format(**fill)
        p.RAG_CONTEXT_PAPER_SUMMARY.format(**fill)
        self.assertTrue(p.LITERATURE_SUMMARY_SYSTEM.strip())


def test_mediator_prompts_contract():
    from prompts import mediator_prompts as m

    for name in (
        "MEDIATOR_SHARED_SYSTEM",
        "MEDIATOR_FORMULATION_PROMPT",
        "MEDIATOR_POST_ANALYSIS_PROMPT",
        "MEDIATOR_ADVERSARY_REVISION_PROMPT",
    ):
        val = getattr(m, name)
        assert isinstance(val, str) and val.strip(), f"{name} empty"
    # output tag contract used by the parsers must survive refinement
    assert "MEDIATOR_POST_ANALYSIS" in m.MEDIATOR_POST_ANALYSIS_PROMPT
    # post-analysis decision vocabulary the loop switches on
    for token in ("self_revise_plan", "continue_from_node_id"):
        assert token in m.MEDIATOR_POST_ANALYSIS_PROMPT


def test_panelist_prompts_contract():
    from prompts import panelist_prompts as p2

    for name in (
        "PANELIST_SHARED_SYSTEM",
        "BIOLOGIST_ROUND1_PROMPT",
        "STATISTICIAN_ROUND1_PROMPT",
        "BIOINFORMATICIAN_ROUND1_PROMPT",
        "PANELIST_CALLBACK_PROMPT",
        "PANEL_OUTPUT_SCHEMA",
    ):
        val = getattr(p2, name)
        assert isinstance(val, str) and val.strip(), f"{name} empty"
    # schema keys the panelist-output parser reads must appear once, via the shared constant
    for key in ("intents", "papers_selected", "confidence", "novelty_type"):
        assert key in p2.PANEL_OUTPUT_SCHEMA
    # each role prompt must embed the shared schema (composed in, not re-pasted)
    for role_prompt in (
        p2.BIOLOGIST_ROUND1_PROMPT,
        p2.STATISTICIAN_ROUND1_PROMPT,
        p2.BIOINFORMATICIAN_ROUND1_PROMPT,
    ):
        assert p2.PANEL_OUTPUT_SCHEMA.strip() in role_prompt


if __name__ == "__main__":
    unittest.main()
