import asyncio
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))
from agents.state import LearningState
from agents.subject_agents import math_agent

async def main():
    state: LearningState = {
        "student_id": "123",
        "grade": 6,
        "subject": "math",
        "chapter": "Knowing Our Numbers",
        "topic": "Introduction",
        "mode": "teaching",
        "retrieved_context": [],
        "teaching_output": {},
        "quiz_questions": [],
        "current_question_index": 0,
        "student_answer": "",
        "feedback_output": {},
        "session_score": 0.0,
        "weak_topics": [],
        "messages": [],
    }
    print("Running math_agent...")
    res = math_agent(state)
    print("Success:", res)

if __name__ == "__main__":
    asyncio.run(main())
