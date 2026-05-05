"""Regression tests for EntityFacts LLM revenue-growth analysis.

The LLM growth summary must compare comparable revenue periods. It should not
compare adjacent rows from a filing-date sorted time series when those rows are
comparative-period disclosures in reverse chronological order, and it should not
let fuzzy "Revenue" matching pull in CostOfRevenue.
"""

from datetime import date

import pytest

from edgar.entity.entity_facts import EntityFacts
from edgar.entity.models import DataQuality, FinancialFact


def _fact(
    concept: str,
    label: str,
    period_start: date,
    period_end: date,
    value: float,
    fiscal_period: str,
    fiscal_year: int,
    filing_date: date,
    form_type: str,
) -> FinancialFact:
    return FinancialFact(
        concept=concept,
        taxonomy='us-gaap',
        label=label,
        value=value,
        numeric_value=value,
        unit='USD',
        scale=1,
        period_start=period_start,
        period_end=period_end,
        period_type='duration',
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        filing_date=filing_date,
        accession='0000000000-26-000001',
        form_type=form_type,
        data_quality=DataQuality.HIGH,
    )


def _growth_context(facts: list[FinancialFact]) -> dict:
    entity_facts = EntityFacts(cik=12345, name='Test Co', facts=facts)
    context = entity_facts.to_llm_context(focus_areas=['growth'])
    return context['focus_analysis']['growth']['revenue_growth_yoy']


@pytest.mark.fast
def test_llm_growth_uses_standardized_revenue_not_cost_of_revenue():
    facts = [
        _fact(
            'us-gaap:CostOfRevenue',
            'Cost of Revenue',
            date(2024, 1, 1),
            date(2024, 12, 31),
            461_633_000.0,
            'FY',
            2025,
            date(2026, 2, 17),
            '10-K',
        ),
        _fact(
            'us-gaap:CostOfRevenue',
            'Cost of Revenue',
            date(2025, 1, 1),
            date(2025, 12, 31),
            608_998_000.0,
            'FY',
            2025,
            date(2026, 2, 17),
            '10-K',
        ),
        _fact(
            'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
            'Revenue from Contract with Customer, Excluding Assessed Tax',
            date(2024, 1, 1),
            date(2024, 12, 31),
            503_123_000.0,
            'FY',
            2025,
            date(2026, 2, 17),
            '10-K',
        ),
        _fact(
            'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
            'Revenue from Contract with Customer, Excluding Assessed Tax',
            date(2025, 1, 1),
            date(2025, 12, 31),
            619_353_000.0,
            'FY',
            2025,
            date(2026, 2, 17),
            '10-K',
        ),
    ]

    growth = _growth_context(facts)

    assert growth['value'] == 23.1
    assert growth['period_comparison'] == 'FY ended 2025-12-31 vs FY ended 2024-12-31'


@pytest.mark.fast
def test_llm_growth_sorts_periods_before_comparing_quarters():
    facts = [
        _fact(
            'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
            'Revenue from Contract with Customer, Excluding Assessed Tax',
            date(2020, 4, 1),
            date(2020, 6, 30),
            100_000_000.0,
            'Q2',
            2021,
            date(2021, 8, 1),
            '10-Q',
        ),
        _fact(
            'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
            'Revenue from Contract with Customer, Excluding Assessed Tax',
            date(2021, 4, 1),
            date(2021, 6, 30),
            240_730_000.0,
            'Q2',
            2021,
            date(2021, 8, 1),
            '10-Q',
        ),
        _fact(
            'us-gaap:Revenues',
            'Revenues',
            date(2025, 1, 1),
            date(2025, 3, 31),
            927_000_000.0,
            'Q1',
            2026,
            date(2026, 4, 29),
            '10-Q',
        ),
        _fact(
            'us-gaap:Revenues',
            'Revenues',
            date(2026, 1, 1),
            date(2026, 3, 31),
            1_067_000_000.0,
            'Q1',
            2026,
            date(2026, 4, 29),
            '10-Q',
        ),
    ]

    growth = _growth_context(facts)

    assert growth['value'] == 15.1
    assert growth['period_comparison'] == 'Q1 ended 2026-03-31 vs Q1 ended 2025-03-31'
