import React, { useEffect, useState } from 'react';
import tagsApi from '@/services/tagsApi';
import type { TagItem } from '@/types/strategies';

interface TagEditorProps {
  strategyId: string;
  initialTagIds: string[];
  onSave: (tagIds: string[]) => Promise<void>;
  onClose: () => void;
}

export default function TagEditor({ strategyId, initialTagIds, onSave, onClose }: TagEditorProps) {
  const [available, setAvailable] = useState<TagItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(initialTagIds));
  const [newTagName, setNewTagName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      const tags = await tagsApi.list(false);
      setAvailable(tags);
    })();
  }, []);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const addNewTag = async () => {
    const name = newTagName.trim();
    if (!name) return;
    const created = await tagsApi.create(name);
    setAvailable(prev => [...prev, created]);
    setSelected(prev => new Set(prev).add(created.id));
    setNewTagName('');
  };

  const handleSave = async () => {
    setSaving(true);
    await onSave(Array.from(selected));
    setSaving(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-3">Edit Strategy Tags</h3>
        <div className="max-h-64 overflow-auto border rounded p-2 mb-3">
          {available.map(t => (
            <label key={t.id} className="flex items-center gap-2 py-1">
              <input type="checkbox" checked={selected.has(t.id)} onChange={() => toggle(t.id)} />
              <span className="inline-flex items-center gap-2">
                <span className="w-3 h-3 inline-block rounded" style={{ backgroundColor: t.color }}></span>
                {t.name}
              </span>
            </label>
          ))}
          {available.length === 0 && <div className="text-sm text-tertiary">No tags yet.</div>}
        </div>
        <div className="flex gap-2 mb-4">
          <input value={newTagName} onChange={e => setNewTagName(e.target.value)} placeholder="New tag name" className="border rounded px-2 py-1 flex-1" />
          <button className="px-3 py-1 bg-gray-200 rounded" onClick={addNewTag}>Add</button>
        </div>
        <div className="flex justify-end gap-2">
          <button className="px-4 py-2 bg-gray-100 rounded" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        </div>
      </div>
    </div>
  );
}

