'use client';

import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PeriodType } from '@/services/equitySearchApi';

interface PeriodSelectorProps {
  value: PeriodType;
  onChange: (value: PeriodType) => void;
  disabled?: boolean;
}

const periodOptions: { value: PeriodType; label: string; description: string }[] = [
  { value: 'ttm', label: 'TTM', description: 'Trailing 12 months' },
  { value: 'last_year', label: 'Last Year', description: 'Most recent fiscal year' },
  { value: 'forward', label: 'Forward', description: 'Forward estimates' },
  { value: 'last_quarter', label: 'Last Quarter', description: 'Most recent quarter' },
];

export function PeriodSelector({ value, onChange, disabled }: PeriodSelectorProps) {
  return (
    <Select
      value={value}
      onValueChange={(val) => onChange(val as PeriodType)}
      disabled={disabled}
    >
      <SelectTrigger
        className="w-[140px]"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
        }}
      >
        <SelectValue placeholder="Select period" />
      </SelectTrigger>
      <SelectContent
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
        }}
      >
        {periodOptions.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            <div className="flex flex-col">
              <span>{option.label}</span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export default PeriodSelector;
