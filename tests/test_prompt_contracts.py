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


def test_paper_prompts_format_contract():
    from prompts import paper_prompts as p
    judge_keys = {"role","retrieval_intent","retrieval_goal","base_query","doc_id",
        "source","title","published","url","full_text_status","objective","background",
        "analysis","method_and_dataset","main_findings","benchmark_methods","limitations",
        "figure_captions","abstract"}
    writer_keys = {"doc_id","source","title","published","doi","url","full_text_status",
        "objective","background","analysis","method_and_dataset","main_findings",
        "benchmark_methods","limitations","figure_captions","abstract","retrieval_intent",
        "retrieval_goal","evidence_contribution","covered_evidence_patterns",
        "missing_evidence","source_ids","task_ids","existing_papers_summary"}
    template_keys = {"paper_id","title","doi","url","source_ids_yaml","full_text_status",
        "tasks_yaml","extends_yaml","retrieval_intents_yaml","retrieval_goals_yaml","session",
        "added","objective","background","analysis","method_and_dataset","key_findings",
        "benchmark_methods","limitations","metrics_used","figure_captions","summary"}
    # .format with every key present must not raise (placeholder set preserved, braces escaped)
    p.PAPER_JUDGE_PROMPT.format(**{k: "x" for k in judge_keys})
    p.PAPER_MD_WRITER_PROMPT.format(**{k: "x" for k in writer_keys})
    p.PAPER_MD_TEMPLATE.format(**{k: "x" for k in template_keys})
    assert p.PAPER_JUDGE_SYSTEM.strip() and p.PAPER_MD_WRITER_SYSTEM.strip()


def test_adversarial_prompts_format_contract():
    from prompts import adversarial_prompts as adv

    # .format() with the exact kwargs used at each real call site
    # (agents/adversarial_panelist.py:186 and :163) must not raise — this proves
    # the placeholder set matches the call site and embedded JSON braces are
    # still {{ }}-escaped.
    adv.ADVERSARIAL_CHALLENGE_PROMPT.format(
        user_question="x",
        mediator_plan="x",
        adversary_context="x",
        debate_history="x",
    )
    adv.ADVERSARIAL_ALIGNMENT_PROMPT.format(
        user_question="x",
        research_plan="x",
        tool_plan="x",
        implementation_plan="x",
    )
    # Output-tag contract the parser reads (agents/adversarial_panelist.py
    # _extract_tag_json / _challenge_done_handler).
    assert "<CHALLENGE>" in adv.ADVERSARIAL_CHALLENGE_PROMPT and "</CHALLENGE>" in adv.ADVERSARIAL_CHALLENGE_PROMPT
    assert "<ALIGNMENT_REVIEW>" in adv.ADVERSARIAL_ALIGNMENT_PROMPT

    # Verdict vocabulary research_loop.py switches on (_ADVERSARY_VERDICTS in
    # agents/adversarial_panelist.py: "survives" | "needs_revision" |
    # "unsalvageable"). "skipped" is a sentinel research_loop.py constructs
    # itself when the adversary step is bypassed (agents/research_loop.py:588)
    # — it is never emitted by these prompts, so it is not asserted here.
    for verdict in ("survives", "needs_revision", "unsalvageable"):
        assert verdict in adv.ADVERSARIAL_CHALLENGE_PROMPT
        assert verdict in adv.ADVERSARIAL_ALIGNMENT_PROMPT

    # role="adversary" retrieval instructions must remain intact.
    assert 'role "adversary"' in adv.ADVERSARIAL_SYSTEM
    for tool in ("search_paper_wiki", "retrieve_literature", "fetch_paper_wiki", "fetch_paper_content"):
        assert tool in adv.ADVERSARIAL_SYSTEM


def test_critic_prompts_format_contract():
    from prompts import critic_prompts as c

    # .format() with the exact kwargs used at the real call site
    # (agents/attributing_critic.py:104-110, AttributingCritic.attribute) must
    # not raise — this proves the placeholder set matches the call site and
    # embedded JSON braces are still {{ }}-escaped.
    c.CRITIC_ATTRIBUTION_PROMPT.format(
        phase_number=2,
        research_plan="x",
        stage_results="x",
        prior_phase_number=1,
        prior_phase_metrics="x",
    )
    assert c.CRITIC_SYSTEM.strip()

    # Output-contract keys read by downstream parsers must survive refinement:
    # agents/attributing_critic.py._extract_tag_json reads the <CRITIC> tag;
    # agents/context_manager.py reads attributions[].step_id/judgment/
    # contribution_score/reason; agents/short_term_memory.py reads key_lessons.
    assert "<CRITIC>" in c.CRITIC_ATTRIBUTION_PROMPT and "</CRITIC>" in c.CRITIC_ATTRIBUTION_PROMPT
    for key in (
        "attributions",
        "step_id",
        "judgment",
        "contribution_score",
        "reason",
        "lesson_candidate",
        "overall_phase_judgment",
        "key_lessons",
    ):
        assert key in c.CRITIC_ATTRIBUTION_PROMPT

    # judgment vocabulary downstream code switches on (GOOD/BAD/NEEDS_REVISION).
    for judgment in ("GOOD", "BAD", "NEEDS_REVISION"):
        assert judgment in c.CRITIC_ATTRIBUTION_PROMPT


if __name__ == "__main__":
    unittest.main()
