from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents.session_recorder import SessionRecorder
from agents.state_graph import StateGraphError, StateGraphManager


class StateGraphTests(unittest.TestCase):
    def test_session_recorder_creates_conversation_and_session_layout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = SessionRecorder(root_dir=Path(tmpdir) / "runs", conversation_id="C_TEST", session_id="S_TEST")
            turn_id = recorder.start_turn(user_message="Run analysis.")
            route_ref = recorder.save_json("route/route_decision.json", {"route": "task"})

            self.assertEqual(turn_id, "turn_001")
            self.assertEqual(route_ref, "route/route_decision.json")
            self.assertTrue((recorder.session_dir / "session.json").exists())
            self.assertTrue((recorder.session_dir / "state_graph.json").parent.exists())
            self.assertTrue((recorder.session_dir / "progress.jsonl").exists())
            self.assertTrue((recorder.session_dir / "nodes").exists())
            self.assertTrue((recorder.conversation_dir / "leaderboard.json").exists())
            leaderboard = json.loads((recorder.conversation_dir / "leaderboard.json").read_text())
            self.assertEqual(leaderboard["conversation_id"], "C_TEST")
            self.assertEqual(leaderboard["nodes"], [])
            session = json.loads((recorder.session_dir / "session.json").read_text())
            self.assertEqual(session["message_history"][0]["turn_id"], "turn_001")
            events = [
                json.loads(line)
                for line in (recorder.session_dir / "progress.jsonl").read_text().splitlines()
                if line.strip()
            ]
            self.assertEqual(events[0]["event_type"], "user_message")

    def test_state_graph_allows_one_active_selected_plan_and_records_alternatives(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateGraphManager(session_dir=tmpdir)
            active = manager.initialize_research_plan(
                selected_plan={"plan_id": "plan_a", "summary": "Selected", "steps": ["A"]},
                alternatives=[
                    {"plan_id": "plan_b", "summary": "Alternative", "why_not_selected_now": "Needs more data."}
                ],
                user_question="Question?",
            )

            graph = manager.graph
            self.assertEqual(active, "plan_001")
            self.assertEqual(graph["active_node_id"], "plan_001")
            active_nodes = [n for n in graph["nodes"].values() if n.get("active")]
            self.assertEqual(len(active_nodes), 1)
            self.assertEqual(graph["nodes"]["plan_002"]["role"], "alternative")
            self.assertEqual(graph["nodes"]["plan_002"]["status"], "candidate")

    def test_state_graph_creates_branch_from_logical_predecessor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateGraphManager(session_dir=tmpdir)
            manager.initialize_research_plan(
                selected_plan={"summary": "Initial", "steps": ["A"]},
                alternatives=[],
                user_question="Question?",
            )
            new_node = manager.apply_post_analysis_decision(
                decision={
                    "decision_type": "self_revise_plan",
                    "rationale": "Analyzer found a missing downstream analysis.",
                    "continue_from_node_id": "plan_001",
                    "updated_selected_research_plan": {"summary": "Revised", "steps": ["A", "B"]},
                },
                active_plan={"steps": ["A"]},
                decision_ref="nodes/plan_001/next_decision.json",
            )

            graph = manager.graph
            self.assertEqual(new_node, "plan_002")
            self.assertEqual(graph["active_node_id"], "plan_002")
            self.assertFalse(graph["nodes"]["plan_001"]["active"])
            self.assertEqual(graph["edges"][0]["from_node_id"], "plan_001")
            self.assertEqual(graph["edges"][0]["to_node_id"], "plan_002")
            self.assertEqual(graph["edges"][0]["transition_reason"], "self_revise_plan")

    def test_parameter_change_records_repeat_iteration_without_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateGraphManager(session_dir=tmpdir)
            manager.initialize_research_plan(
                selected_plan={"summary": "Initial", "steps": ["A"]},
                alternatives=[],
                user_question="Question?",
            )
            node_id = manager.apply_post_analysis_decision(
                decision={"decision_type": "parameter_change", "rationale": "Try a stricter threshold."},
                active_plan={"steps": ["A"]},
                decision_ref="nodes/plan_001/next_decision.json",
            )

            graph = manager.graph
            self.assertEqual(node_id, "plan_001")
            self.assertEqual(graph["active_node_id"], "plan_001")
            self.assertEqual(len(graph["edges"]), 0)
            self.assertEqual(len(graph["nodes"]["plan_001"]["iterations"]), 1)

    def test_state_graph_rejects_missing_continue_from_node(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateGraphManager(session_dir=tmpdir)
            manager.initialize_research_plan(
                selected_plan={"summary": "Initial", "steps": ["A"]},
                alternatives=[],
                user_question="Question?",
            )
            with self.assertRaises(StateGraphError):
                manager.apply_post_analysis_decision(
                    decision={
                        "decision_type": "self_revise_plan",
                        "continue_from_node_id": "plan_404",
                        "updated_selected_research_plan": {"summary": "Revised", "steps": ["B"]},
                    },
                    active_plan={"steps": ["A"]},
                )

    def test_initialize_research_plan_warns_on_different_active_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateGraphManager(session_dir=tmpdir)
            first = manager.initialize_research_plan(
                selected_plan={"summary": "Initial", "steps": ["A"]},
                alternatives=[],
                user_question="Question?",
            )
            second = manager.initialize_research_plan(
                selected_plan={"summary": "Different", "steps": ["B"]},
                alternatives=[],
                user_question="Question?",
            )

            graph = manager.graph
            self.assertEqual(first, second)
            self.assertEqual(graph["warnings"][0]["active_node_id"], "plan_001")

    def test_declare_unanswerable_marks_active_node_terminal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateGraphManager(session_dir=tmpdir)
            manager.initialize_research_plan(
                selected_plan={"summary": "Initial", "steps": ["A"]},
                alternatives=[],
                user_question="Question?",
            )
            manager.apply_post_analysis_decision(
                decision={"decision_type": "declare_unanswerable", "unanswerable_reason": "Missing condition metadata."},
                active_plan={"steps": ["A"]},
            )

            graph = manager.graph
            self.assertIsNone(graph["active_node_id"])
            self.assertEqual(graph["nodes"]["plan_001"]["status"], "unanswerable")

    def test_trajectory_context_uses_analyzer_verdict_not_report_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            manager = StateGraphManager(session_dir=session_dir)
            manager.initialize_research_plan(
                selected_plan={"summary": "Initial", "steps": ["A"]},
                alternatives=[],
                user_question="Question?",
            )
            report_path = session_dir / "nodes" / "plan_001" / "analyzer_report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps({"result_verdict": "supported", "results_summary": "Evidence supports the claim."}),
                encoding="utf-8",
            )
            manager.attach_analyzer("plan_001", analyzer_report_ref="nodes/plan_001/analyzer_report.json")

            context = manager.trajectory_context()
            self.assertEqual(context["active_node"]["latest_analyzer_verdict"], "supported")
            self.assertEqual(context["active_node"]["analyzer_report_path"], "nodes/plan_001/analyzer_report.json")


if __name__ == "__main__":
    unittest.main()
