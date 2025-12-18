'use client';

/**
 * BriefingSettings - Morning Briefing Customization Component
 *
 * Allows users to configure their morning briefing preferences including:
 * - Include news toggle
 * - Include market overview toggle
 * - Verbosity level (brief/standard/detailed)
 * - Focus areas
 *
 * Phase 2: Enhanced Morning Briefing (December 2025)
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Newspaper, TrendingUp, FileText, Focus, Save, RefreshCw, Check, X } from 'lucide-react';

interface BriefingPreferences {
  include_news: boolean;
  include_market_overview: boolean;
  verbosity: 'brief' | 'standard' | 'detailed';
  focus_areas: string[];
}

const DEFAULT_PREFERENCES: BriefingPreferences = {
  include_news: true,
  include_market_overview: true,
  verbosity: 'standard',
  focus_areas: [],
};

const FOCUS_AREA_OPTIONS = [
  { id: 'tech', label: 'Technology', description: 'Focus on tech sector holdings' },
  { id: 'dividends', label: 'Dividends', description: 'Highlight dividend-paying stocks' },
  { id: 'risk', label: 'Risk', description: 'Emphasize risk metrics and concerns' },
  { id: 'options', label: 'Options', description: 'Focus on options positions' },
  { id: 'movers', label: 'Top Movers', description: 'Highlight biggest gainers/losers' },
  { id: 'news', label: 'Market News', description: 'More emphasis on news analysis' },
];

const STORAGE_KEY = 'sigmasight_briefing_preferences';

export function BriefingSettings() {
  const [preferences, setPreferences] = useState<BriefingPreferences>(DEFAULT_PREFERENCES);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Load preferences from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setPreferences({ ...DEFAULT_PREFERENCES, ...parsed });
      } catch (e) {
        console.error('Failed to parse briefing preferences:', e);
      }
    }
  }, []);

  // Save preferences to localStorage
  const handleSave = () => {
    setSaving(true);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error('Failed to save briefing preferences:', e);
    } finally {
      setSaving(false);
    }
  };

  // Reset to defaults
  const handleReset = () => {
    setPreferences(DEFAULT_PREFERENCES);
    localStorage.removeItem(STORAGE_KEY);
  };

  // Toggle focus area
  const toggleFocusArea = (areaId: string) => {
    setPreferences(prev => {
      const newAreas = prev.focus_areas.includes(areaId)
        ? prev.focus_areas.filter(a => a !== areaId)
        : [...prev.focus_areas, areaId];
      return { ...prev, focus_areas: newAreas };
    });
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-500" />
          <CardTitle className="text-lg">Morning Briefing Settings</CardTitle>
        </div>
        <CardDescription>
          Customize how your daily morning briefing is generated.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Content Toggles */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium">Content Options</h3>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Newspaper className="h-4 w-4 text-muted-foreground" />
              <Label>Include News</Label>
            </div>
            <Button
              variant={preferences.include_news ? 'default' : 'outline'}
              size="sm"
              onClick={() =>
                setPreferences(prev => ({ ...prev, include_news: !prev.include_news }))
              }
            >
              {preferences.include_news ? (
                <><Check className="h-4 w-4 mr-1" /> On</>
              ) : (
                <><X className="h-4 w-4 mr-1" /> Off</>
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground ml-6">
            Include market news and headlines affecting your holdings
          </p>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <Label>Include Market Overview</Label>
            </div>
            <Button
              variant={preferences.include_market_overview ? 'default' : 'outline'}
              size="sm"
              onClick={() =>
                setPreferences(prev => ({ ...prev, include_market_overview: !prev.include_market_overview }))
              }
            >
              {preferences.include_market_overview ? (
                <><Check className="h-4 w-4 mr-1" /> On</>
              ) : (
                <><X className="h-4 w-4 mr-1" /> Off</>
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground ml-6">
            Include S&P 500, NASDAQ, VIX, and sector performance
          </p>
        </div>

        {/* Verbosity Level */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium">Verbosity Level</h3>
          <div className="flex gap-2">
            {(['brief', 'standard', 'detailed'] as const).map((level) => (
              <Button
                key={level}
                variant={preferences.verbosity === level ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPreferences(prev => ({ ...prev, verbosity: level }))}
                className="capitalize"
              >
                {level}
              </Button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            {preferences.verbosity === 'brief' && 'Quick highlights only - just the essentials'}
            {preferences.verbosity === 'standard' && 'Balanced analysis with key details'}
            {preferences.verbosity === 'detailed' && 'Comprehensive analysis with full context'}
          </p>
        </div>

        {/* Focus Areas */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Focus className="h-4 w-4" />
            <h3 className="text-sm font-medium">Focus Areas</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Select areas to emphasize in your briefings (optional)
          </p>
          <div className="grid grid-cols-2 gap-2">
            {FOCUS_AREA_OPTIONS.map((area) => (
              <Button
                key={area.id}
                variant={preferences.focus_areas.includes(area.id) ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => toggleFocusArea(area.id)}
                className="justify-start"
              >
                {area.label}
              </Button>
            ))}
          </div>
          {preferences.focus_areas.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Selected: {preferences.focus_areas.map(a => {
                const opt = FOCUS_AREA_OPTIONS.find(o => o.id === a);
                return opt?.label;
              }).join(', ')}
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-4 border-t">
          <Button
            onClick={handleSave}
            disabled={saving}
            className="flex-1"
          >
            {saving ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            {saved ? 'Saved!' : 'Save Preferences'}
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
          >
            Reset
          </Button>
        </div>

        {/* Usage Note */}
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">
            These preferences will be applied when you generate a morning briefing
            from the AI Chat page using the &quot;Morning Briefing&quot; insight type.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export default BriefingSettings;

// Export a function to get current preferences (for use by other components)
export function getBriefingPreferences(): BriefingPreferences | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}
