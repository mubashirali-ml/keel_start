"""T-002: case validation rules (ADR-0013): equity, vesting defaults, founders, state,
missing facts, purity and friendly messages."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest

from launch_agents.domain import CaseFacts, EntityType, Founder
from launch_agents.domain import types as domain_types
from launch_agents.rules import validation
from launch_agents.rules.validation import (
    ValidationIssue,
    ValidationResult,
    apply_vesting_defaults,
    missing_facts,
    validate_facts,
)

ALL_CODES = (
    "equity_total", "equity_range", "equity_precision", "cliff_exceeds_vesting", "vesting_range",
    "founder_name_missing", "founder_email_invalid", "founder_email_duplicate", "invalid_state",
    "entity_state_mismatch",
)


def founder(n: int, name: str | None = None, *, equity: str = "50", email: str | None = None,
            vesting: int | None = 48, cliff: int | None = 12) -> Founder:
    name = f"Founder Name{n}" if name is None else name
    return Founder(id=f"f{n}", name=name, email=email if email is not None else f"p{n}@example.com",
                   equity_percent=Decimal(equity), vesting_months=vesting, cliff_months=cliff)


def facts_with(*founders: Founder, entity_type=EntityType.LLC, state="WY") -> CaseFacts:
    return CaseFacts(
        business_description="bookkeeping software for small bakeries",
        founders=list(founders),
        entity_type=entity_type,
        state=state,
        incorporation_date=date(2026, 12, 1),
    )


def codes(result: ValidationResult) -> list[str]:
    return [i.code for i in result.issues]


def issue(result: ValidationResult, code: str) -> ValidationIssue:
    found = [i for i in result.issues if i.code == code]
    assert len(found) == 1, (code, result.issues)
    return found[0]


# ---------------------------------------------------------------------------------------
# Re-exports and the sample case
# ---------------------------------------------------------------------------------------
def test_reexports_domain_types():
    assert validation.ValidationIssue is domain_types.ValidationIssue
    assert validation.ValidationResult is domain_types.ValidationResult
    from launch_agents import rules

    assert rules.validate_facts is validate_facts


def test_sample_two_founder_llc_is_ok_with_note_for_bob(sample_facts):
    result = validate_facts(sample_facts)
    assert result.ok is True
    assert result.issues == []
    assert result.missing == []
    assert result.notes == [
        "No vesting was given for Bob Diaz, so I used the standard 48 months with a 12-month cliff."
    ]
    bob = result.facts.founders[1]
    assert (bob.vesting_months, bob.cliff_months) == (48, 12)


# ---------------------------------------------------------------------------------------
# AC1: equity
# ---------------------------------------------------------------------------------------
def test_equity_60_40_ok():
    result = validate_facts(facts_with(founder(1, equity="60"), founder(2, equity="40")))
    assert result.ok and result.issues == []


def test_equity_60_30_reports_total_of_90_percent():
    result = validate_facts(facts_with(founder(1, equity="60"), founder(2, equity="30")))
    assert codes(result) == ["equity_total"]
    i = issue(result, "equity_total")
    assert i.field == "founders" and i.founder_id is None
    assert "90%" in i.message
    assert i.message == "Equity adds up to 90%; it must total exactly 100%."
    assert result.ok is False


def test_equity_thirds_with_two_decimals_ok():
    result = validate_facts(facts_with(founder(1, equity="33.33"), founder(2, equity="33.33"),
                                       founder(3, equity="33.34")))
    assert result.ok and result.issues == []


def test_equity_total_with_trailing_zeros_is_exactly_100():
    result = validate_facts(facts_with(founder(1, equity="60.00"), founder(2, equity="40.0")))
    assert result.ok


@pytest.mark.parametrize("bad", ["0", "101", "-5"])
def test_equity_out_of_range(bad):
    result = validate_facts(facts_with(founder(1, equity="100"), founder(2, equity=bad)))
    i = issue(result, "equity_range")
    assert i.founder_id == "f2"
    assert f"{bad}%" in i.message
    assert result.ok is False


def test_equity_exactly_100_single_founder_ok():
    result = validate_facts(facts_with(founder(1, equity="100")))
    assert result.ok


def test_equity_precision_three_decimals():
    result = validate_facts(facts_with(founder(1, equity="33.333"), founder(2, equity="33.333"),
                                       founder(3, equity="33.334")))
    assert codes(result) == ["equity_precision"] * 3  # total is exactly 100
    assert [i.founder_id for i in result.issues] == ["f1", "f2", "f3"]
    assert "33.333%" in result.issues[0].message


def test_equity_two_decimals_with_trailing_zero_is_not_a_precision_issue():
    result = validate_facts(facts_with(founder(1, equity="50.500"), founder(2, equity="49.5")))
    assert result.ok


def test_equity_compare_is_exact_decimal_not_float():
    # float(49.99999999999999999) == 50.0, so a float compare would wrongly say 100.
    tiny = "49.99999999999999999"
    assert float(Decimal("50") + Decimal(tiny)) == 100.0
    result = validate_facts(facts_with(founder(1, equity="50"), founder(2, equity=tiny)))
    assert "equity_total" in codes(result)
    assert "99.99999999999999999%" in issue(result, "equity_total").message


def test_equity_total_not_reported_without_founders():
    result = validate_facts(CaseFacts())
    assert "equity_total" not in codes(result)


# ---------------------------------------------------------------------------------------
# AC2: vesting
# ---------------------------------------------------------------------------------------
def test_vesting_both_missing_defaults_48_12_with_one_note_per_founder():
    facts = facts_with(founder(1, "Alice Chen", equity="60", vesting=None, cliff=None),
                       founder(2, "Bob Diaz", equity="40", vesting=None, cliff=None))
    out, notes = apply_vesting_defaults(facts)
    assert [(f.vesting_months, f.cliff_months) for f in out.founders] == [(48, 12), (48, 12)]
    assert notes == [
        "No vesting was given for Alice Chen, so I used the standard 48 months with a 12-month cliff.",
        "No vesting was given for Bob Diaz, so I used the standard 48 months with a 12-month cliff.",
    ]
    result = validate_facts(facts)
    assert result.ok and result.notes == notes


def test_vesting_only_24_gives_cliff_12():
    out, notes = apply_vesting_defaults(facts_with(founder(1, "Ann Lee", equity="100", vesting=24, cliff=None)))
    assert (out.founders[0].vesting_months, out.founders[0].cliff_months) == (24, 12)
    assert len(notes) == 1 and "Ann Lee" in notes[0]


def test_vesting_only_6_gives_cliff_6():
    out, notes = apply_vesting_defaults(facts_with(founder(1, "Ann Lee", equity="100", vesting=6, cliff=None)))
    assert (out.founders[0].vesting_months, out.founders[0].cliff_months) == (6, 6)
    assert validate_facts(facts_with(founder(1, equity="100", vesting=6, cliff=None))).ok
    assert len(notes) == 1


def test_only_cliff_6_gives_vesting_48():
    out, notes = apply_vesting_defaults(facts_with(founder(1, "Ann Lee", equity="100", vesting=None, cliff=6)))
    assert (out.founders[0].vesting_months, out.founders[0].cliff_months) == (48, 6)
    assert len(notes) == 1 and "Ann Lee" in notes[0]


def test_stated_vesting_gets_no_note_and_is_unchanged():
    facts = facts_with(founder(1, equity="100", vesting=36, cliff=6))
    out, notes = apply_vesting_defaults(facts)
    assert notes == []
    assert (out.founders[0].vesting_months, out.founders[0].cliff_months) == (36, 6)


def test_cliff_13_with_vesting_12_names_founder():
    result = validate_facts(facts_with(founder(1, "Alice Chen", equity="60"),
                                       founder(2, "Bob Diaz", equity="40", vesting=12, cliff=13)))
    assert codes(result) == ["cliff_exceeds_vesting"]
    i = result.issues[0]
    assert i.founder_id == "f2" and "Bob Diaz" in i.message
    assert "13 months" in i.message and "12 months" in i.message


def test_zero_vesting_zero_cliff_is_valid():
    result = validate_facts(facts_with(founder(1, equity="100", vesting=0, cliff=0)))
    assert result.ok
    assert (result.facts.founders[0].vesting_months, result.facts.founders[0].cliff_months) == (0, 0)


def test_zero_vesting_only_defaults_cliff_to_zero():
    result = validate_facts(facts_with(founder(1, equity="100", vesting=0, cliff=None)))
    assert result.ok and result.facts.founders[0].cliff_months == 0


def test_zero_vesting_with_cliff_is_cliff_exceeds_vesting():
    result = validate_facts(facts_with(founder(1, "Ann Lee", equity="100", vesting=0, cliff=3)))
    assert codes(result) == ["cliff_exceeds_vesting"]


@pytest.mark.parametrize("vesting,cliff", [(-1, 0), (121, 12), (48, -1), (-6, None)])
def test_vesting_range(vesting, cliff):
    result = validate_facts(facts_with(founder(1, "Ann Lee", equity="100", vesting=vesting, cliff=cliff)))
    assert "vesting_range" in codes(result)
    assert "cliff_exceeds_vesting" not in codes(result)  # one clear message, not two
    i = issue(result, "vesting_range")
    assert i.founder_id == "f1" and "Ann Lee" in i.message
    assert result.ok is False


def test_vesting_120_is_the_upper_bound():
    assert validate_facts(facts_with(founder(1, equity="100", vesting=120, cliff=12))).ok


# ---------------------------------------------------------------------------------------
# AC3: founders
# ---------------------------------------------------------------------------------------
def test_founder_name_missing():
    result = validate_facts(facts_with(founder(1, equity="60"), founder(2, "  ", equity="40")))
    i = issue(result, "founder_name_missing")
    assert i.founder_id == "f2" and i.field == "founders.name"
    assert "Founder 2" in i.message


@pytest.mark.parametrize("bad", ["bob", "bob@", "bob@example", "bob @example.com", "@example.com", ""])
def test_founder_email_invalid(bad):
    result = validate_facts(facts_with(founder(1, equity="60"), founder(2, "Bob Diaz", equity="40", email=bad)))
    i = issue(result, "founder_email_invalid")
    assert i.founder_id == "f2" and "Bob Diaz" in i.message


def test_founder_email_duplicate_is_case_insensitive():
    result = validate_facts(facts_with(founder(1, "Alice Chen", equity="60", email="alice@example.com"),
                                       founder(2, "Bob Diaz", equity="40", email=" ALICE@Example.com ")))
    assert codes(result) == ["founder_email_duplicate"]
    i = result.issues[0]
    assert i.founder_id == "f2" and "Bob Diaz" in i.message and "Alice Chen" in i.message


def test_each_founder_problem_gets_its_own_code():
    result = validate_facts(facts_with(founder(1, "", equity="34", email="x@example.com"),
                                       founder(2, "Bea", equity="33", email="nope"),
                                       founder(3, "Cy", equity="33", email="X@example.com")))
    assert [(i.code, i.founder_id) for i in result.issues] == [
        ("founder_name_missing", "f1"),
        ("founder_email_invalid", "f2"),
        ("founder_email_duplicate", "f3"),
    ]


# ---------------------------------------------------------------------------------------
# AC4: state
# ---------------------------------------------------------------------------------------
def test_unknown_state_code():
    result = validate_facts(facts_with(founder(1, equity="100"), state="ZZ"))
    assert codes(result) == ["invalid_state"]
    assert issue(result, "invalid_state").field == "state"


def test_state_is_normalised_in_result():
    facts = facts_with(founder(1, equity="100"), state=" wy ")
    result = validate_facts(facts)
    assert result.ok and result.facts.state == "WY"
    assert facts.state == " wy "


def test_c_corp_in_wyoming_is_a_mismatch():
    result = validate_facts(facts_with(founder(1, equity="100"), entity_type=EntityType.C_CORP, state="WY"))
    assert codes(result) == ["entity_state_mismatch"]
    assert "Wyoming" in result.issues[0].message and "Delaware" in result.issues[0].message


def test_c_corp_in_delaware_ok_and_llc_anywhere_ok():
    assert validate_facts(facts_with(founder(1, equity="100"), entity_type=EntityType.C_CORP, state="DE")).ok
    assert validate_facts(facts_with(founder(1, equity="100"), entity_type=EntityType.LLC, state="TX")).ok


# ---------------------------------------------------------------------------------------
# AC5: missing facts
# ---------------------------------------------------------------------------------------
def test_missing_facts_all_in_ask_order():
    assert missing_facts(CaseFacts()) == [
        "business_description", "entity_type", "state", "founders", "incorporation_date",
    ]


def test_missing_facts_partial_keeps_order_and_skips_optional():
    facts = CaseFacts(state="DE", founders=[founder(1, equity="100")], name_preferences=[])
    assert missing_facts(facts) == ["business_description", "entity_type", "incorporation_date"]


def test_blank_strings_count_as_missing():
    facts = CaseFacts(business_description="   ", state="")
    assert missing_facts(facts)[:3] == ["business_description", "entity_type", "state"]
    assert validate_facts(facts).missing[:3] == ["business_description", "entity_type", "state"]


def test_complete_facts_have_nothing_missing_and_optional_never_listed(sample_facts):
    assert sample_facts.name_preferences == [] and sample_facts.company_name is None
    assert missing_facts(sample_facts) == []


def test_ok_false_while_anything_missing_even_without_issues():
    facts = facts_with(founder(1, equity="100"))
    facts.incorporation_date = None
    result = validate_facts(facts)
    assert result.issues == [] and result.missing == ["incorporation_date"] and result.ok is False


def test_ok_false_when_issue_even_with_nothing_missing():
    result = validate_facts(facts_with(founder(1, equity="90")))
    assert result.missing == [] and result.issues and result.ok is False


# ---------------------------------------------------------------------------------------
# AC6: purity
# ---------------------------------------------------------------------------------------
def test_validate_facts_is_pure_and_returns_defaults_applied(sample_facts):
    before = sample_facts.model_dump()
    result = validate_facts(sample_facts)
    assert sample_facts.model_dump() == before
    assert sample_facts.founders[1].vesting_months is None
    assert result.facts is not sample_facts
    assert result.facts.founders[1] is not sample_facts.founders[1]
    assert all(f.vesting_months is not None and f.cliff_months is not None for f in result.facts.founders)
    # Result facts stay a full copy of the input apart from normalisation/defaults.
    assert result.facts.business_description == sample_facts.business_description
    assert result.facts.incorporation_date == sample_facts.incorporation_date


def test_apply_vesting_defaults_is_pure(sample_facts):
    before = sample_facts.model_dump()
    out, _ = apply_vesting_defaults(sample_facts)
    assert sample_facts.model_dump() == before
    assert out is not sample_facts


def test_validate_is_deterministic(sample_facts):
    assert validate_facts(sample_facts) == validate_facts(sample_facts)


def test_83b_deadline_for_sample(sample_facts):
    from launch_agents.domain import deadline_83b, days_until

    result = validate_facts(sample_facts)
    deadline = deadline_83b(result.facts.incorporation_date)
    assert deadline == date(2026, 12, 31)
    assert days_until(deadline, date(2026, 11, 23)) == 38


# ---------------------------------------------------------------------------------------
# AC7: friendly messages
# ---------------------------------------------------------------------------------------
def _all_issue_examples() -> list[ValidationIssue]:
    cases = [
        facts_with(founder(1, "Alice Chen", equity="60"), founder(2, "Bob Diaz", equity="30")),
        facts_with(founder(1, equity="0"), founder(2, equity="101")),
        facts_with(founder(1, equity="33.333"), founder(2, equity="66.667")),
        facts_with(founder(1, "Chris", equity="100", vesting=12, cliff=13)),
        facts_with(founder(1, equity="100", vesting=0, cliff=1)),
        facts_with(founder(1, equity="100", vesting=-1, cliff=-2)),
        facts_with(founder(1, "", equity="50"), founder(2, equity="50", email="bad")),
        facts_with(founder(1, equity="50", email=""), founder(2, equity="50", email="P1@example.com")),
        facts_with(founder(1, equity="50", email="a@example.com"), founder(2, equity="50", email="A@EXAMPLE.COM")),
        facts_with(founder(1, equity="100"), state="ZZ", entity_type=EntityType.C_CORP),
        facts_with(founder(1, equity="100"), state="WY", entity_type=EntityType.C_CORP),
    ]
    return [i for facts in cases for i in validate_facts(facts).issues]


def test_every_code_is_covered_by_the_message_examples():
    assert set(ALL_CODES) <= {i.code for i in _all_issue_examples()}


@pytest.mark.parametrize("item", _all_issue_examples(), ids=lambda i: f"{i.code}-{i.founder_id}")
def test_messages_are_friendly_sentences(item):
    msg = item.message
    assert msg[0].isupper() or msg[0] == '"', msg
    assert msg.endswith("."), msg
    assert not re.search(r"[{}\[\]]", msg), msg  # no JSON
    assert "_" not in msg, msg  # no field codes like equity_percent / founder_id
    for code in ALL_CODES:
        assert code not in msg
    for token in ("founders.", "f1", "f2", "None", "Decimal", "EntityType"):
        assert token not in msg, (token, msg)


def test_notes_are_friendly_sentences():
    _, notes = apply_vesting_defaults(facts_with(
        founder(1, "Ann", equity="25", vesting=None, cliff=None),
        founder(2, "Bo", equity="25", vesting=24, cliff=None),
        founder(3, "Cy", equity="25", vesting=None, cliff=6),
        founder(4, "", equity="25", vesting=None, cliff=None),
    ))
    assert len(notes) == 4
    assert "Founder 4" in notes[3]
    for note in notes:
        assert note[0].isupper() and note.endswith(".") and "_" not in note and "None" not in note


def test_impossible_given_vesting_gets_an_issue_not_a_note():
    result = validate_facts(facts_with(founder(1, "Ann Lee", equity="100", vesting=-6, cliff=None)))
    assert result.notes == []
    assert codes(result) == ["vesting_range"]
    result = validate_facts(facts_with(founder(1, "Ann Lee", equity="100", vesting=None, cliff=-1)))
    assert result.notes == []
    assert codes(result) == ["vesting_range"]


def test_partial_default_notes_read_naturally():
    _, notes = apply_vesting_defaults(facts_with(founder(1, "Bo", equity="100", vesting=24, cliff=None)))
    assert notes == ["No cliff was given for Bo, so I used a 12-month cliff with the 24 months of vesting you gave."]
    _, notes = apply_vesting_defaults(facts_with(founder(1, "Cy", equity="100", vesting=None, cliff=6)))
    assert notes == ["No vesting length was given for Cy, so I used the standard 48 months "
                     "with the 6-month cliff you gave."]
