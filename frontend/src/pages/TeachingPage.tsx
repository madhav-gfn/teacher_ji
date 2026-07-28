import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { apiClient, type ChapterCompleteResponse, type TeachingResponse } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { Sidebar } from "../components/Sidebar";
import { TeachingCard } from "../components/TeachingCard";
import { useSessionStore } from "../store/sessionStore";

function isChapterCompleteResponse(
  response: TeachingResponse | ChapterCompleteResponse,
): response is ChapterCompleteResponse {
  return "ready_for_quiz" in response;
}

export function TeachingPage() {
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

  // Phase 3B: "Next topic" and "Explain differently" both regenerate the
  // whole card, so - unlike the chat panel - there's no structured content to
  // render incrementally. Tokens still stream live into streamPreview while
  // the request is in flight (an honest "the agent is actually generating
  // this now" signal), then the TeachingCard swaps in once `done` lands.
  const [streamPreview, setStreamPreview] = useState("");
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [nextTopicError, setNextTopicError] = useState<string | null>(null);
  const [explainError, setExplainError] = useState<string | null>(null);

  const advanceTopic = async () => {
    if (!sessionId || !currentTopic) {
      return;
    }
    setIsAdvancing(true);
    setStreamPreview("");
    setNextTopicError(null);
    try {
      for await (const event of apiClient.streamNextTopic({
        session_id: sessionId,
        completed_topic: currentTopic,
      })) {
        if (event.event === "token") {
          setStreamPreview((prev) => prev + event.data);
        } else if (event.event === "done") {
          markTopicComplete(currentTopic);
          if (isChapterCompleteResponse(event.data)) {
            setSession({ mode: "quiz", currentTopic: null, teachingOutput: null, topicsRemaining: [] });
          } else {
            setSession({
              currentTopic: event.data.topic,
              topicsRemaining: event.data.next_topics,
              teachingOutput: event.data.teaching_output,
              feedbackOutput: null,
            });
          }
        } else if (event.event === "error") {
          setNextTopicError(event.data.detail);
        }
      }
    } catch (error) {
      setNextTopicError(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setIsAdvancing(false);
      setStreamPreview("");
    }
  };

  const requestExplainDifferently = async () => {
    if (!sessionId || !currentTopic) {
      return;
    }
    setIsRefreshing(true);
    setStreamPreview("");
    setExplainError(null);
    try {
      for await (const event of apiClient.streamExplainDifferently({
        session_id: sessionId,
        hint: `Use a different example and a different phrasing for the topic "${currentTopic}".`,
      })) {
        if (event.event === "token") {
          setStreamPreview((prev) => prev + event.data);
        } else if (event.event === "done") {
          setSession({
            currentTopic: event.data.topic,
            topicsRemaining: event.data.next_topics,
            teachingOutput: event.data.teaching_output,
            feedbackOutput: null,
          });
        } else if (event.event === "error") {
          setExplainError(event.data.detail);
        }
      }
    } catch (error) {
      setExplainError(error instanceof Error ? error.message : "Something went wrong.");
    } finally {
      setIsRefreshing(false);
      setStreamPreview("");
    }
  };

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
        <div className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="min-w-0">
            {isAdvancing || isRefreshing ? (
              <div className="mb-4 rounded-2xl border border-purple-100 bg-purple-50 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-purple-700">
                  {isAdvancing ? "Teaching the next topic..." : "Rebuilding the explanation..."}
                </p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-purple-950">
                  {streamPreview || "Thinking..."}
                </p>
              </div>
            ) : null}

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
                  isAdvancing={isAdvancing}
                  isRefreshing={isRefreshing}
                  onNext={() => void advanceTopic()}
                  onExplainDifferently={() => void requestExplainDifferently()}
                />
              </motion.div>
            </AnimatePresence>

            {nextTopicError ? <p className="mt-4 text-sm text-red-600">{nextTopicError}</p> : null}
            {explainError ? <p className="mt-4 text-sm text-red-600">{explainError}</p> : null}
          </div>

          <div className="h-[calc(100vh-6rem)] lg:sticky lg:top-6">
            <ChatPanel />
          </div>
        </div>
      </main>
    </div>
  );
}
