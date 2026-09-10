from __future__ import annotations

import pytest

from services.llm.prompts.v1 import (
    SignalNoisePromptV1,
    CompanyInferencePromptV1,
    RiskNarrativePromptV1,
    OutreachDraftPromptV1,
)


class TestSignalNoisePromptV1:
    """Test signal/noise classification prompt template."""

    def test_render_basic(self) -> None:
        """Test basic signal/noise prompt rendering."""
        prompt = SignalNoisePromptV1()
        result = prompt.render(
            domain="example.com",
            exposures_text=prompt.render_exposures(["exposed_database"]),
            titles_text=prompt.render_titles(["Apache 2.4"]),
        )

        assert "example.com" in result
        assert "exposed_database" in result
        assert "Apache 2.4" in result
        assert "signal" in result.lower() or "noise" in result.lower()

    def test_render_empty_exposures(self) -> None:
        """Test prompt with empty exposures list."""
        prompt = SignalNoisePromptV1()
        result = prompt.render(
            domain="safe.example.com",
            exposures_text=prompt.render_exposures([]),
            titles_text=prompt.render_titles(["Nginx"]),
        )

        assert "safe.example.com" in result
        assert "None detected" in result or "none detected" in result.lower()

    def test_render_multiple_exposures(self) -> None:
        """Test prompt with multiple exposures."""
        prompt = SignalNoisePromptV1()
        exposures = ["exposed_database", "weak_tls", "legacy_protocol"]
        result = prompt.render(
            domain="risky.example.com",
            exposures_text=prompt.render_exposures(exposures),
            titles_text=prompt.render_titles(["Apache", "IIS"]),
        )

        for exposure in exposures:
            assert exposure in result

    def test_render_empty_titles(self) -> None:
        """Test prompt with empty HTTP titles."""
        prompt = SignalNoisePromptV1()
        result = prompt.render(
            domain="example.com",
            exposures_text=prompt.render_exposures(["exposed_database"]),
            titles_text=prompt.render_titles([]),
        )

        assert "example.com" in result
        assert "None detected" in result or "none detected" in result.lower()

    def test_template_version_metadata(self) -> None:
        """Test prompt template version and use case."""
        prompt = SignalNoisePromptV1()
        assert prompt.version == "v1"
        assert prompt.use_case == "signal_noise_classification"

    def test_repr(self) -> None:
        """Test prompt repr."""
        prompt = SignalNoisePromptV1()
        repr_str = repr(prompt)
        assert "SignalNoisePromptV1" in repr_str
        assert "v1" in repr_str


class TestCompanyInferencePromptV1:
    """Test company name inference prompt template."""

    def test_render_basic(self) -> None:
        """Test basic company inference prompt rendering."""
        prompt = CompanyInferencePromptV1()
        result = prompt.render(
            domain="acme.com",
            titles_text=prompt.render_titles(["ACME Corp"]),
            products_text=prompt.render_products(["nginx"]),
        )

        assert "acme.com" in result
        assert "ACME Corp" in result
        assert "nginx" in result

    def test_render_empty_titles_and_products(self) -> None:
        """Test prompt with empty titles and products."""
        prompt = CompanyInferencePromptV1()
        result = prompt.render(
            domain="example.com",
            titles_text=prompt.render_titles([]),
            products_text=prompt.render_products([]),
        )

        assert "example.com" in result
        assert result.count("None detected") >= 1  # At least one "None detected"

    def test_render_multiple_products(self) -> None:
        """Test prompt with multiple products."""
        prompt = CompanyInferencePromptV1()
        products = ["Apache", "PHP", "MySQL"]
        result = prompt.render(
            domain="site.com",
            titles_text=prompt.render_titles(["Site Title"]),
            products_text=prompt.render_products(products),
        )

        for product in products:
            assert product in result

    def test_template_version_metadata(self) -> None:
        """Test prompt template version and use case."""
        prompt = CompanyInferencePromptV1()
        assert prompt.version == "v1"
        assert prompt.use_case == "company_name_inference"

    def test_repr(self) -> None:
        """Test prompt repr."""
        prompt = CompanyInferencePromptV1()
        repr_str = repr(prompt)
        assert "CompanyInferencePromptV1" in repr_str
        assert "v1" in repr_str


class TestRiskNarrativePromptV1:
    """Test risk narrative generation prompt template."""

    def test_render_basic(self) -> None:
        """Test basic risk narrative prompt rendering."""
        prompt = RiskNarrativePromptV1()
        result = prompt.render(
            domain="example.com",
            risk_score="85.0",
            signal_tags_text=prompt.render_signal_tags(["CRITICAL_CVE", "EXPOSED_DATABASE"]),
            exposures_text=prompt.render_exposures({"database": 2, "legacy_protocol": 1}),
        )

        assert "example.com" in result
        assert "85.0" in result
        assert "critical vulnerabilities" in result
        assert "Database exposed" in result
        assert "database: 2" in result
        assert "legacy_protocol: 1" in result

    def test_render_empty_signal_tags(self) -> None:
        """Test prompt with empty signal tags."""
        prompt = RiskNarrativePromptV1()
        result = prompt.render(
            domain="example.com",
            risk_score="50.0",
            signal_tags_text=prompt.render_signal_tags([]),
            exposures_text=prompt.render_exposures({}),
        )

        assert "example.com" in result
        assert "None" in result

    def test_render_risk_score_formatting(self) -> None:
        """Test risk score is formatted to one decimal place."""
        prompt = RiskNarrativePromptV1()
        result = prompt.render(
            domain="example.com",
            risk_score="75.5",
            signal_tags_text=prompt.render_signal_tags([]),
            exposures_text=prompt.render_exposures({}),
        )

        assert "75.5" in result

    def test_render_multiple_exposures(self) -> None:
        """Test prompt with multiple exposures."""
        prompt = RiskNarrativePromptV1()
        exposures = {
            "database": 3,
            "legacy_protocol": 2,
            "weak_tls": 5,
        }
        result = prompt.render(
            domain="example.com",
            risk_score="90.0",
            signal_tags_text=prompt.render_signal_tags([]),
            exposures_text=prompt.render_exposures(exposures),
        )

        for exposure_type, count in exposures.items():
            assert f"{exposure_type}: {count}" in result

    def test_signal_tag_descriptions_included(self) -> None:
        """Test signal tags are described in prompt."""
        prompt = RiskNarrativePromptV1()
        result = prompt.render(
            domain="example.com",
            risk_score="80.0",
            signal_tags_text=prompt.render_signal_tags(["KNOWN_VULNERABILITIES"]),
            exposures_text=prompt.render_exposures({}),
        )

        assert "Known vulnerabilities" in result

    def test_template_version_metadata(self) -> None:
        """Test prompt template version and use case."""
        prompt = RiskNarrativePromptV1()
        assert prompt.version == "v1"
        assert prompt.use_case == "risk_narrative_generation"

    def test_repr(self) -> None:
        """Test prompt repr."""
        prompt = RiskNarrativePromptV1()
        repr_str = repr(prompt)
        assert "RiskNarrativePromptV1" in repr_str
        assert "v1" in repr_str


