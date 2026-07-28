import { getAuthToken } from "./authToken";

export type Subject = "math" | "science" | "sst" | "custom";
export type SessionMode = "selection" | "documents" | "teaching" | "quiz" | "results";

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
  // Generic "study your own material" schema (agents/document_agent.py)
  example?: string;
  key_points?: string[];
}

export interface StartSessionRequest {
  document_id?: string;
  grade?: number;
  subject?: "math" | "science" | "sst";
  chapter?: string;
  topic?: string;
  custom_topics?: string[];
}

export interface DocumentSummary {
  document_id: string;
  title: string;
  filename: string;
  topic_count: number;
  chunk_count: number;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  topics: string[];
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

// Mirrors backend/api/models.py:StudentProfile exactly - the Phase 1B Memory
// model (per-concept mastery/confidence), not a session log.
export interface StudentProfile {
  student_id: string;
  grade: number;
  learning_style: string;
  mastery: Record<string, number>;
  confidence: Record<string, number>;
  weak_topics: string[];
  revision_due: string[];
  quiz_history: QuizHistoryEntry[];
  total_sessions: number;
}

const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function parseResponse<TResponse>(response: Response): Promise<TResponse> {
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

async function request<TResponse>(
  path: string,
  init?: RequestInit,
): Promise<TResponse> {
  const token = await getAuthToken();

  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  return parseResponse<TResponse>(response);
}

// Phase 3B: SSE streaming. Deliberately not EventSource - it can't send a POST
// body or an Authorization header, both of which every endpoint here needs.
// A manual fetch + ReadableStream reader parsing the `event:`/`data:` frame
// format is the standard workaround for authenticated/POST SSE in browsers.
export type StreamEvent<TDone> =
  | { event: "token"; data: string }
  | { event: "done"; data: TDone }
  | { event: "error"; data: { detail: string } };

async function* streamRequest<TDone>(
  path: string,
  body: unknown,
): AsyncGenerator<StreamEvent<TDone>> {
  const token = await getAuthToken();

  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "");
    let detail = text || `Request failed with status ${response.status}`;
    try {
      const parsed = text ? JSON.parse(text) : null;
      if (parsed && typeof parsed.detail === "string") {
        detail = parsed.detail;
      }
    } catch {
      // not JSON - use the raw text as-is
    }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventName = "message";
      let dataLine = "";
      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLine += line.slice(5).trim();
        }
      }

      if (dataLine) {
        yield { event: eventName, data: JSON.parse(dataLine) } as StreamEvent<TDone>;
      }

      boundary = buffer.indexOf("\n\n");
    }
  }
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
  streamStartSession(body: StartSessionRequest) {
    return streamRequest<TeachingResponse>("/session/start/stream", body);
  },
  streamNextTopic(body: NextTopicRequest) {
    return streamRequest<TeachingResponse | ChapterCompleteResponse>("/session/next-topic/stream", body);
  },
  streamSessionQuestion(body: SessionQuestionRequest) {
    return streamRequest<TeachingResponse>("/session/question/stream", body);
  },
  streamExplainDifferently(body: ExplainDifferentlyRequest) {
    return streamRequest<TeachingResponse>("/session/explain-differently/stream", body);
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
  getStudentProfile(studentId: string) {
    return request<StudentProfile>(`/student/${studentId}`);
  },
  async uploadDocument(file: File, title?: string) {
    const form = new FormData();
    form.append("file", file);
    if (title) {
      form.append("title", title);
    }
    const token = await getAuthToken();
    const response = await fetch(`${BASE_URL}/documents/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
    });
    return parseResponse<DocumentDetail>(response);
  },
  listDocuments() {
    return request<DocumentSummary[]>("/documents");
  },
  getDocument(documentId: string) {
    return request<DocumentDetail>(`/documents/${documentId}`);
  },
  deleteDocument(documentId: string) {
    return request<{ status: string; document_id: string }>(`/documents/${documentId}`, {
      method: "DELETE",
    });
  },
};
