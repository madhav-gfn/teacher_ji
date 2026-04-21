import { create } from "zustand";
import type {
  FeedbackOutput,
  QuizQuestion,
  SessionMode,
  Subject,
  TeachingOutput,
} from "../api/client";

const STORAGE_KEY = "teacher-ji-student-id";

function getOrCreateStudentId() {
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const generated = `student-${Math.random().toString(36).slice(2, 10)}`;
  window.localStorage.setItem(STORAGE_KEY, generated);
  return generated;
}

interface SessionState {
  studentId: string;
  sessionId: string | null;
  grade: number | null;
  subject: Subject | null;
  chapter: string | null;
  currentTopic: string | null;
  topicsCompleted: string[];
  topicsRemaining: string[];
  sessionScore: number;
  weakTopics: string[];
  quizQuestions: QuizQuestion[];
  currentQuestionIndex: number;
  mode: SessionMode;
  teachingOutput: TeachingOutput | null;
  feedbackOutput: FeedbackOutput | null;
  setSession: (payload: Partial<SessionState>) => void;
  markTopicComplete: (topic: string) => void;
  setQuizData: (questions: QuizQuestion[]) => void;
  updateScore: (score: number) => void;
  addWeakTopic: (topic: string) => void;
  removeWeakTopic: (topic: string) => void;
  setMode: (mode: SessionMode) => void;
  setTeachingOutput: (output: TeachingOutput | null) => void;
  setFeedbackOutput: (output: FeedbackOutput | null) => void;
  setCurrentQuestionIndex: (index: number) => void;
  resetSession: () => void;
}

const initialState = () => ({
  studentId: getOrCreateStudentId(),
  sessionId: null,
  grade: null,
  subject: null,
  chapter: null,
  currentTopic: null,
  topicsCompleted: [],
  topicsRemaining: [],
  sessionScore: 0,
  weakTopics: [],
  quizQuestions: [],
  currentQuestionIndex: 0,
  mode: "selection" as SessionMode,
  teachingOutput: null,
  feedbackOutput: null,
});

export const useSessionStore = create<SessionState>((set) => ({
  ...initialState(),
  setSession: (payload) => set((state) => ({ ...state, ...payload })),
  markTopicComplete: (topic) =>
    set((state) => ({
      topicsCompleted: state.topicsCompleted.includes(topic)
        ? state.topicsCompleted
        : [...state.topicsCompleted, topic],
      topicsRemaining: state.topicsRemaining.filter((item) => item !== topic),
    })),
  setQuizData: (questions) =>
    set({
      quizQuestions: questions,
      currentQuestionIndex: 0,
      feedbackOutput: null,
    }),
  updateScore: (score) => set({ sessionScore: score }),
  addWeakTopic: (topic) =>
    set((state) => ({
      weakTopics: state.weakTopics.includes(topic) ? state.weakTopics : [...state.weakTopics, topic],
    })),
  removeWeakTopic: (topic) =>
    set((state) => ({
      weakTopics: state.weakTopics.filter((item) => item !== topic),
    })),
  setMode: (mode) => set({ mode }),
  setTeachingOutput: (output) => set({ teachingOutput: output }),
  setFeedbackOutput: (output) => set({ feedbackOutput: output }),
  setCurrentQuestionIndex: (index) => set({ currentQuestionIndex: index }),
  resetSession: () =>
    set(() => ({
      ...initialState(),
    })),
}));
