"""Quick start example for jfinqa."""

from jfinqa import evaluate, load_from_file

# Load sample questions from local file
questions = load_from_file("tests/fixtures/sample_questions.json")
print(f"Loaded {len(questions)} questions")

# Create perfect predictions (for demonstration)
predictions = {q.id: q.qa.answer for q in questions}

# Run evaluation
result = evaluate(questions, predictions=predictions)
print(result.summary())

# Inspect individual results
for r in result.results:
    status = "OK" if r.correct else "WRONG"
    print(f"  [{status}] {r.question_id}: {r.predicted}")
