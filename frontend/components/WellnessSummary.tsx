'use client';

type WellnessEntry = {
  mood?: string;
  energy?: string;
  goals?: string[];
  summary?: string;
};

export default function WellnessSummary({ entry }: { entry?: WellnessEntry | null }) {
  if (!entry) {
    return (
      <div className="px-6 py-4 bg-[#1b1f25] text-gray-300 rounded-xl shadow-lg backdrop-blur-xl">
        <p>No wellness check-in yet.</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-5 bg-gradient-to-br from-[#1c222b] to-[#14171c] text-white rounded-2xl shadow-xl backdrop-blur-xl border border-white/10 w-[340px]">
      <p className="font-semibold text-lg">🌿 Today’s Wellness Summary</p>

      <div className="mt-3 space-y-1">
        <p><span className="text-gray-400">Mood:</span> {entry.mood}</p>
        <p><span className="text-gray-400">Energy:</span> {entry.energy}</p>
        <p><span className="text-gray-400">Goals:</span> {entry.goals?.join(', ')}</p>
      </div>

      <p className="mt-3 text-sm text-gray-400 italic">
        {entry.summary}
      </p>
    </div>
  );
}
