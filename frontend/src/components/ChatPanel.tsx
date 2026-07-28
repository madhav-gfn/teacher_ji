import { useRef, useState } from "react";
import { apiClient } from "../api/client";
import { useSessionStore } from "../store/sessionStore";
import { Markdown } from "./Markdown";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: "streaming" | "done" | "error";
}

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// Phase 3C: a chat panel alongside the existing TeachingCard (not a
// replacement for it - master_plan.md decided against a rewrite). A chat
// message is just another turn through the same Supervisor/Learning Agent
// loop every other teaching action already uses (/session/question/stream is
// the SSE twin of the existing /session/question) - this component only adds
// a conversational way to see and send those turns.
export function ChatPanel() {
  const { sessionId, currentTopic, setSession } = useSessionStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  };

  const send = async () => {
    const question = input.trim();
    if (!question || !sessionId || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);

    const userMessage: ChatMessage = { id: newId(), role: "user", content: question, status: "done" };
    const assistantId = newId();
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: "assistant", content: "", status: "streaming" },
    ]);
    scrollToBottom();

    try {
      for await (const event of apiClient.streamSessionQuestion({ session_id: sessionId, question })) {
        if (event.event === "token") {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId ? { ...message, content: message.content + event.data } : message,
            ),
          );
          scrollToBottom();
        } else if (event.event === "done") {
          const response = event.data;
          const answer = [response.teaching_output.headline, response.teaching_output.explanation]
            .filter(Boolean)
            .join("\n\n");

          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId
                ? { ...message, content: answer || message.content, status: "done" }
                : message,
            ),
          );

          setSession({
            currentTopic: response.topic,
            topicsRemaining: response.next_topics,
            teachingOutput: response.teaching_output,
            feedbackOutput: null,
          });
        } else if (event.event === "error") {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId
                ? { ...message, content: event.data.detail, status: "error" }
                : message,
            ),
          );
        }
      }
    } catch (error) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: error instanceof Error ? error.message : "Something went wrong.",
                status: "error",
              }
            : message,
        ),
      );
    } finally {
      setIsSending(false);
      scrollToBottom();
    }
  };

  if (!sessionId || !currentTopic) {
    return null;
  }

  return (
    <div className="flex h-full flex-col rounded-2xl border border-gray-100 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-5 py-4">
        <p className="text-sm font-semibold text-gray-900">Chat about {currentTopic}</p>
        <p className="text-xs text-gray-500">
          Ask a follow-up any time - it goes through the same teaching agent, streamed live.
        </p>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {messages.length === 0 ? (
          <p className="text-sm text-gray-400">No messages yet. Ask something about this topic.</p>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                  message.role === "user"
                    ? "bg-purple-600 text-white"
                    : message.status === "error"
                      ? "border border-red-200 bg-red-50 text-red-700"
                      : "border border-gray-100 bg-gray-50 text-gray-800"
                }`}
              >
                {message.role === "assistant" ? (
                  <Markdown>{message.content || (message.status === "streaming" ? "..." : "")}</Markdown>
                ) : (
                  <p className="leading-6">{message.content}</p>
                )}
                {message.status === "streaming" ? (
                  <span className="mt-1 inline-block h-3 w-1.5 animate-pulse bg-gray-400 align-text-bottom" />
                ) : null}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="border-t border-gray-100 p-4">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send();
              }
            }}
            placeholder="Ask a question about this topic..."
            className="min-h-11 max-h-32 flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-gray-700 outline-none transition focus:border-purple-300 focus:bg-white focus:ring-2 focus:ring-purple-100"
          />
          <button
            type="button"
            onClick={() => void send()}
            disabled={!input.trim() || isSending}
            className="rounded-xl bg-purple-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
          >
            {isSending ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
