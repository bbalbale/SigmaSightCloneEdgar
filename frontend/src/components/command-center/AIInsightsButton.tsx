"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "@/contexts/ThemeContext";
import { Sparkles } from "lucide-react";

export function AIInsightsButton() {
  const { theme } = useTheme();
  const router = useRouter();

  const handleClick = () => {
    router.push("/sigmasight-ai");
  };

  return (
    <button
      onClick={handleClick}
      className={`flex items-center gap-2 px-4 py-2 rounded transition-all duration-200 ${
        theme === "dark"
          ? "bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 border border-slate-700 hover:border-slate-600"
          : "bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-300 hover:border-slate-400"
      }`}
    >
      <Sparkles className="h-4 w-4" />
      <span className="text-sm font-medium">AI Insights</span>
    </button>
  );
}
