import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv

if "pandas" not in sys.modules:
    fake_pandas = types.ModuleType("pandas")
    fake_pandas.Series = lambda data: list(data)
    fake_pandas.read_excel = lambda *args, **kwargs: None
    fake_pandas.read_csv = lambda *args, **kwargs: None
    sys.modules["pandas"] = fake_pandas

from agents.session_dispatcher import SessionDispatcher
from agents.decision_schema import DecisionValidationError
from agents.session_router import SessionRouter, validate_session_route
from agents.session_state import SessionStateStore
from agents.tools import _normalize_pipeline_trial_inputs
from backend import BackendConfig, SingleCellBackend
from frontend.server import _artifact_url_for_path, _is_under, _resolve_artifact_request_path


class _FakeResponsesAPI:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("No more fake responses configured")
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses):
        self.responses = _FakeResponsesAPI(responses)


class _FakeResponse:
    def __init__(self, text):
        self.id = "response-id"
        self.output = []
        self.output_text = text


class _FakeCoder:
    def __init__(self):
        self.calls = []

    def run(self, *, implementation_plan, session_state, session_tag):
        self.calls.append(
            {
                "implementation_plan": implementation_plan,
                "session_state": session_state,
                "session_tag": session_tag,
            }
        )
        return {"status": "completed", "script_path": "/tmp/solution.py"}


class _FakeCoderWithArtifacts(_FakeCoder):
    def run(self, *, implementation_plan, session_state, session_tag):
        super().run(implementation_plan=implementation_plan, session_state=session_state, session_tag=session_tag)
        return {
            "status": "completed",
            "message": "Coder pipeline completed.",
            "metrics": {"ari": 0.91},
            "artifacts": {
                "plot_path": "/tmp/qc_plot.png",
                "report_path": "/tmp/report.json",
            },
        }


class _FakeResultSummarizer:
    def __init__(self):
        self.calls = []

    def summarize(self, *, user_query, decision, raw_results, session_tag):
        self.calls.append(
            {
                "user_query": user_query,
                "decision": decision,
                "raw_results": raw_results,
                "session_tag": session_tag,
            }
        )
        return {"message": "Metrics: {\"ari\": 0.91}", "figures": ["/tmp/qc_plot.png"]}


class _FakeResearchExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, *, user_message, session_state, session_tag):
        self.calls.append(
            {
                "user_message": user_message,
                "session_state": session_state,
                "session_tag": session_tag,
            }
        )
        return {
            "status": "completed",
            "message": "Research pipeline completed.",
            "artifact_dir": "/tmp/research",
        }


class _FakeResearchLoop:
    def __init__(self):
        self.calls = []

    def run(self, *, user_question, pipeline_mode):
        self.calls.append({"user_question": user_question, "pipeline_mode": pipeline_mode})
        return {
            "status": "done",
            "final_report": {"summary": f"ResearchLoop {pipeline_mode} completed."},
            "phases_completed": 1,
            "phase_log": [],
            "pipeline_mode": pipeline_mode,
        }


class _FakeToolConsultant:
    def __init__(self, decision=None):
        self.calls = []
        self.decision = decision or {
            "task": "bounded code task",
            "dag_plan": None,
            "implementation_plan": {"goal": "Run bounded code task.", "inputs": {"h5ad_path": "/tmp/in.h5ad"}},
            "research_brief": None,
        }

    def decide(self, *, user_message, session_state, session_tag):
        self.calls.append(
            {
                "user_message": user_message,
                "session_state": session_state,
                "session_tag": session_tag,
            }
        )
        return dict(self.decision)


def _route_response(payload):
    return _FakeResponse("<SESSION_ROUTE>\n" + json.dumps(payload) + "\n</SESSION_ROUTE>")


