"""Fast research CI against actual research code and disposable synthetic inputs.

Only NumPy is installed. No models, materials databases, CHGNet, pymatgen or QE
are imported. Tests invoke the original acquisition, budget, gate, formula and
streamed-JSON implementations; historical paths are redirected before writes.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCRATCH: Path | None = None
sys.dont_write_bytecode = True


def load_source(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


acquisition = load_source("ci_acquisition", "research_acquisition.py")
formula_rules = load_source("ci_formula_rules", "scripts/phase2_formula_rules.py")
json_columns = load_source("ci_json_columns", "scripts/phase2_json_columns.py")


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        instant = cls(2030, 1, 1, 7, tzinfo=timezone.utc)
        return instant if tz is None else instant.astimezone(tz)


class ScratchCase(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="case-", dir=SCRATCH)
        self.root = Path(self.workspace.name)
        self.addCleanup(self.workspace.cleanup)

    def put_json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.ids = np.array([f"id-{i:02d}" for i in range(12)])
        self.mean = np.zeros(12)
        self.radius = np.zeros(12)
        self.features = np.zeros((12, 150))
        self.distance = np.zeros(12)

    def select(self, policy="quality", **changes):
        values = dict(material_ids=self.ids, predicted_mean=self.mean,
                      calibrated_radius=self.radius, diversity_features=self.features,
                      distance_to_known=self.distance, rng=np.random.default_rng(41))
        values.update(changes)
        return acquisition.select_batch(policy, **values)

    def test_quality_uses_lowest_energy_and_id_tie_break(self):
        mean = self.mean.copy()
        mean[9] = -0.3
        rows, _ = self.select(predicted_mean=mean)
        self.assertEqual(rows.tolist(), [9, 0, 1, 2, 3, 4, 5, 6, 7, 8])

    def test_uncertainty_explores_highest_radius(self):
        radius = np.arange(12) * 0.01
        rows, decisions = self.select("uncertainty", calibrated_radius=radius)
        self.assertEqual(rows.tolist(), list(range(11, 1, -1)))
        self.assertTrue(all(row["role"] == "uncertainty" for row in decisions))

    def test_full_policy_separates_seven_exploitation_and_three_exploration(self):
        radius = np.arange(12) * 0.01
        rows, decisions = self.select("full", calibrated_radius=radius)
        self.assertEqual(rows.tolist(), [0, 1, 2, 3, 4, 5, 6, 11, 10, 9])
        self.assertEqual([row["role"] for row in decisions],
                         ["conservative"] * 7 + ["optimistic"] * 3)

    def test_random_policy_is_seeded_and_without_replacement(self):
        first, _ = self.select("random")
        second, _ = self.select("random")
        self.assertEqual(first.tolist(), second.tolist())
        self.assertEqual(len(set(first.tolist())), 10)

    def test_diversity_updates_after_each_choice(self):
        features = self.features.copy()
        features[1] = 2
        features[2] = 2
        features[3] = -2
        rows, decisions = self.select("quality_diversity", diversity_features=features,
                                      distance_to_known=np.ones(12))
        self.assertEqual(rows[:3].tolist(), [0, 1, 3])
        self.assertEqual(decisions[1]["diversity_distance_at_selection"], 1)
        self.assertEqual(decisions[2]["diversity_distance_at_selection"], 1)

    def test_invalid_candidate_arrays_and_frozen_batch_are_rejected(self):
        invalid = [
            {"material_ids": np.array(["duplicate"] * 12)},
            {"predicted_mean": np.zeros(11)},
            {"calibrated_radius": np.full(12, -1.0)},
            {"predicted_mean": np.full(12, np.nan)},
            {"distance_to_known": np.full(12, 1.1)},
            {"diversity_features": np.zeros((12, 149))},
            {"batch_size": 2},
        ]
        for changes in invalid:
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                self.select(**changes)

    def test_fresh_shortlist_is_bounded_and_separates_roles(self):
        rows, decisions = acquisition.select_fresh_pair(
            self.ids, self.mean, np.arange(12) * 0.01, self.features, self.distance)
        self.assertEqual(rows.tolist(), [0, 11])
        self.assertEqual([row["role"] for row in decisions], ["conservative", "optimistic"])
        empty, evidence = acquisition.select_fresh_pair([], [], [], [], [])
        self.assertEqual(empty.tolist(), [])
        self.assertEqual(evidence, [])

    def test_calibration_quantile_and_uncertainty_floor(self):
        calibration = acquisition.calibrate_uncertainty(
            np.arange(9) * 0.01, np.zeros(9), np.zeros(9))
        self.assertEqual(calibration["rank_1_based"], 9)
        self.assertAlmostEqual(calibration["q"], 8)
        np.testing.assert_allclose(
            acquisition.uncertainty_radius([0, 0.02], calibration), [0.08, 0.16])
        with self.assertRaises(ValueError):
            acquisition.calibrate_uncertainty([0], [0], [0])

    def test_normalization_uses_initial_training_only_and_clips(self):
        normalization = acquisition.fit_diversity_normalization(np.zeros((2, 408)))
        np.testing.assert_array_equal(normalization["scale"], np.ones(150))
        transformed = acquisition.transform_diversity(np.full((1, 408), 100), normalization)
        np.testing.assert_array_equal(transformed, np.full((1, 150), 5))
        np.testing.assert_array_equal(normalization["center"], np.zeros(150))


class BudgetTests(ScratchCase):
    def setUp(self):
        super().setUp()
        self.budget = load_source("ci_budget", "research_budget.py")
        self.budget.ROOT = self.root
        self.budget.BASELINE = self.root / "artifacts/phase3/budget_baseline.json"
        self.budget.EVENTS = self.root / "artifacts/runtime_budget_events.jsonl"
        self.budget.CANONICAL = self.root / "artifacts/budget_ledger.json"
        self.budget.LOCK = self.root / "artifacts/runtime_budget.lock"
        self.budget.datetime = FixedDateTime
        baseline = json.loads((ROOT / "artifacts/phase3/budget_baseline.json").read_text(
            encoding="utf-8-sig"))
        baseline["budget"]["numerical_stop_utc"] = "2030-01-01T09:00:00+00:00"
        self.put_json("artifacts/phase3/budget_baseline.json", baseline)

    def state(self):
        return self.budget.snapshot()

    def test_attempts_charged_before_dispatch_and_failure_keeps_charge(self):
        ticket = self.budget.reserve_job("generation", "fixture-generation", attempts=3)
        before = self.state()
        self.assertEqual(before["generation"]["charged_attempts"], 15)
        self.assertIn(ticket["reservation_id"], before["generation"]["active_reservations"])
        after = self.budget.finish_job(ticket, 4.5, "failed")
        self.assertEqual(after["generation"]["charged_attempts"], 15)
        self.assertEqual(after["generation"]["remaining_attempts"], 113)
        self.assertEqual(after["generation"]["active_reservations"], [])

    def test_attempt_ceiling_rejection_does_not_write_event(self):
        with self.assertRaisesRegex(RuntimeError, "attempt capacity"):
            self.budget.reserve_job("generation", "over-cap", attempts=117)
        self.assertFalse(self.budget.EVENTS.exists())

    def test_unfinished_reservation_keeps_entire_watchdog(self):
        self.budget.reserve_job("chgnet", "fixture-relax", category="prototype", max_seconds=100)
        state = self.state()["chgnet"]
        self.assertEqual(state["reserved_inflight_seconds"], 100)
        self.assertAlmostEqual(state["available_unreserved_seconds"],
                               state["remaining_seconds"] - 100)

    def test_walltime_ceiling_blocks_oversubscription(self):
        baseline = json.loads(self.budget.BASELINE.read_text(encoding="utf-8"))
        baseline["budget"]["chgnet"].update(
            ceiling_seconds=100, charged_wall_seconds=0, remaining_seconds=100)
        self.put_json("artifacts/phase3/budget_baseline.json", baseline)
        self.budget.reserve_job("chgnet", "almost-all", category="prototype", max_seconds=60)
        with self.assertRaisesRegex(RuntimeError, "walltime"):
            self.budget.reserve_job("chgnet", "too-large", category="prototype", max_seconds=50)

    def test_qe_single_flight_and_duplicate_finish_are_enforced(self):
        ticket = self.budget.reserve_job("qe", "fixture-qe", max_seconds=30)
        with self.assertRaisesRegex(RuntimeError, "already active"):
            self.budget.reserve_job("qe", "another-qe", max_seconds=30)
        state = self.budget.finish_job(ticket, 31, "timeout")
        self.assertEqual(state["qe"]["reserved_inflight_seconds"], 0)
        events = [json.loads(line) for line in self.budget.EVENTS.read_text().splitlines()]
        self.assertTrue(events[-1]["watchdog_allowance_exceeded"])
        with self.assertRaises(RuntimeError):
            self.budget.finish_job(ticket, 31, "timeout")

    def test_same_job_cannot_be_reserved_again_after_finish(self):
        ticket = self.budget.reserve_job("generation", "once")
        self.budget.finish_job(ticket, 0, "aborted")
        with self.assertRaisesRegex(RuntimeError, "already reserved"):
            self.budget.reserve_job("generation", "once")

    def test_category_cap_keeps_failed_launches_charged(self):
        for number in range(4):
            ticket = self.budget.reserve_job("chgnet", f"prototype-{number}",
                                             category="prototype", max_seconds=1)
            self.budget.finish_job(ticket, 0, "failed")
        with self.assertRaisesRegex(RuntimeError, "category cap"):
            self.budget.reserve_job("chgnet", "prototype-4", category="prototype")

    def test_project_stop_and_invalid_requests_fail_before_dispatch(self):
        for changes in [
            dict(lane="qe", job_id="beyond-stop", max_seconds=7201),
            dict(lane="wrong", job_id="invalid-lane"),
            dict(lane="qe", job_id="not-one", attempts=2),
            dict(lane="generation", job_id="nonfinite", max_seconds=float("nan")),
            dict(lane="chgnet", job_id="unknown-category", category="unknown"),
        ]:
            with self.subTest(changes=changes), self.assertRaises((ValueError, RuntimeError)):
                self.budget.reserve_job(**changes)
        self.assertFalse(self.budget.EVENTS.exists())

    def test_missing_baseline_is_not_silently_recreated(self):
        self.budget.BASELINE.unlink()
        with self.assertRaisesRegex(RuntimeError, "baseline"):
            self.budget.reserve_job("generation", "missing-baseline")
        self.assertFalse(self.budget.EVENTS.exists())


class GateTests(ScratchCase):
    def setUp(self):
        super().setUp()
        self.gates = load_source("ci_stretch_gates", "scripts/phase4_gates.py")
        self.gates.ROOT = self.root
        self.gates.datetime = FixedDateTime
        self.primary = {"controls": [{"valid_unique_count": 1}, {"valid_unique_count": 1}],
                        "new_formulas_with_exact_valid_structure": 6}
        self.replay = {"status": "completed", "n_paired_seeds": 5}
        self.qe = {"status": "passed", "all_jobs_finished": True}
        self.budget = {"project_started_utc": "2030-01-01T00:00:00+00:00",
                       "generation": {"remaining_attempts": 16}}

    def run_gate(self):
        for path, value in [
            ("artifacts/phase4/generation/summary.json", self.primary),
            ("artifacts/phase4/replay/aggregate_summary.json", self.replay),
            ("artifacts/phase4/qe/summary.json", self.qe),
            ("artifacts/budget_ledger.json", self.budget),
        ]:
            self.put_json(path, value)
        with redirect_stdout(io.StringIO()):
            self.gates.main()
        return json.loads((self.root / "artifacts/phase4/gates/composition_stretch.json").read_text())

    def test_each_required_gate_independently_disables_optional_work(self):
        cases = [
            ("replay seeds", lambda: self.replay.update(n_paired_seeds=4)),
            ("arm validity", lambda: self.primary["controls"][0].update(valid_unique_count=0)),
            ("formula coverage", lambda: self.primary.update(new_formulas_with_exact_valid_structure=5)),
            ("DFT reference", lambda: self.qe.update(all_jobs_finished=False)),
            ("generation slots", lambda: self.budget["generation"].update(remaining_attempts=15)),
            ("time margin", lambda: self.budget.update(project_started_utc="2029-12-31T21:00:00+00:00")),
        ]
        originals = json.dumps([self.primary, self.replay, self.qe, self.budget])
        for label, fail_gate in cases:
            with self.subTest(gate=label):
                self.primary, self.replay, self.qe, self.budget = json.loads(originals)
                fail_gate()
                output = self.run_gate()
                self.assertFalse(output["enabled"])
                self.assertEqual(list(output["gates"].values()).count(False), 1)
                self.assertEqual(output["new_structure_draws_in_gate_check"], 0)
                (self.root / "artifacts/phase4/gates/composition_stretch.json").unlink()

    def test_all_gates_pass_requires_explicit_plan_instead_of_dispatch(self):
        with self.assertRaisesRegex(RuntimeError, "explicit bounded stretch execution plan"):
            self.run_gate()
        self.assertFalse((self.root / "artifacts/phase4/gates/composition_stretch.json").exists())

    def test_existing_decision_is_never_overwritten(self):
        self.primary["controls"][0]["valid_unique_count"] = 0
        self.run_gate()
        decision = self.root / "artifacts/phase4/gates/composition_stretch.json"
        original = decision.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already committed"):
            self.run_gate()
        self.assertEqual(decision.read_bytes(), original)


class CompositionAndParsingTests(ScratchCase):
    def test_formula_normalizes_fractions_and_repeated_elements(self):
        expected = (("Mg", 1), ("O", 1))
        self.assertEqual(formula_rules.formula_counts("Mg0.5 O0.5"), expected)
        self.assertEqual(formula_rules.formula_counts("MgMgO2"), expected)
        self.assertEqual(formula_rules.canonical_formula(expected), "MgO")

    def test_unsupported_formula_and_invalid_counts_rejected(self):
        for value in ["", "Ca(OH)2", "MgO!"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                formula_rules.formula_counts(value)
        with self.assertRaises(ValueError):
            formula_rules.normalized_counts({"Mg": -1, "O": 1})

    def test_enumeration_is_label_blind_bounded_charge_balanced_and_deterministic(self):
        first = formula_rules.enumerate_formulas()
        second = formula_rules.enumerate_formulas()
        self.assertEqual(first, second)
        self.assertIn(formula_rules.formula_counts("MgO"), first)
        for counts, record in first.items():
            self.assertLessEqual(record["n_atoms_reduced"], 20)
            self.assertEqual(record["n_atoms_reduced"], sum(dict(counts).values()))
            for witness in record["oxidation_state_witnesses"]:
                self.assertEqual(sum(record["counts"][symbol] * charge
                                     for symbol, charge in witness.items()), 0)

    def test_streaming_numbers_cross_one_byte_block_boundaries(self):
        for text, expected in [("-123456789", -123456789), ("1.25e-12", 1.25e-12)]:
            with self.subTest(text=text):
                stream = json_columns.JSONStream(io.StringIO("[" + text + "]"), block_size=1)
                stream.expect("[")
                self.assertEqual(stream.value(), expected)
                stream.expect("]")
                self.assertEqual(stream.peek(), "")

    def test_gzip_column_filter_returns_ordinary_records_without_object_decoding(self):
        path = self.root / "fixture.json.gz"
        sample = {"formula": {"0": "MgO", "1": "CaO"},
                  "structure": {"0": {"@module": "os", "@class": "NotExecutable"}},
                  "oracle": {"0": -123.0}}
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            json.dump(sample, handle)
        records = list(json_columns.iter_column_records(path, wanted_columns={"formula", "structure"}))
        self.assertEqual(records[0], ("formula", "0", "MgO"))
        self.assertEqual(records[-1][2], {"@module": "os", "@class": "NotExecutable"})
        self.assertTrue(all(column != "oracle" for column, _, _ in records))

    def test_truncated_json_and_trailing_content_are_rejected(self):
        for text in ['{"formula":{"0":"MgO"', '{"formula":{"0":"MgO"}} garbage']:
            with self.subTest(text=text):
                path = self.root / "bad.json.gz"
                with gzip.open(path, "wt", encoding="utf-8") as handle:
                    handle.write(text)
                with self.assertRaises(ValueError):
                    list(json_columns.iter_column_records(path))


def science_snapshot():
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--",
         "research_*.py", "scripts/phase*.py", "config", "artifacts", "data", "requirements"],
        check=True, capture_output=True)
    paths = [path for path in result.stdout.decode("utf-8").split("\0") if path]
    if not paths:
        raise ValueError("Expected version-controlled research inputs for preservation check")
    return {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in paths}


def main():
    global SCRATCH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    scratch = args.scratch.absolute()
    if scratch.resolve().is_relative_to(ROOT):
        parser.error("Scratch must be outside the project; historical outputs stay untouched")
    scratch.mkdir(parents=True, exist_ok=True)
    if args.report and args.report.absolute().resolve().is_relative_to(ROOT):
        parser.error("Report must be outside the project")
    before = science_snapshot()
    with tempfile.TemporaryDirectory(prefix="flamel-research-ci-", dir=scratch) as temporary:
        SCRATCH = Path(temporary)
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = science_snapshot()
    unchanged = before == after
    report = {"status": "PASS" if result.wasSuccessful() and unchanged else "FAIL",
              "tests": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": len(result.skipped),
              "numpy": np.__version__, "tracked_research_inputs_verified": len(before),
              "historical_inputs_unchanged": unchanged,
              "model_imports": [], "scientific_jobs_dispatched": 0,
              "fixture_scope": "Synthetic acquisition, budget, composition-stretch, formula and streamed JSON only"}
    if args.report:
        args.report.absolute().parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
