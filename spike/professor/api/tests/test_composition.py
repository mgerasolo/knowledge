import pytest

from composition import (
    CitationIntegrityError,
    TierParseError,
    parse_tier_json,
    validate_citation_integrity,
)


VALID = {
    "said": [{"text": "I teach value.", "citations": [1, 2]}],
    "might_say": "Inference: increase certainty.",
    "extension": "He hasn't directly addressed this; test the offer.",
}


@pytest.mark.parametrize(
    "text",
    [
        '{"tiers":{"said":[{"text":"I teach value.","citations":[1,2]}],"might_say":"Inference: increase certainty.","extension":"He hasn\'t directly addressed this; test the offer."}}',
        '```json\n{"said":[{"text":"I teach value.","citations":[1,2]}],"might_say":"Inference: increase certainty.","extension":"He hasn\'t directly addressed this; test the offer."}\n```',
        'Model preface {"tiers":{"said":[{"text":"I teach value.","citations":[1,2]}],"might_say":"Inference: increase certainty.","extension":"He hasn\'t directly addressed this; test the offer."}} trailing',
    ],
)
def test_tier_parser_accepts_plain_fenced_and_wrapped_json(text):
    tiers = parse_tier_json(text)
    assert tiers["said"][0]["citations"] == [1, 2]
    assert set(tiers) == {"said", "might_say", "extension"}


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"tiers":{"said":"bad","might_say":"x","extension":"y"}}',
        '{"tiers":{"said":[{"text":"x","citations":[true]}],"might_say":"x","extension":"y"}}',
        '{"tiers":{"said":[{"text":"x","citations":[]}],"might_say":"x","extension":"y"}}',
        '{"tiers":{"said":[{"text":"   ","citations":[1]}],"might_say":"x","extension":"y"}}',
        '{"tiers":{"said":[],"might_say":"x","extension":"   "}}',
        '{"tiers":{"said":[],"might_say":[],"extension":"y"}}',
    ],
)
def test_tier_parser_rejects_invalid_contract(text):
    with pytest.raises(TierParseError):
        parse_tier_json(text)


def test_citation_integrity_accepts_only_retrieved_numbers():
    validate_citation_integrity(VALID, {1, 2})
    with pytest.raises(CitationIntegrityError, match="3"):
        validate_citation_integrity(
            {**VALID, "said": [{"text": "fabricated", "citations": [3]}]}, {1, 2}
        )


class ScriptedLLM:
    def __init__(self, responses):
        self.responses = iter(responses)

    def chat(self, model, messages, **options):
        return {"content": next(self.responses), "usage": {}, "model": model}


class ComposerConfig:
    CHAT_MODEL = "main"
    EXTENSION_MODEL = "extension"
    ENABLE_EXTENSION_MODEL = True


def test_composer_enforces_labels_after_extension_model_output():
    from composition import Composer
    from corpus import PersonalityCorpus, Video

    llm = ScriptedLLM([
        '{"tiers":{"said":[{"text":"I teach value.","citations":[1]}],"might_say":"Add certainty.","extension":"General advice."}}',
        "Test the wording with customers.",
    ])
    corpus = PersonalityCorpus("p", "Teacher", "", (Video("v", "V", None, 10),))
    result = Composer(llm, ComposerConfig).compose(
        "How?", [{"video_youtube_id": "v", "start_time": 1, "end_time": 2, "text": "Value"}], corpus
    )
    assert result.tiers["might_say"].startswith("Inference:")
    assert result.tiers["extension"].startswith("He hasn't directly addressed this.")


def test_composer_returns_tier_c_only_when_retrieval_is_silent():
    from composition import Composer
    from corpus import PersonalityCorpus

    llm = ScriptedLLM([
        '{"tiers":{"said":[],"might_say":"A guess.","extension":"General advice."}}',
        "General model advice.",
    ])
    corpus = PersonalityCorpus("p", "Teacher", "", ())
    tiers = Composer(llm, ComposerConfig).compose("Novel?", [], corpus).tiers
    assert tiers["said"] == []
    assert tiers["might_say"] == ""
    assert "corpus is silent" in tiers["extension"].lower()
    assert "hasn't directly addressed" in tiers["extension"].lower()


def test_tier_parser_takes_first_object_when_trailing_braces_follow():
    # Live failure 2026-08-14: model appended commentary containing braces
    # after the tier object; an rfind("}")-slice produced "Extra data".
    text = (
        '{"tiers":{"said":[{"text":"I teach value.","citations":[1]}],'
        '"might_say":"Inference: x.","extension":"He hasn\'t directly addressed this."}}'
        ' Note: {"unrelated": "object"}'
    )
    tiers = parse_tier_json(text)
    assert tiers["said"][0]["citations"] == [1]


def test_rewrite_filters_usage_to_integer_token_keys():
    # Live failure 2026-08-14: LiteLLM usage carries nested *_tokens_details
    # dicts; the service's int() conversion must never see them.
    from composition import Composer

    class UsageLLM:
        def chat(self, model, messages, **options):
            return {
                "content": "standalone query",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 8,
                    "total_tokens": 108,
                    "prompt_tokens_details": {"cached_tokens": 0},
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
                "model": model,
            }

    query, usage = Composer(UsageLLM(), ComposerConfig).rewrite(
        "what about pricing?", [{"role": "user", "content": "offers"}]
    )
    assert query == "standalone query"
    assert usage == {"prompt_tokens": 100, "completion_tokens": 8, "total_tokens": 108}
    assert all(isinstance(value, int) for value in usage.values())
