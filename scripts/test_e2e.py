import httpx, sys, time

BASE = "http://localhost:8000"
client = httpx.Client(timeout=30)
results = []

def test(name, fn):
    try:
        fn()
        print(f"  PASS  {name}")
        results.append(True)
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        results.append(False)

session_id = None
quiz_questions = []

def t1():
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200

def t2():
    global session_id
    r = client.post(f"{BASE}/session/start", json={
        "student_id": "test_01", "grade": 6, "subject": "math",
        "chapter": "Knowing Our Numbers", "topic": "Introduction to large numbers"
    })
    assert r.status_code == 200
    d = r.json()
    assert "session_id" in d
    for key in ["headline","explanation","ncert_example","analogy","common_mistake","guiding_question"]:
        assert key in d["teaching_output"], f"missing key: {key}"
    session_id = d["session_id"]

def t3():
    r = client.post(f"{BASE}/session/next-topic", json={
        "session_id": session_id, "completed_topic": "Introduction to large numbers"
    })
    assert r.status_code == 200
    d = r.json()
    assert "teaching_output" in d or d.get("ready_for_quiz") == True

def t4():
    global quiz_questions
    r = client.post(f"{BASE}/quiz/start", json={"session_id": session_id})
    assert r.status_code == 200
    d = r.json()
    assert len(d["questions"]) >= 3
    for q in d["questions"]:
        for key in ["question_id","question","options","correct_answer","explanation","concept_tested"]:
            assert key in q
    quiz_questions = d["questions"]

def t5():
    r = client.post(f"{BASE}/quiz/submit-answer", json={
        "session_id": session_id, "question_id": 1, "student_answer": "Z_WRONG_ANSWER"
    })
    assert r.status_code == 200
    d = r.json()
    assert d["feedback_output"]["is_correct"] == False
    assert d["feedback_output"]["hint_if_wrong"] is not None

for name, fn in [("Health check", t1), ("Start session + teaching output", t2),
                  ("Next topic progression", t3), ("Quiz generation", t4),
                  ("Feedback on wrong answer", t5)]:
    test(name, fn)

passed = sum(results)
print(f"\n{passed}/{len(results)} tests passed")
sys.exit(0 if passed == len(results) else 1)
