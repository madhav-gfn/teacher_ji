import type { Subject } from "../api/client";
import { subjectMeta } from "../data/curriculum";

interface SidebarProps {
  subject: Subject;
  chapter: string;
  currentTopic: string;
  topicsCompleted: string[];
  topicsRemaining: string[];
}

export function Sidebar({
  subject,
  chapter,
  currentTopic,
  topicsCompleted,
  topicsRemaining,
}: SidebarProps) {
  const meta = subjectMeta[subject];
  const orderedTopics = [...topicsCompleted, currentTopic, ...topicsRemaining].filter(
    (topic, index, items) => items.indexOf(topic) === index,
  );
  const estimatedMinutes = Math.max(topicsRemaining.length * 6, 4);

  return (
    <aside className="flex h-screen w-[280px] shrink-0 flex-col border-r border-gray-200 bg-white px-5 py-6">
      <div className={`rounded-2xl border px-4 py-4 ${meta.accent}`}>
        <p className="text-xs font-semibold uppercase tracking-[0.24em]">Structured Teaching Board</p>
        <h1 className="mt-3 text-xl font-bold">{meta.label}</h1>
        <p className="mt-2 text-sm leading-6">{chapter}</p>
      </div>

      <div className="mt-6 flex-1 overflow-hidden">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Chapter flow</h2>
          <span className="text-xs text-gray-500">{orderedTopics.length} topics</span>
        </div>
        <div className="space-y-2 overflow-y-auto pr-1">
          {orderedTopics.map((topic) => {
            const isCompleted = topicsCompleted.includes(topic);
            const isCurrent = topic === currentTopic;

            const classes = isCompleted
              ? "border-green-200 bg-green-500 text-white"
              : isCurrent
                ? "border-purple-200 bg-purple-600 text-white"
                : "border-gray-200 bg-white text-gray-600";

            return (
              <div
                key={topic}
                className={`flex items-center gap-3 rounded-full border px-4 py-3 text-sm font-medium shadow-sm ${classes}`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    isCompleted
                      ? "bg-white/90"
                      : isCurrent
                        ? "animate-pulse bg-white"
                        : "bg-gray-300"
                  }`}
                />
                <span className="line-clamp-2">{topic}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-gray-100 bg-gray-50 p-4">
        <h3 className="text-sm font-semibold text-gray-900">Student progress</h3>
        <div className="mt-4 space-y-3">
          <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Topics completed</p>
            <p className="mt-2 text-2xl font-bold text-gray-900">{topicsCompleted.length}</p>
          </div>
          <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Estimated time left</p>
            <p className="mt-2 text-2xl font-bold text-gray-900">{estimatedMinutes} min</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
