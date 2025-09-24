import React, { useEffect, useMemo, useState } from 'react';
import strategiesApi, { StrategyListItem } from '@/services/strategiesApi';
import TagEditor from './TagEditor';

interface Props {
  portfolioId: string;
}

export default function StrategyList({ portfolioId }: Props) {
  const [items, setItems] = useState<StrategyListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: string; tagIds: string[] } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const data = await strategiesApi.listByPortfolio({ portfolioId, includeTags: true, includePositions: false, limit: 500 });
        setItems(Array.isArray(data.strategies) ? data.strategies : []);
      } catch (e: any) {
        setError(e?.message || 'Failed to load strategies');
      } finally {
        setLoading(false);
      }
    })();
  }, [portfolioId]);

  const openEditor = (id: string, currentTagIds: string[]) => {
    setEditing({ id, tagIds: currentTagIds });
  };

  const onSaveTags = async (tagIds: string[]) => {
    if (!editing) return;
    await strategiesApi.replaceStrategyTags(editing.id, tagIds);
    // Update local state
    setItems(prev => prev.map(s => s.id === editing.id ? { ...s, tags: s.tags ? tagIds.map(id => {
      const found = s.tags!.find(t => t.id === id);
      return found || { id, name: 'Updated', color: '#4A90E2' };
    }) : [] } : s));
    setEditing(null);
  };

  if (loading) return <div>Loading strategies...</div>;
  if (error) return <div className="text-red-600">{error}</div>;

  return (
    <div className="space-y-3">
      {(Array.isArray(items) ? items : []).map(s => (
        <div key={s.id} className="border rounded p-3 bg-white flex items-center justify-between">
          <div>
            <div className="font-semibold">{s.name}</div>
            <div className="text-sm text-gray-600">{s.type} {s.is_synthetic ? '(multi-leg)' : ''} • {s.position_count ?? 0} legs</div>
            <div className="flex gap-2 mt-2 flex-wrap">
              {Array.isArray(s.tags) ? s.tags.map(tag => (
                <span key={tag.id} className="px-2 py-0.5 text-sm rounded" style={{ backgroundColor: tag.color, color: '#fff' }}>{tag.name}</span>
              )) : null}
              {(!Array.isArray(s.tags) || s.tags.length === 0) && <span className="text-xs text-gray-500">No tags</span>}
            </div>
          </div>
          <div>
            <button className="px-3 py-1 bg-gray-100 rounded" onClick={() => openEditor(s.id, Array.isArray(s.tags) ? s.tags.map(t => t.id) : [])}>Edit Tags</button>
          </div>
        </div>
      ))}

      {editing && (
        <TagEditor
          strategyId={editing.id}
          initialTagIds={editing.tagIds}
          onSave={onSaveTags}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
