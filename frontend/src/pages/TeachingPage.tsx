import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { Sidebar } from "../components/Sidebar";
import { TeachingCard } from "../components/TeachingCard";
import { useSessionStore } from "../store/sessionStore";

function isChapterCompleteResponse(
  response: Awaited<ReturnType<typeof apiClient.nextTopic>>,
): response is {
  session_id: string;
  ready_for_quiz: true;
  chapter_summary: Record<string, unknown>;
  topics_covered: string[];
} {
  return "ready_for_quiz" in response;
}

export function TeachingPage() {
  const [showQuestionInput, setShowQuestionInput] = useState(false);
  const [questionText, setQuestionText] = useState("");
  const {
    sessionId,
    subject,
    chapter,
    currentTopic,
    topicsCompleted,
    topicsRemaining,
    teachingOutput,
    setSession,
    markTopicComplete,
  } = useSessionStore();

  const nextTopic = useMutation({
    mutationFn: async () => {
      if (!sessionId || !currentTopic) {
        throw new Error("Session is not ready.");
      }

      return apiClient.nextTopic({
        session_id: sessionId,
        completed_topic: currentTopic,
      });
    },
    onSuccess: (response) => {
      if (!currentTopic) {
        return;
      }

      markTopicComplete(currentTopic);

      if (isChapterCompleteResponse(response)) {
        setSession({
          mode: "quiz",
          currentTopic: null,
          teachingOutput: null,
          topicsRemaining: [],
        });
        return;
      }

      setSession({
        currentTopic: response.topic,
        topicsRemaining: response.next_topics,
        teachingOutput: response.teaching_output,
        feedbackOutput: null,
      });
    },
  });

  const askQuestion = useMutation({
    mutationFn: async (question: string) => {
      if (!sessionId) {
        throw new Error("Session is not ready.");
      }

      return apiClient.askSessionQuestion({
        session_id: sessionId,
        question,
      });
    },
    onSuccess: (response) => {
      setSession({
        currentTopic: response.topic,
        topicsRemaining: response.next_topics,
        teachingOutput: response.teaching_output,
        feedbackOutput: null,
      });
      setQuestionText("");
      setShowQuestionInput(false);
    },
  });

  const explainDifferently = useMutation({
    mutationFn: async () => {
      if (!sessionId || !currentTopic) {
        throw new Error("Session is not ready.");
      }

      return apiClient.explainDifferently({
        session_id: sessionId,
        hint: `Use a different example and a different phrasing for the topic "${currentTopic}".`,
      });
    },
    onSuccess: (response) => {
      setSession({
        currentTopic: response.topic,
        topicsRemaining: response.next_topics,
        teachingOutput: response.teaching_output,
        feedbackOutput: null,
      });
    },
  });

  if (!sessionId || !subject || !chapter || !currentTopic || !teachingOutput) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50 p-6">
        <div className="rounded-2xl border border-gray-100 bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-semibold text-gray-900">No active teaching session.</p>
          <button
            type="button"
            onClick={() => setSession({ mode: "selection" })}
            className="mt-4 rounded-xl bg-purple-600 px-5 py-3 text-sm font-semibold text-white"
          >
            Go to chapter selection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-stone-50">
      <Sidebar
        subject={subject}
        chapter={chapter}
        currentTopic={currentTopic}
        topicsCompleted={topicsCompleted}
        topicsRemaining={topicsRemaining}
      />

      <main className="min-w-0 flex-1 px-6 py-6 lg:px-8">
        <div className="mx-auto max-w-5xl">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentTopic}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -18 }}
              transition={{ duration: 0.25 }}
            >
              <TeachingCard
                subject={subject}
                chapter={chapter}
                topic={currentTopic}
                teachingOutput={teachingOutput}
                isAdvancing={nextTopic.isPending}
                isRefreshing={explainDifferently.isPending}
                onNext={() => nextTopic.mutate()}
                onExplainDifferently={() => explainDifferently.mutate()}
              />
            </motion.div>
          </AnimatePresence>

          <div className="mt-5 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-900">Ask a question about this</p>
                  <p className="text-sm text-gray-500">
                    Send a focused follow-up and re-teach the same topic with that context.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowQuestionInput((value) => !value)}
                  className="rounded-xl border border-gray-200 px-4 py-3 text-sm font-semibold text-gray-700 transition hover:border-purple-200 hover:text-purple-700"
                >
                  {showQuestionInput ? "Hide question box" : "Ask a question about this"}
                </button>
              </div>

              {showQuestionInput ? (
                <div className="rounded-2xl border border-purple-100 bg-purple-50 p-4">
                  <textarea
                    value={questionText}
                    onChange={(event) => setQuestionText(event.target.value)}
                    placeholder="Ask a specific question about this topic..."
                    className="min-h-28 w-full rounded-xl border border-purple-100 bg-white px-4 py-3 text-sm text-gray-700 outline-none transition focus:border-purple-300 focus:ring-2 focus:ring-purple-100"
                  />
                  <div className="mt-3 flex flex-wrap items-center justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setQuestionText("");
                        setShowQuestionInput(false);
                      }}
                      className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold text-gray-700"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={!questionText.trim() || askQuestion.isPending}
                      onClick={() => askQuestion.mutate(questionText.trim())}
                      className="rounded-xl bg-purple-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
                    >
                      {askQuestion.isPending ? "Sending question..." : "Submit question"}
                    </button>
                  </div>
                </div>
              ) : null}
            </div>

            {nextTopic.error ? (
              <p className="mt-4 text-sm text-red-600">{nextTopic.error.message}</p>
            ) : null}
            {askQuestion.error ? (
              <p className="mt-4 text-sm text-red-600">{askQuestion.error.message}</p>
            ) : null}
            {explainDifferently.error ? (
              <p className="mt-4 text-sm text-red-600">{explainDifferently.error.message}</p>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
}
