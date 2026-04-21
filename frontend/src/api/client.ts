export type Subject = "math" | "science" | "sst";
export type SessionMode = "selection" | "teaching" | "quiz" | "results";

export interface TimelineEvent {
  year: string;
  event: string;
}

export interface TeachingOutput {
  headline?: string;
  explanation?: string | string[];
  ncert_example?: string;
  analogy?: string;
  common_mistake?: string;
  guiding_question?: string;
  real_world_example?: string;
  diagram_description?: string;
  story?: string;
  key_facts?: string[];
  mnemonic?: string;
  timeline?: TimelineEvent[];
  connection_to_present?: string;
  topics_covered?: string[];
}

export interface StartSessionRequest {
  student_id: string;
  grade: number;
  subject: Subject;
  chapter: string;
  topic: string;
  custom_topics?: string[];
}

export interface TeachingResponse {
  session_id: string;
  subject: Subject;
  chapter: string;
  topic: string;
  teaching_output: TeachingOutput;
  retrieved_chunks: Record<string, unknown>[];
  next_topics: string[];
}

export interface ChapterCompleteResponse {
  session_id: string;
  ready_for_quiz: true;
  chapter_summary: Record<string, unknown>;
  topics_covered: string[];
}

export interface NextTopicRequest {
  session_id: string;
  completed_topic: string;
}

export interface StartQuizRequest {
  session_id: string;
}

export interface SessionQuestionRequest {
  session_id: string;
  question: string;
}

export interface ExplainDifferentlyRequest {
  session_id: string;
  hint: string;
}

export interface QuizQuestion {
  question_id: number;
  question_type: "mcq" | "short_answer";
  question: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  concept_tested: string;
  difficulty: "easy" | "medium" | "hard";
  evaluation?: FeedbackOutput;
}

export interface QuizResponse {
  session_id: string;
  questions: QuizQuestion[];
  total_questions: number;
}

export interface SubmitAnswerRequest {
  session_id: string;
  question_id: number;
  student_answer: string;
}

export interface FeedbackOutput {
  is_correct: boolean;
  verdict: "correct" | "partially_correct" | "incorrect";
  feedback: string;
  encouragement: string;
  hint_if_wrong?: string | null;
  concept_strength: "mastered" | "developing" | "needs_revision";
  suggested_revision?: string | null;
}

export interface FeedbackResponse {
  session_id: string;
  question_id: number;
  feedback_output: FeedbackOutput;
  session_score_so_far: number;
  questions_remaining: number;
}

export interface UpdateStudentProfileRequest {
  session_id: string;
  subject: Subject;
  chapter: string;
  session_score: number;
  mastered_topics: string[];
  weak_topics: string[];
  quiz_date: string;
}

export interface QuizHistoryEntry {
  date: string;
  subject: string;
  chapter: string;
  score: number;
}

export interface StudentProfile {
  student_id: string;
  grade: number;
  topics_mastered: Record<string, string[]>;
  weak_topics: Record<string, string[]>;
  quiz_history: QuizHistoryEntry[];
  total_sessions: number;
}

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request<TResponse>(
  path: string,
  init?: RequestInit,
): Promise<TResponse> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const text = await response.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!response.ok) {
    const detail =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof (data as { detail: unknown }).detail === "string"
        ? (data as { detail: string }).detail
        : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return data as TResponse;
}

export const apiClient = {
  startSession(body: StartSessionRequest) {
    return request<TeachingResponse>("/session/start", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  nextTopic(body: NextTopicRequest) {
    return request<TeachingResponse | ChapterCompleteResponse>("/session/next-topic", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  askSessionQuestion(body: SessionQuestionRequest) {
    return request<TeachingResponse>("/session/question", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  explainDifferently(body: ExplainDifferentlyRequest) {
    return request<TeachingResponse>("/session/explain-differently", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  startQuiz(body: StartQuizRequest) {
    return request<QuizResponse>("/quiz/start", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  submitAnswer(body: SubmitAnswerRequest) {
    return request<FeedbackResponse>("/quiz/submit-answer", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateStudentProfile(studentId: string, body: UpdateStudentProfileRequest) {
    return request<StudentProfile>(`/student/${studentId}/update`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};