class TestOutreachDraftPromptV1:
    """Test outreach draft generation prompt template."""

    def test_render_basic(self) -> None:
        """Test basic outreach draft prompt rendering."""
        prompt = OutreachDraftPromptV1()
        result = prompt.render(
            company_name="Acme Corp",
            risk_score="85.0",
            narrative="Your infrastructure has critical vulnerabilities.",
        )

        assert "Acme Corp" in result
        assert "85.0" in result
        assert "critical vulnerabilities" in result

    def test_render_different_risk_scores(self) -> None:
        """Test prompt with different risk scores."""
        prompt = OutreachDraftPromptV1()

        result_high = prompt.render(
            company_name="Company A",
            risk_score="95.0",
            narrative="Test narrative",
        )
        result_low = prompt.render(
            company_name="Company B",
            risk_score="30.0",
            narrative="Test narrative",
        )

        assert "95.0" in result_high
        assert "30.0" in result_low

    def test_render_long_narrative(self) -> None:
        """Test prompt with long narrative excerpt."""
        prompt = OutreachDraftPromptV1()
        long_narrative = (
            "This domain hosts infrastructure with multiple critical issues "
            "including exposed databases, outdated protocols, and known vulnerabilities."
        )
        result = prompt.render(
            company_name="Big Corp",
            risk_score="88.0",
            narrative=long_narrative,
        )

        assert long_narrative in result

    def test_render_special_characters_in_company_name(self) -> None:
        """Test prompt with special characters in company name."""
        prompt = OutreachDraftPromptV1()
        result = prompt.render(
            company_name="O'Reilly & Associates",
            risk_score="75.0",
            narrative="Test narrative",
        )

        assert "O'Reilly & Associates" in result

    def test_template_version_metadata(self) -> None:
        """Test prompt template version and use case."""
        prompt = OutreachDraftPromptV1()
        assert prompt.version == "v1"
        assert prompt.use_case == "outreach_draft_generation"

    def test_repr(self) -> None:
        """Test prompt repr."""
        prompt = OutreachDraftPromptV1()
        repr_str = repr(prompt)
        assert "OutreachDraftPromptV1" in repr_str
        assert "v1" in repr_str


class TestPromptTemplateConsistency:
    """Test consistency across all prompt templates."""

    def test_all_prompts_have_version(self) -> None:
        """Test all prompts have version attribute."""
        prompts = [
            SignalNoisePromptV1(),
            CompanyInferencePromptV1(),
            RiskNarrativePromptV1(),
            OutreachDraftPromptV1(),
        ]

        for prompt in prompts:
            assert hasattr(prompt, "version")
            assert prompt.version == "v1"

    def test_all_prompts_have_use_case(self) -> None:
        """Test all prompts have use_case attribute."""
        prompts = [
            SignalNoisePromptV1(),
            CompanyInferencePromptV1(),
            RiskNarrativePromptV1(),
            OutreachDraftPromptV1(),
        ]

        for prompt in prompts:
            assert hasattr(prompt, "use_case")
            assert isinstance(prompt.use_case, str)
            assert len(prompt.use_case) > 0

    def test_all_prompts_have_template(self) -> None:
        """Test all prompts have template attribute."""
        prompts = [
            SignalNoisePromptV1(),
            CompanyInferencePromptV1(),
            RiskNarrativePromptV1(),
            OutreachDraftPromptV1(),
        ]

        for prompt in prompts:
            assert hasattr(prompt, "template")
            assert isinstance(prompt.template, str)
            assert len(prompt.template) > 0

    def test_no_duplicate_use_cases(self) -> None:
        """Test each prompt has unique use case."""
        prompts = [
            SignalNoisePromptV1(),
            CompanyInferencePromptV1(),
            RiskNarrativePromptV1(),
            OutreachDraftPromptV1(),
        ]

        use_cases = [p.use_case for p in prompts]
        assert len(use_cases) == len(set(use_cases))

    def test_all_prompts_repr_consistent(self) -> None:
        """Test all prompts have consistent repr format."""
        prompts = [
            SignalNoisePromptV1(),
            CompanyInferencePromptV1(),
            RiskNarrativePromptV1(),
            OutreachDraftPromptV1(),
        ]

        for prompt in prompts:
            repr_str = repr(prompt)
            assert "v1" in repr_str
            assert prompt.use_case in repr_str
