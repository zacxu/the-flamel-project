"""Download and audit the pinned Phase 1 WBM data with Python's standard library.

No model fitting, feature extraction, split allocation, or package installation occurs.
Run from any directory: python scripts/phase1_data.py [--offline]
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import re
import sys
import time
import traceback
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "wbm"
ARTIFACTS = ROOT / "artifacts" / "phase1" / "data"
EXPECTED_ROWS = 256_963
FILES = {
    "summary": {
        "filename": "2023-12-13-wbm-summary.csv.gz",
        "url": "https://ndownloader.figshare.com/files/64706751",
        "md5": "1555268d3aa59d20262cb9d01ce0994b",
        "size_bytes": 12_745_623,
        "registry_key": "wbm_summary",
    },
    "initial_structures": {
        "filename": "2022-10-19-wbm-init-structs.jsonl.gz",
        "url": "https://ndownloader.figshare.com/files/53161835",
        "md5": "b809f101dd42a745ec2baabe7eb16f11",
        "size_bytes": 49_537_334,
        "registry_key": "wbm_initial_structures",
    },
}
SUMMARY_COLUMNS = [
    "material_id", "formula", "n_sites", "volume", "uncorrected_energy",
    "e_form_per_atom_wbm", "e_above_hull_wbm", "bandgap_pbe",
    "protostructure_spglib_initial_structure", "uncorrected_energy_from_cse",
    "e_correction_per_atom_mp2020", "e_correction_per_atom_mp_legacy",
    "e_form_per_atom_uncorrected", "e_form_per_atom_mp2020_corrected",
    "e_above_hull_mp2020_corrected_ppd_mp",
    "site_stats_fingerprint_init_final_norm_diff", "protostructure_spglib",
    "unique_prototype",
]
INITIAL_COLUMNS = {"material_id", "formula_from_cse", "initial_structure"}
TARGET = "e_above_hull_mp2020_corrected_ppd_mp"
EXCLUDED_NONOXYGEN = {
    "H", "B", "C", "N", "F", "Si", "P", "S", "Cl", "Ge", "As", "Se",
    "Br", "Sb", "Te", "I", "At", "Ts", "He", "Ne", "Ar", "Kr", "Xe",
    "Rn", "Og",
}
SYMBOLS = set(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co "
    "Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb "
    "Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re "
    "Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es "
    "Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
)
FORMULA_PART = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")
ID_RE = re.compile(r"wbm-[1-5]-[1-9]\d*")
REGISTRY_API = "https://api.github.com/repos/janosh/matbench-discovery/commits/main"
REGISTRY_RELATIVE = "matbench_discovery/data-files.yml"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(message: str) -> None:
    line = f"{now()} {message}"
    print(line, flush=True)
    with (ARTIFACTS / "audit.log").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> dict[str, object]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            md5.update(block)
            sha256.update(block)
    return {"size_bytes": size, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def open_url(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "bears-phase1-data-audit/1.0"})
    return urllib.request.urlopen(request, timeout=120)


def fetch_bytes(url: str) -> bytes:
    for attempt in range(1, 4):
        try:
            with open_url(url) as response:
                return response.read()
        except Exception as error:
            log(f"fetch failed attempt={attempt} url={url}: {type(error).__name__}: {error}")
            if attempt == 3:
                raise
            time.sleep(attempt)
    raise AssertionError("unreachable")


def obtain_file(spec: dict[str, object], offline: bool) -> dict[str, object]:
    path = DATA / str(spec["filename"])
    if path.exists():
        actual = digest(path)
        if actual["md5"] != spec["md5"] or actual["size_bytes"] != spec["size_bytes"]:
            raise ValueError(f"Existing file does not match pinned checksum/size: {path}")
        log(f"verified cached {path.name}")
        return {**spec, **actual, "path": path.relative_to(ROOT).as_posix(), "cached": True}
    if offline:
        raise FileNotFoundError(f"Offline mode requires {path}")
    partial = path.with_suffix(path.suffix + ".partial")
    for attempt in range(1, 4):
        try:
            log(f"download start {path.name} attempt={attempt}")
            with open_url(str(spec["url"])) as response, partial.open("wb") as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
            actual = digest(partial)
            if actual["md5"] != spec["md5"] or actual["size_bytes"] != spec["size_bytes"]:
                raise ValueError(f"Downloaded checksum/size mismatch: {path.name}: {actual}")
            partial.replace(path)
            log(f"download verified {path.name} size={actual['size_bytes']} sha256={actual['sha256']}")
            return {**spec, **actual, "path": path.relative_to(ROOT).as_posix(), "cached": False}
        except Exception as error:
            log(f"download failed attempt={attempt}: {type(error).__name__}: {error}")
            if attempt == 3:
                raise
            time.sleep(attempt)
    raise AssertionError("unreachable")


def registry_snapshot(offline: bool) -> dict[str, object]:
    meta_path = DATA / "registry_metadata.json"
    if offline:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        revision = json.loads(fetch_bytes(REGISTRY_API))["sha"]
        url = f"https://raw.githubusercontent.com/janosh/matbench-discovery/{revision}/{REGISTRY_RELATIVE}"
        content = fetch_bytes(url)
        path = DATA / f"data-files-{revision}.yml"
        path.write_bytes(content)
        metadata = {
            "repository": "https://github.com/janosh/matbench-discovery",
            "revision": revision,
            "revision_api": REGISTRY_API,
            "url": url,
            "retrieved_at_utc": now(),
            "path": path.relative_to(ROOT).as_posix(),
            **digest(path),
        }
        write_json(meta_path, metadata)
    path = ROOT / str(metadata["path"])
    if digest(path)["sha256"] != metadata["sha256"]:
        raise ValueError("Cached registry snapshot SHA256 mismatch")
    # Match only the relevant top-level records. No YAML dependency is required.
    content = path.read_text(encoding="utf-8")
    checks = {}
    for spec in FILES.values():
        key = str(spec["registry_key"])
        match = re.search(rf"^{re.escape(key)}:\n(.*?)(?=^\S|\Z)", content, flags=re.M | re.S)
        if not match:
            raise ValueError(f"Missing registry section {key}")
        section = match.group(1)
        declared_md5 = re.search(r"^  md5:\s*([0-9a-f]{32})\s*$", section, re.M)
        declared_url = re.search(r"^  url:\s*(\S+)\s*$", section, re.M)
        if not declared_md5 or declared_md5.group(1) != spec["md5"]:
            raise ValueError(f"Pinned MD5 differs from retrieved registry for {key}")
        if not declared_url or declared_url.group(1).rsplit("/", 1)[-1] != str(spec["url"]).rsplit("/", 1)[-1]:
            raise ValueError(f"Pinned file ID differs from retrieved registry for {key}")
        checks[key] = {"md5_matches": True, "file_id_matches": True}
    metadata["pinned_file_checks"] = checks
    log(f"registry snapshot verified revision={metadata['revision']}")
    return metadata


def formula_counts(formula: str) -> dict[str, float]:
    compact = "".join(formula.split())
    counts: collections.Counter[str] = collections.Counter()
    cursor = 0
    for part in FORMULA_PART.finditer(compact):
        if part.start() != cursor or part.group(1) not in SYMBOLS:
            raise ValueError(f"Unsupported formula format: {formula!r}")
        amount = float(part.group(2) or 1)
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(f"Invalid formula amount: {formula!r}")
        counts[part.group(1)] += amount
        cursor = part.end()
    if cursor != len(compact) or not counts:
        raise ValueError(f"Unsupported formula format: {formula!r}")
    return dict(counts)


def finite(value: object, context: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Nonfinite number in {context}")
    return number


def population_audit(summary: Path):
    ids: dict[str, tuple[int, dict[str, float]]] = {}
    counters = collections.Counter()
    chain = collections.Counter()
    element_rejections = collections.Counter()
    groups: set[str] = set()
    targets_min = math.inf
    targets_max = -math.inf
    index_fields = ["material_id", "formula", "chemical_system", "n_sites", "eligible_metal_oxide", "reserved_mg_o_control", "exclusion_reasons"]
    with gzip.open(summary, "rt", encoding="utf-8", newline="") as stream, (ARTIFACTS / "eligible_population.csv").open("w", encoding="utf-8", newline="") as eligible_stream, (ARTIFACTS / "reserved_mg_o_controls.csv").open("w", encoding="utf-8", newline="") as reserved_stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != SUMMARY_COLUMNS:
            raise ValueError(f"Summary schema differs: {reader.fieldnames}")
        eligible_writer = csv.DictWriter(eligible_stream, fieldnames=index_fields)
        reserved_writer = csv.DictWriter(reserved_stream, fieldnames=index_fields)
        eligible_writer.writeheader()
        reserved_writer.writeheader()
        for line, row in enumerate(reader, start=2):
            mid = row["material_id"]
            if not ID_RE.fullmatch(mid) or mid in ids:
                raise ValueError(f"Duplicate or malformed summary ID at line {line}: {mid}")
            composition = formula_counts(row["formula"])
            elements = set(composition)
            sites = finite(row["n_sites"], mid + ":n_sites")
            if not sites.is_integer() or sites <= 0 or not math.isclose(sum(composition.values()), sites, abs_tol=1e-6):
                raise ValueError(f"Summary site count/composition mismatch for {mid}")
            if row["unique_prototype"] not in {"True", "False"}:
                raise ValueError(f"Unexpected unique_prototype flag for {mid}")
            if not row["protostructure_spglib_initial_structure"]:
                raise ValueError(f"Missing initial protostructure for {mid}")
            for column in ("e_form_per_atom_wbm", "e_above_hull_wbm", "e_form_per_atom_uncorrected", "e_form_per_atom_mp2020_corrected", TARGET):
                finite(row[column], mid + ":" + column)
            target = float(row[TARGET])
            targets_min, targets_max = min(targets_min, target), max(targets_max, target)
            ids[mid] = (int(sites), composition)
            counters["all_rows"] += 1
            counters["all_reference_hull_le_0"] += target <= 0
            counters["all_near_stable_le_0.05"] += target <= .05
            counters["all_negative_signed_hull_distances"] += target < 0
            unique = row["unique_prototype"] == "True"
            oxygen = "O" in elements
            two_three = len(elements) in (2, 3)
            small = sites <= 20
            prohibited = (elements - {"O"}) & EXCLUDED_NONOXYGEN
            eligible = unique and oxygen and two_three and small and not prohibited
            reserved = elements == {"Mg", "O"}
            if unique:
                chain["unique_prototype"] += 1
                if oxygen:
                    chain["then_oxygen_present"] += 1
                    if two_three:
                        chain["then_two_or_three_elements"] += 1
                        if small:
                            chain["then_at_most_20_sites"] += 1
                            element_rejections.update(prohibited)
                            if not prohibited:
                                chain["then_no_excluded_nonoxygen_elements"] += 1
            reasons = []
            if not unique: reasons.append("not_unique_prototype")
            if not oxygen: reasons.append("no_oxygen")
            if not two_three: reasons.append("not_two_or_three_elements")
            if not small: reasons.append("more_than_20_sites")
            if prohibited: reasons.append("excluded_elements:" + ",".join(sorted(prohibited)))
            out = {
                "material_id": mid, "formula": row["formula"],
                "chemical_system": "-".join(sorted(elements)), "n_sites": int(sites),
                "eligible_metal_oxide": eligible, "reserved_mg_o_control": reserved,
                "exclusion_reasons": ";".join(reasons),
            }
            if eligible:
                eligible_writer.writerow(out)
                groups.add(out["chemical_system"])
                counters["eligible_rows"] += 1
                counters["eligible_reference_hull_le_0"] += target <= 0
                counters["eligible_near_stable_le_0.05"] += target <= .05
                counters["eligible_reserved_mg_o"] += reserved
            if reserved:
                reserved_writer.writerow(out)
                counters["all_mg_o_rows"] += 1
                counters["unique_prototype_mg_o_rows"] += unique
                counters["all_mg_o_at_most_20_sites"] += small
                counters["all_mg_o_reference_hull_le_0"] += target <= 0
                counters["all_mg_o_near_stable_le_0.05"] += target <= .05
    if len(ids) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} summary rows, got {len(ids)}")
    counters["eligible_chemical_systems"] = len(groups)
    counters["eligible_not_reserved_mg_o"] = counters["eligible_rows"] - counters["eligible_reserved_mg_o"]
    result = {
        "summary_columns": SUMMARY_COLUMNS, "summary_unique_ids": len(ids),
        "counts": dict(counters), "sequential_eligibility_counts": dict(chain),
        "excluded_element_occurrences_after_first_four_filters": dict(element_rejections),
        "signed_target_range_eV_per_atom": [targets_min, targets_max],
        "proposal_count_comparison": {
            "expected_eligible": 8294, "observed_eligible": counters["eligible_rows"],
            "expected_chemical_systems": 1866, "observed_chemical_systems": len(groups),
            "expected_near_stable": 1934, "observed_near_stable": counters["eligible_near_stable_le_0.05"],
        },
    }
    log(f"summary gzip/schema/population audit complete rows={len(ids)} eligible={counters['eligible_rows']} groups={len(groups)}")
    return ids, result


def check_vector(value: object, context: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"Expected 3-vector in {context}")
    return [finite(item, context) for item in value]


def structures_audit(path: Path, summary_ids: dict[str, tuple[int, dict[str, float]]]):
    seen: set[str] = set()
    checked_sites = 0
    fractional_outside_cell_sites = 0
    max_cartesian_consistency_error = 0.0
    volumes_min, volumes_max = math.inf, -math.inf
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for row_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"Blank initial-structure row {row_number}")
            row = json.loads(line)
            if set(row) != INITIAL_COLUMNS:
                raise ValueError(f"Initial record schema differs at row {row_number}: {list(row)}")
            mid = row["material_id"]
            if mid in seen or mid not in summary_ids:
                raise ValueError(f"Duplicate or unjoined initial-structure ID: {mid}")
            seen.add(mid)
            expected_n, expected_comp = summary_ids[mid]
            if formula_counts(row["formula_from_cse"]) != expected_comp:
                raise ValueError(f"Initial/summary formula mismatch for {mid}")
            structure = row["initial_structure"]
            if structure.get("@class") != "Structure":
                raise ValueError(f"Initial structure is not a Structure for {mid}")
            lattice = structure["lattice"]
            matrix = lattice["matrix"]
            if not isinstance(matrix, list) or len(matrix) != 3:
                raise ValueError(f"Invalid lattice matrix for {mid}")
            a, b, c = [check_vector(vector, mid + ":lattice") for vector in matrix]
            determinant = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
            volume = finite(lattice["volume"], mid + ":initial_volume")
            if volume <= 0 or not math.isclose(abs(determinant), volume, rel_tol=1e-6, abs_tol=1e-5):
                raise ValueError(f"Invalid or inconsistent initial cell volume for {mid}")
            volumes_min, volumes_max = min(volumes_min, volume), max(volumes_max, volume)
            sites = structure["sites"]
            if not isinstance(sites, list) or len(sites) != expected_n:
                raise ValueError(f"Initial/summary number of sites mismatch for {mid}")
            composition: collections.Counter[str] = collections.Counter()
            for site in sites:
                abc = check_vector(site["abc"], mid + ":fractional_coordinates")
                xyz = check_vector(site["xyz"], mid + ":cartesian_coordinates")
                predicted = [sum(abc[k]*matrix[k][j] for k in range(3)) for j in range(3)]
                error = max(abs(predicted[j]-xyz[j]) for j in range(3))
                max_cartesian_consistency_error = max(max_cartesian_consistency_error, error)
                if error > 1e-4:
                    raise ValueError(f"Initial fractional/cartesian coordinates inconsistent for {mid}: {error}")
                fractional_outside_cell_sites += any(x < 0 or x >= 1 for x in abc)
                species = site["species"]
                if not isinstance(species, list) or not species:
                    raise ValueError(f"Missing species for {mid}")
                occupancy = 0.0
                for specie in species:
                    element = specie["element"]
                    amount = finite(specie["occu"], mid + ":occupancy")
                    if element not in SYMBOLS or amount <= 0:
                        raise ValueError(f"Invalid species/occupancy for {mid}")
                    composition[element] += amount
                    occupancy += amount
                if not math.isclose(occupancy, 1.0, abs_tol=1e-8):
                    raise ValueError(f"Non-unit site occupancy for {mid}")
                checked_sites += 1
            if set(composition) != set(expected_comp) or any(not math.isclose(composition[e], expected_comp[e], abs_tol=1e-6) for e in expected_comp):
                raise ValueError(f"Initial/summary elemental composition mismatch for {mid}")
            if row_number % 50_000 == 0:
                log(f"initial-structure rows checked={row_number}")
    missing = set(summary_ids) - seen
    if len(seen) != EXPECTED_ROWS or missing:
        raise ValueError(f"Initial/summary join incomplete: initial={len(seen)} missing={len(missing)}")
    log(f"initial gzip/schema/geometry/join audit complete rows={len(seen)} sites={checked_sites}")
    return {
        "initial_record_columns": sorted(INITIAL_COLUMNS),
        "unique_initial_ids": len(seen), "matched_summary_ids": len(seen),
        "missing_initial_ids": 0, "extra_initial_ids": 0, "duplicate_initial_ids": 0,
        "validated_sites": checked_sites,
        "all_formulas_and_site_counts_match_summary": True,
        "all_cells_finite_nonzero_and_volume_consistent": True,
        "all_site_coordinates_finite_and_cartesian_consistent": True,
        "max_cartesian_consistency_error_angstrom": max_cartesian_consistency_error,
        "initial_volume_range_angstrom_cubed": [volumes_min, volumes_max],
        "fractional_sites_outside_unit_cell": fractional_outside_cell_sites,
        "fractional_wrapping_note": "Finite fractional coordinates outside [0,1) are valid periodic representations; no coordinates were changed.",
        "gzip_crc_verified_by_full_stream_read": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Re-audit cached files without any network requests")
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    started = now()
    log(f"Phase 1 data audit started offline={args.offline} python={platform.python_version()}")
    try:
        registry = registry_snapshot(args.offline)
        files = {name: obtain_file(spec, args.offline) for name, spec in FILES.items()}
        ids, population = population_audit(ROOT / str(files["summary"]["path"]))
        structures = structures_audit(ROOT / str(files["initial_structures"]["path"]), ids)
        comparison = population["proposal_count_comparison"]
        count_match = comparison["observed_eligible"] == comparison["expected_eligible"] and comparison["observed_chemical_systems"] == comparison["expected_chemical_systems"] and comparison["observed_near_stable"] == comparison["expected_near_stable"]
        report = {
            "status": "passed", "started_at_utc": started, "completed_at_utc": now(),
            "elapsed_seconds": time.perf_counter()-start,
            "summary_gzip_crc_verified_by_full_stream_read": True,
            "population": population, "initial_structures": structures,
            "proposal_population_counts_reproduced": count_match, "errors": [],
            "warnings": [] if count_match else ["Observed population differs from proposal audit; retained observed counts without forcing agreement."],
        }
        write_json(ARTIFACTS / "validation_report.json", report)
        manifest = {
            "schema_version": 1, "status": "passed", "created_at_utc": now(),
            "phase": 1, "dataset": "Matbench Discovery WBM released historical data",
            "expected_records": EXPECTED_ROWS, "files": files, "registry": registry,
            "audit_script": {"path": Path(__file__).relative_to(ROOT).as_posix(), **digest(Path(__file__))},
            "runtime": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "dependencies": "Python standard library only"},
            "target": {
                "column": TARGET, "unit": "eV/atom",
                "meaning": "Released signed distance to the fixed historical MP reference convex hull after MP2020 energy corrections",
                "near_stable_threshold_inclusive": 0.05, "on_or_below_reference_hull_threshold_inclusive": 0.0,
                "negative_values_preserved": True, "oracle_recomputed": False,
                "scope": "Historical WBM label replay; not interchangeable with fresh Quantum ESPRESSO or CHGNet energies.",
            },
            "population_definition": {
                "unique_prototype": True, "required_element": "O", "number_of_elements_inclusive": [2, 3],
                "max_sites_in_initial_cell": 20,
                "excluded_nonoxygen_elements": sorted(EXCLUDED_NONOXYGEN),
                "definition_note": "Operational proposal family; published unique_prototype is a retrospective population flag, not a prospective novelty screen.",
            },
            "reserved_control": {
                "chemical_system": "Mg-O", "scope": "All Mg-O entries must remain outside future training and calibration across every seed.",
                "flag_written": "reserved_mg_o_control", "rows_excluded_from_splits_now": False,
                "count_all_summary": population["counts"].get("all_mg_o_rows", 0),
                "count_in_eligible_population": population["counts"].get("eligible_reserved_mg_o", 0),
                "additional_fresh_systems": "To be reserved in Phase 2 before any splits are frozen.",
            },
            "feature_lineage": {
                "permitted_sources": ["formula (composition only)", "protostructure_spglib_initial_structure", "initial_structure lattice and sites"],
                "n_sites": "Validated against initial_structure.sites for every row; descriptor implementation may derive it from initial geometry.",
                "excluded_feature_columns": [column for column in SUMMARY_COLUMNS if column not in {"material_id", "formula", "n_sites", "protostructure_spglib_initial_structure", "unique_prototype"}],
                "unique_prototype": "Population definition only; never a predictor feature.",
                "material_id": "Join/audit key only; substitution-round or ID order must not be predictor features.",
                "relaxed_geometry_not_used": True, "features_extracted": False,
            },
            "counts": population["counts"],
            "phase2_operations_performed": {"splits_created": False, "features_extracted": False, "models_trained": False},
            "outputs": {},
        }
        for filename in ("eligible_population.csv", "reserved_mg_o_controls.csv", "validation_report.json"):
            path = ARTIFACTS / filename
            manifest["outputs"][filename] = {"path": path.relative_to(ROOT).as_posix(), **digest(path)}
        write_json(ARTIFACTS / "dataset_manifest.json", manifest)
        write_json(ARTIFACTS / "errors.json", {"status": "passed", "errors": []})
        log(f"Phase 1 data audit PASSED elapsed_seconds={time.perf_counter()-start:.3f}")
        return 0
    except Exception as error:
        details = {"status": "failed", "at_utc": now(), "exception": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        write_json(ARTIFACTS / "errors.json", details)
        write_json(ARTIFACTS / "validation_report.json", details)
        log(f"Phase 1 data audit FAILED: {type(error).__name__}: {error}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