class SessionRoutingTests(unittest.TestCase):
    def test_validate_session_route_accepts_expected_shape(self):
        route = validate_session_route(
            {
                "resolved_intent": "Explain ARI.",
                "route": "direct_response",
                "reason": "explain metric",
                "response": "ARI compares cluster assignments.",
            }
        )
        self.assertEqual(route["route"], "direct_response")
        self.assertEqual(route["resolved_intent"], "Explain ARI.")
        self.assertNotIn("instructions", route)

    def test_validate_session_route_rejects_invalid_intent_mode(self):
        with self.assertRaises(DecisionValidationError):
            validate_session_route(
                {
                    "resolved_intent": "Explore the dataset.",
                    "intent_mode": "research",
                    "route": "task",
                    "reason": "invalid enum",
                }
            )

    def test_direct_response_does_not_call_orchestrator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "route": "direct_response",
                                "reason": "general explanation",
                                "response": "ARI compares two clusterings while correcting for chance.",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="what is ARI?", session_state={}, session_tag="turn1")

            self.assertEqual(result["route"]["route"], "direct_response")
            self.assertEqual(result["result"]["status"], "completed")
            self.assertIn("ARI compares", result["result"]["message"])
            self.assertEqual(tool_consultant.calls, [])

    def test_task_calls_orchestrator_with_resolved_intent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Find the best annotation workflow for /tmp/in.h5ad.",
                                "intent_mode": "operational",
                                "route": "task",
                                "reason": "new analysis task",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="find best annotation workflow", session_state={}, session_tag="turn1")

            self.assertEqual(result["route"]["route"], "task")
            self.assertEqual(len(tool_consultant.calls), 1)
            self.assertEqual(tool_consultant.calls[0]["user_message"], "Find the best annotation workflow for /tmp/in.h5ad.")
            self.assertIn("implementation_plan", result["decision"])
            self.assertIn("Status: completed.", result["result"]["message"])

    def test_operational_task_bypasses_research_loop_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Run cell type annotation on /tmp/in.h5ad.",
                                "intent_mode": "operational",
                                "route": "task",
                                "reason": "known workflow",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant()
            research_loop = _FakeResearchLoop()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
                research_loop=research_loop,
            )

            result = dispatcher.handle(user_message="annotate cells", session_state={}, session_tag="turn_operational")

            self.assertEqual(result["route"]["intent_mode"], "operational")
            self.assertEqual(len(tool_consultant.calls), 1)
            self.assertEqual(research_loop.calls, [])
            self.assertEqual(result["result"]["execution_path"], "tool_execution")

    def test_discovery_task_routes_to_research_loop_full(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Find what immune cell state drives disease severity.",
                                "intent_mode": "discovery",
                                "route": "task",
                                "reason": "open biological question",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant()
            research_loop = _FakeResearchLoop()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
                research_loop=research_loop,
            )

            result = dispatcher.handle(user_message="what drives severity?", session_state={}, session_tag="turn_discovery")

            self.assertEqual(tool_consultant.calls, [])
            self.assertEqual(research_loop.calls[0]["pipeline_mode"], "full")
            self.assertEqual(research_loop.calls[0]["user_question"], "Find what immune cell state drives disease severity.")
            self.assertEqual(result["decision"]["route"], "research_loop")
            self.assertEqual(result["result"]["pipeline_mode"], "full")

    def test_ambiguous_task_requests_user_choice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Analyze this dataset for interesting biology.",
                                "intent_mode": "ambiguous",
                                "route": "task",
                                "reason": "analysis request but mode is unclear",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            research_loop = _FakeResearchLoop()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=_FakeToolConsultant(),
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
                research_loop=research_loop,
            )

            result = dispatcher.handle(user_message="analyze this", session_state={}, session_tag="turn_ambiguous")

            self.assertEqual(research_loop.calls, [])
            self.assertEqual(result["decision"]["route"], "clarification_required")
            self.assertEqual(result["decision"]["intent_mode"], "ambiguous")
            self.assertEqual(result["result"]["status"], "needs_input")
            self.assertEqual(result["result"]["loop_status"], "awaiting_user")
            self.assertIn("Option 1", result["result"]["message"])
            self.assertIn("Option 2", result["result"]["message"])

    def test_discovery_without_research_loop_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Find what immune cell state drives disease severity.",
                                "intent_mode": "discovery",
                                "route": "task",
                                "reason": "open biological question",
                            }
                        )
                    ]
                ),
            )
            tool_consultant = _FakeToolConsultant()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=SessionStateStore(Path(tmpdir) / "session_state.json"),
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="what drives severity?", session_state={}, session_tag="turn_no_loop")

            self.assertEqual(result["result"]["status"], "failed")
            self.assertEqual(result["decision"]["route"], "research_loop_unavailable")
            self.assertEqual(result["decision"]["pipeline_mode"], "full")
            self.assertEqual(tool_consultant.calls, [])

    def test_tool_result_ui_prefers_structured_dataset_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Load /tmp/in.h5ad and summarize the dataset.",
                                "intent_mode": "operational",
                                "route": "task",
                                "reason": "dataset overview request",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant(
                {
                    "task": "summarize dataset",
                    "dag_plan": None,
                    "implementation_plan": {"goal": "Summarize dataset.", "inputs": {"h5ad_path": "/tmp/in.h5ad"}},
                    "research_brief": None,
                }
            )
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="show me the overview", session_state={}, session_tag="turn_summary")

            self.assertIn("Status: completed.", result["result"]["message"])
            self.assertEqual(result["result"]["status"], "completed")

    def test_composable_coder_result_uses_result_summarizer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Generate a QC plot.",
                                "intent_mode": "operational",
                                "route": "task",
                                "reason": "new plotting task",
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant(
                {
                    "task": "Generate a QC plot.",
                    "dag_plan": None,
                    "implementation_plan": {
                        "goal": "Generate a QC plot.",
                        "inputs": {"h5ad_path": "/tmp/in.h5ad"},
                    },
                    "research_brief": None,
                }
            )
            summarizer = _FakeResultSummarizer()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoderWithArtifacts(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
                result_summarizer=summarizer,
            )

            result = dispatcher.handle(user_message="make a qc plot", session_state={}, session_tag="turn_coder")

            self.assertIn("Metrics:", result["result"]["message"])
            self.assertIn("/tmp/qc_plot.png", result["result"]["images"])
            self.assertEqual(summarizer.calls[0]["session_tag"], "turn_coder_result_summarizer")

    def test_pipeline_trial_inputs_filter_unsupported_methods_and_align_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SingleCellBackend(
                BackendConfig(
                    cache_dir=Path(tmpdir) / "cache",
                    scratch_dir=Path(tmpdir) / "scratch",
                    log_dir=Path(tmpdir) / "logs",
                    reticulate_python=Path(sys.executable),
                )
            )
            pipeline_config = {
                "normalize.method": "log1p",
                "embed.method": "seurat_pca",
                "cluster.method": "leiden",
            }
            evaluation = {"metrics": ["ari"], "embedding_key": "X_pca", "cluster_key": "leiden", "label_key": "cell_type"}

            normalized_config, normalized_eval = _normalize_pipeline_trial_inputs(
                backend=backend,
                pipeline_name="rna_preprocess_and_cluster",
                pipeline_config=pipeline_config,
                evaluation=evaluation,
            )

            self.assertEqual(normalized_eval["embedding_key"], "X_seurat_pca")
            self.assertEqual(normalized_config["cluster.embedding_key"], "X_seurat_pca")
            self.assertEqual(normalized_config["cluster.cluster_key"], "leiden")

    def test_backend_supported_capabilities_lists_louvain_for_rna_clustering(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = SingleCellBackend(
                BackendConfig(
                    cache_dir=Path(tmpdir) / "cache",
                    scratch_dir=Path(tmpdir) / "scratch",
                    log_dir=Path(tmpdir) / "logs",
                    reticulate_python=Path(sys.executable),
                )
            )

            supported = backend.supported_capabilities()

            self.assertEqual(supported["rna"]["cluster"]["supported_methods"], ["leiden", "louvain"])

    def test_dispatcher_trims_persistent_snapshot_for_router(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = _FakeClient(
                [
                    _route_response(
                        {
                            "route": "direct_response",
                            "reason": "summary request",
                            "response": "short answer",
                        }
                    )
                ]
            )
            router = SessionRouter(engine_name="gpt-test", result_dir=tmpdir, client=client)
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            store.data["history"] = [{"role": "assistant", "content": "large old history"}]
            store.data["last_decision"] = {
                "task": "Compare RNA preprocessing paths.",
                "objective_name": "ari",
                "dag_plan": {
                    "layers": [
                        {"stage": "rna_clustering", "variants": [{"method": "leiden"}]},
                    ]
                },
            }
            store.data["last_result"] = {
                "status": "completed",
                "message": "done",
                "attempts": [{"stdout": "large attempt log"}],
                "trace": [{"result": "large trace"}],
                "stdout": "verbose output",
            }
            store.data["last_route"] = {
                "route": "execute_existing_capability",
                "reason": "previous route",
                "requires_execution": True,
                "requires_artifact_lookup": True,
            }
            store.save()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=_FakeToolConsultant(),
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            dispatcher.handle(
                user_message="summarize",
                session_state={"history": [{"role": "user", "content": "summarize"}]},
                session_tag="turn1",
            )

            prompt = client.responses.calls[0]["input"][1]["content"]
            session_state_text = prompt.split("Choose exactly one route:", 1)[0]
            self.assertIn('"history"', session_state_text)
            self.assertIn('"persistent_session"', session_state_text)
            self.assertNotIn('"large old history"', session_state_text)
            self.assertNotIn('"search_space"', session_state_text)
            self.assertNotIn('"attempts"', session_state_text)
            self.assertNotIn('"trace"', session_state_text)
            self.assertNotIn('"requires_artifact_lookup"', session_state_text)
            self.assertIn('"last_route"', session_state_text)
            self.assertIn('"reason": "previous route"', session_state_text)
            self.assertIn('"objective_name": "ari"', session_state_text)

    def test_direct_response_reads_referenced_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "overview.json"
            artifact.write_text(json.dumps({"status": "ok", "cells": 3}), encoding="utf-8")
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": f"Show {artifact}",
                                "route": "direct_response",
                                "reason": "show existing overview",
                                "requires_artifact_lookup": True,
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            tool_consultant = _FakeToolConsultant()
            coder = _FakeCoder()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=coder,
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="show me the overview", session_state={}, session_tag="turn2")

            self.assertEqual(result["decision"]["decision"], "artifact_lookup")
            self.assertEqual(result["result"]["status"], "completed")
            self.assertIn('"cells": 3', result["result"]["message"])
            self.assertEqual(tool_consultant.calls, [])
            self.assertEqual(coder.calls, [])

    def test_direct_response_returns_images_for_png_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "qc_histograms.png"
            artifact.write_bytes(b"\x89PNG\r\n\x1a\n")
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": f"Show {artifact}",
                                "route": "direct_response",
                                "reason": "show existing image",
                                "requires_artifact_lookup": True,
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=_FakeToolConsultant(),
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="show me the QC histograms", session_state={}, session_tag="turn2")

            self.assertEqual(result["decision"]["decision"], "artifact_lookup")
            self.assertEqual(result["result"]["message"], "Image: qc_histograms.png")
            self.assertEqual(result["result"]["images"], [str(artifact)])

    def test_direct_response_summarizes_binary_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "output.h5ad"
            artifact.write_bytes(b"\x00\x01\x02")
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": f"Show {artifact}",
                                "route": "direct_response",
                                "reason": "show existing binary",
                                "requires_artifact_lookup": True,
                            }
                        )
                    ]
                ),
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=_FakeToolConsultant(),
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="show me the output h5ad", session_state={}, session_tag="turn2")

            self.assertIn("Binary file (.h5ad, 3 bytes)", result["result"]["message"])
            self.assertEqual(result["result"]["images"], [])

    def test_artifact_path_guard_uses_real_path_boundaries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed = Path(tmpdir) / "artifacts"
            allowed.mkdir()
            inside = allowed / "plot.png"
            inside.write_bytes(b"png")
            sibling = Path(str(allowed) + "_evil")
            sibling.mkdir()
            outside = sibling / "plot.png"
            outside.write_bytes(b"png")

            self.assertTrue(_is_under(inside, allowed))
            self.assertFalse(_is_under(outside, allowed))

    def test_artifact_url_for_path_uses_clean_relative_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_root = Path(tmpdir) / "tool_artifacts"
            result_root = Path(tmpdir) / "results"
            tool_root.mkdir()
            result_root.mkdir()
            image = tool_root / "plots" / "qc_histograms.png"
            image.parent.mkdir()
            image.write_bytes(b"png")
            report = result_root / "feedback" / "summary.json"
            report.parent.mkdir()
            report.write_text("{}", encoding="utf-8")

            self.assertEqual(
                _artifact_url_for_path(image, tool_artifact_dir=tool_root, result_dir=result_root),
                "/artifacts/tool/plots/qc_histograms.png",
            )
            self.assertEqual(
                _artifact_url_for_path(report, tool_artifact_dir=tool_root, result_dir=result_root),
                "/artifacts/result/feedback/summary.json",
            )

    def test_resolve_artifact_request_path_round_trips_clean_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tool_root = Path(tmpdir) / "tool_artifacts"
            result_root = Path(tmpdir) / "results"
            tool_root.mkdir()
            result_root.mkdir()
            image = tool_root / "plots" / "qc histograms.png"
            image.parent.mkdir()
            image.write_bytes(b"png")

            url = _artifact_url_for_path(image, tool_artifact_dir=tool_root, result_dir=result_root)
            resolved = _resolve_artifact_request_path(
                url,
                tool_artifact_dir=tool_root,
                result_dir=result_root,
            )

            self.assertEqual(resolved, image.resolve())

    def test_task_builds_previous_plan_context_for_modification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            store.data["active_work_type"] = "dag"
            store.data["last_decision"] = {
                "task": "compare workflows",
                "dag_plan": {
                    "input_h5ad_path": "/tmp/input.h5ad",
                    "output_dir": "/tmp/out",
                    "objective_name": "cell_type_annotation_default",
                    "evaluation": {"metrics": ["ari"], "embedding_key": "X_pca", "cluster_key": "leiden"},
                    "layers": [
                        {
                            "stage": "rna_dimensionality_reduction",
                            "variants": [{"method": "pca"}, {"method": "scvi"}],
                        }
                    ],
                },
                "implementation_plan": None,
                "research_brief": None,
            }
            store.data["last_artifacts"] = {"trace_path": "/tmp/trace.json"}
            store.data["active_h5ad_path"] = "/tmp/current.h5ad"
            store.data["active_cluster_key"] = "leiden"
            store.save()
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Rerun the previous optimization with scVI instead of PCA.",
                                "intent_mode": "operational",
                                "route": "task",
                                "reason": "user requested scVI",
                            }
                        )
                    ]
                ),
            )
            tool_consultant = _FakeToolConsultant()
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="rerun with scVI", session_state={}, session_tag="turn2")

            self.assertEqual(result["route"]["route"], "task")
            self.assertEqual(len(tool_consultant.calls), 1)
            call = tool_consultant.calls[0]
            self.assertEqual(call["user_message"], "Rerun the previous optimization with scVI instead of PCA.")
            self.assertEqual(call["session_state"]["previous_plan_type"], "composable")
            self.assertIn('"dag_plan"', call["session_state"]["previous_plan"])
            self.assertIn('"active_h5ad_path": "/tmp/current.h5ad"', json.dumps(call["session_state"]["execution_context"]))

    def test_direct_response_can_summarize_previous_dag_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            store.data["last_decision"] = {
                "task": "Compare PCA and scVI clustering.",
                "dag_plan": {
                    "layers": [
                        {
                            "stage": "rna_clustering",
                            "variants": [{"method": "leiden"}],
                        }
                    ]
                },
            }
            store.data["last_result"] = {
                "status": "completed",
                "message": "Selected the scVI path based on the requested objective.",
                "artifact_dir": "/tmp/dag_artifacts",
            }
            store.save()
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Summarize the previous DAG run.",
                                "route": "direct_response",
                                "reason": "asks about previous run",
                                "response": None,
                                "requires_artifact_lookup": True,
                            }
                        )
                    ]
                ),
            )
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=_FakeToolConsultant(),
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="what options were explored?", session_state={}, session_tag="turn2")

            self.assertIn("Previous result", result["result"]["message"])
            self.assertIn("Selected the scVI path", result["result"]["message"])

    def test_direct_response_loads_trace_and_report_at_answer_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_path = Path(tmpdir) / "dag_trace.json"
            trace_path.write_text(
                json.dumps(
                    [
                        {
                            "index": 0,
                            "tool_name": "read_dataset_summary",
                            "arguments": {},
                            "result": {"status": "completed", "message": "loaded dataset summary"},
                        },
                        {
                            "index": 1,
                            "tool_name": "rna_clustering",
                            "arguments": {"method": "leiden"},
                            "result": {"error": "missing embedding"},
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report_path = Path(tmpdir) / "coder_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "attempts": 2,
                        "metrics": {"ari": 0.72},
                        "attempt_log": [
                            {"execution_result": {"returncode": 1, "stderr": "ValueError: missing cluster key"}}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store = SessionStateStore(Path(tmpdir) / "session_state.json")
            store.data["last_artifacts"] = {
                "trace_path": str(trace_path),
                "report_path": str(report_path),
            }
            store.data["last_result"] = {
                "status": "failed",
                "message": "previous run failed",
                "trace_path": str(trace_path),
                "report_path": str(report_path),
            }
            store.save()
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Explain what happened in the last execution.",
                                "route": "direct_response",
                                "reason": "asks what happened",
                                "response": None,
                            }
                        )
                    ]
                ),
            )
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=_FakeToolConsultant(),
                coder=_FakeCoder(),
                research_executor=_FakeResearchExecutor(),
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=store,
                result_dir=tmpdir,
            )

            result = dispatcher.handle(user_message="what happened last run?", session_state={}, session_tag="turn2")

            self.assertIn("Execution trace details", result["result"]["message"])
            self.assertIn("read_dataset_summary", result["result"]["message"])
            self.assertIn("rna_clustering", result["result"]["message"])
            self.assertIn("Coder report details", result["result"]["message"])
            self.assertIn("ValueError: missing cluster key", result["result"]["message"])

    def test_task_dispatches_research_to_research_executor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            router = SessionRouter(
                engine_name="gpt-test",
                result_dir=tmpdir,
                client=_FakeClient(
                    [
                        _route_response(
                            {
                                "resolved_intent": "Design and evaluate a broader prior-guided method for this dataset.",
                                "intent_mode": "operational",
                                "route": "task",
                                "reason": "broad research task",
                            }
                        )
                    ]
                ),
            )
            research_executor = _FakeResearchExecutor()
            tool_consultant = _FakeToolConsultant(
                decision={
                    "task": "broader method research",
                    "dag_plan": None,
                    "implementation_plan": None,
                    "research_brief": {"goal": "Design and evaluate a broader prior-guided method."},
                }
            )
            dispatcher = SessionDispatcher(
                router=router,
                tool_consultant=tool_consultant,
                coder=_FakeCoder(),
                research_executor=research_executor,
                tool_artifact_dir=Path(tmpdir) / "artifacts",
                state_store=SessionStateStore(Path(tmpdir) / "session_state.json"),
                result_dir=tmpdir,
            )

            result = dispatcher.handle(
                user_message="do broader method research",
                session_state={"input_h5ad_path": "/tmp/in.h5ad"},
                session_tag="turn3",
            )

            self.assertEqual(result["decision"]["research_brief"]["goal"], "Design and evaluate a broader prior-guided method.")
            self.assertEqual(len(research_executor.calls), 1)
            self.assertIn("Research pipeline completed.", result["result"]["message"])

    def test_session_state_records_in_progress_then_completion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session_state.json"
            store = SessionStateStore(path)

            store.begin_turn(user_message="run workflow", session_tag="turn1")
            in_progress = json.loads(path.read_text())
            self.assertEqual(in_progress["history"][-1]["content"], "run workflow")
            self.assertEqual(in_progress["history"][-1]["status"], "in_progress")
            self.assertEqual(in_progress["current_turn"]["session_tag"], "turn1")

            store.record_turn(
                user_message="run workflow",
                payload={"result": {"status": "completed", "message": "done"}},
            )
            completed = json.loads(path.read_text())
            self.assertEqual(completed["history"][-2]["status"], "completed")
            self.assertEqual(completed["history"][-1]["role"], "assistant")
            self.assertIsNone(completed["current_turn"])

    def test_session_state_persists_dag_best_path_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session_state.json"
            store = SessionStateStore(path)

            store.record_turn(
                user_message="run dag",
                payload={
                    "decision": {"dag_plan": {"layers": []}},
                    "result": {
                        "status": "completed",
                        "message": "done",
                        "raw_results": {
                            "dag_result": {
                                "status": "completed",
                                "best_path": {
                                    "path_dir": "/tmp/path_001",
                                    "artifacts": {
                                        "00_qc/output.h5ad": "/tmp/path_001/00_qc/output.h5ad",
                                    },
                                    "resolved_outputs": {
                                        "output_h5ad_path": "/tmp/path_001/output.h5ad",
                                    },
                                },
                            }
                        },
                    },
                },
            )

            completed = json.loads(path.read_text())
            self.assertEqual(completed["active_work_type"], "dag")
            self.assertEqual(completed["active_h5ad_path"], "/tmp/path_001/output.h5ad")
            self.assertEqual(completed["last_artifacts"]["path_dir"], "/tmp/path_001")
            self.assertNotIn("output_h5ad_path", completed["last_artifacts"])

    def test_session_state_history_uses_human_summary_not_raw_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session_state.json"
            store = SessionStateStore(path)

            store.begin_turn(user_message="run coder", session_tag="turn1")
            store.record_turn(
                user_message="run coder",
                payload={
                    "result": {
                        "status": "completed",
                        "script_path": "/tmp/solution.py",
                        "artifact_dir": "/tmp/artifacts",
                    }
                },
            )
            completed = json.loads(path.read_text())
            message = completed["history"][-1]["content"]

            self.assertIn("Status: completed.", message)
            self.assertIn("script_path: /tmp/solution.py", message)
            self.assertFalse(message.strip().startswith("{"))

    def test_session_state_surfaces_error_in_zero_exit_stdout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session_state.json"
            store = SessionStateStore(path)

            store.begin_turn(user_message="show overview", session_tag="turn1")
            store.record_turn(
                user_message="show overview",
                payload={
                    "result": {
                        "status": "completed",
                        "script_path": "/tmp/solution.py",
                        "stdout": "Wrote error overview to /tmp/overview.json",
                    }
                },
            )
            completed = json.loads(path.read_text())

            self.assertEqual(completed["history"][-2]["status"], "failed")
            self.assertEqual(completed["history"][-1]["status"], "failed")
            self.assertIn("Error reported in script output", completed["history"][-1]["content"])
            self.assertIn("Wrote error overview", completed["last_error"])

    def test_session_state_records_failed_turn(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session_state.json"
            store = SessionStateStore(path)

            store.begin_turn(user_message="run workflow", session_tag="turn1")
            store.record_error(user_message="run workflow", error="boom")
            failed = json.loads(path.read_text())

            self.assertEqual(failed["history"][-2]["status"], "failed")
            self.assertEqual(failed["history"][-1]["content"], "boom")
            self.assertEqual(failed["last_result"]["status"], "failed")
            self.assertEqual(failed["last_error"], "boom")

    def test_session_state_reset_clears_existing_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "session_state.json"
            store = SessionStateStore(path)
            store.data["history"] = [{"role": "user", "content": "old"}]
            store.data["initial_query"] = "previous task"
            store.data["last_error"] = "boom"
            store.save()

            store.reset()
            reset_payload = json.loads(path.read_text())

            self.assertEqual(reset_payload["history"], [])
            self.assertIsNone(reset_payload["initial_query"])
            self.assertIsNone(reset_payload["last_error"])


if __name__ == "__main__":
    unittest.main()
