"""Label-blind composition rules shared by Phase 2 catalog and inventory work."""
from fractions import Fraction
from functools import reduce
from itertools import combinations, product
from math import gcd, lcm
import re

PALETTE = {"Mg": [2], "Ca": [2], "Sr": [2], "Ba": [2], "Zn": [2],
           "Al": [3], "Ga": [3], "In": [3], "Ti": [4], "Zr": [4],
           "Hf": [4], "Sn": [2, 4]}
ATOMIC_NUMBERS = {"O": 8, "Mg": 12, "Ca": 20, "Sr": 38, "Ba": 56, "Zn": 30,
                  "Al": 13, "Ga": 31, "In": 49, "Ti": 22, "Zr": 40, "Hf": 72, "Sn": 50}
TOKEN = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")


def normalized_counts(composition):
    amounts = {symbol: Fraction(str(value)).limit_denominator(10000)
               for symbol, value in composition.items() if value != 0}
    if not amounts or any(value <= 0 for value in amounts.values()):
        raise ValueError("Composition has no atoms or nonpositive counts")
    denominator = reduce(lcm, (value.denominator for value in amounts.values()), 1)
    integers = {symbol: int(value * denominator) for symbol, value in amounts.items()}
    factor = reduce(gcd, integers.values())
    return tuple(sorted((symbol, value // factor) for symbol, value in integers.items()))


def formula_counts(formula):
    compact = re.sub(r"\s+", "", formula)
    matches = list(TOKEN.finditer(compact))
    if not matches or "".join(match.group(0) for match in matches) != compact:
        raise ValueError(f"Unsupported catalog formula: {formula!r}")
    amounts = {}
    for match in matches:
        symbol, value = match.groups()
        amounts[symbol] = amounts.get(symbol, Fraction()) + Fraction(value or "1")
    return normalized_counts(amounts)


def canonical_formula(counts):
    # Text is only a stable display/tie-break convention. Set membership uses tuples.
    ordered = sorted(dict(counts).items(), key=lambda pair: (pair[0] == "O", pair[0]))
    return "".join(symbol + (str(number) if number != 1 else "") for symbol, number in ordered)


def chemical_system(counts):
    return "-".join(sorted(dict(counts)))


def enumerate_formulas():
    records = {}
    for n_metals in (1, 2):
        for metals in combinations(sorted(PALETTE), n_metals):
            for charges in product(*(PALETTE[metal] for metal in metals)):
                for counts in product(range(1, 20), repeat=n_metals):
                    total_charge = sum(number * charge for number, charge in zip(counts, charges))
                    if total_charge % 2:
                        continue
                    oxygen = total_charge // 2
                    if sum(counts) + oxygen > 20:
                        continue
                    normalized = normalized_counts(dict(zip((*metals, "O"), (*counts, oxygen))))
                    row = records.setdefault(normalized, {
                        "formula": canonical_formula(normalized), "counts": dict(normalized),
                        "chemical_system": chemical_system(normalized),
                        "n_atoms_reduced": sum(number for _, number in normalized),
                        "oxidation_state_witnesses": [],
                    })
                    witness = {**dict(zip(metals, charges)), "O": -2}
                    if witness not in row["oxidation_state_witnesses"]:
                        row["oxidation_state_witnesses"].append(witness)
    for key, row in records.items():
        row["closed_shell_by_assigned_states_heuristic"] = True
        row["redox_ambiguity_penalty"] = int("Sn" in row["counts"])
        row["atomic_number_sum_proxy"] = sum(ATOMIC_NUMBERS[symbol] * number for symbol, number in key)
        row["ranking_key"] = [row["n_atoms_reduced"], row["redox_ambiguity_penalty"],
                              row["atomic_number_sum_proxy"], row["formula"]]
        assert all(sum(row["counts"][symbol] * charge for symbol, charge in witness.items()) == 0
                   for witness in row["oxidation_state_witnesses"])
    return records


def reserved_superset():
    metals = sorted(PALETTE)
    return sorted({"-".join(sorted((*group, "O")))
                   for size in (1, 2) for group in combinations(metals, size)})
