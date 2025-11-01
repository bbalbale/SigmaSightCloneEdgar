"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";

export function AIInsightsButton() {
  const router = useRouter();

  const handleClick = () => {
    router.push("/sigmasight-ai");
  };

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-2 transition-all duration-200"
      style={{
        padding: '0.5rem 1rem',
        borderRadius: 'calc(var(--border-radius) * 0.5)',
        border: '1px solid var(--border-primary)',
        backgroundColor: 'var(--bg-secondary)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-body)'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'
      }}
    >
      <Sparkles className="h-4 w-4" />
      <span
        className="font-medium"
        style={{ fontSize: 'var(--text-sm)' }}
      >
        AI Insights
      </span>
    </button>
  );
}
