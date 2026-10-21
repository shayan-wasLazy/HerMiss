from agents.adaptive_quiz import AdaptiveQuizPolicy, QuizGenerationError, generate_mcqs


def test_generates_mcqs_grounded_in_text():
    text = (
        "Convolutional Neural Networks use convolution to detect local patterns. "
        "Pooling reduces spatial dimensions and can lower computation. "
        "Backpropagation computes gradients for updating model parameters. "
        "Activation functions introduce nonlinearity into a neural network."
    )
    questions = generate_mcqs(text, count=4, source_name="notes.txt")
    assert len(questions) == 4
    for question in questions:
        assert len(question["options"]) == 4
        assert question["answer"] in question["options"]
        assert "uploaded notes" in question["question"]


def test_rejects_empty_notes():
    import pytest
    with pytest.raises(QuizGenerationError):
        generate_mcqs("")


def test_policy_tracks_wrong_and_slow_answers(tmp_path):
    policy = AdaptiveQuizPolicy(tmp_path / "progress.json")
    policy.record_answer("q1", False, 35)
    result = policy.record_answer("q1", False, 30)
    assert result["wrong"] == 2
    assert result["slow"] == 2
    assert policy.summary()["repeatedly_missed"] == 1
    loaded = AdaptiveQuizPolicy(tmp_path / "progress.json")
    assert loaded.stats["q1"]["attempts"] == 2
