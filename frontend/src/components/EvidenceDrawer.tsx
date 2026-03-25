'use client';

import React, { useEffect, useState } from 'react';
import { ChevronRight, Plus } from 'lucide-react';
import type { EvidenceItem, HumanEvidenceInput, PartyEvidenceItem } from '@/components/debate-types';

type TabKey = 'plaintiff' | 'defendant';

export default function EvidenceDrawer({
  evidenceList,
  plaintiffEvidence,
  defendantEvidence,
  activeId,
  open,
  onToggle,
  onAddHumanEvidence,
  courtStarted = true,
}: {
  evidenceList: EvidenceItem[];
  plaintiffEvidence: PartyEvidenceItem[];
  defendantEvidence: PartyEvidenceItem[];
  activeId: string | null;
  open: boolean;
  onToggle: () => void;
  onAddHumanEvidence: (input: HumanEvidenceInput) => void;
  courtStarted?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<TabKey>('plaintiff');
  const [showForm, setShowForm] = useState(false);
  const [party, setParty] = useState<TabKey>('plaintiff');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');

  useEffect(() => {
    if (!activeId) return;
    const el = document.getElementById(activeId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeId]);

  const activePartyEvidence = activeTab === 'plaintiff' ? plaintiffEvidence : defendantEvidence;

  const handleSubmit = () => {
    if (!name.trim() || !desc.trim()) return;
    onAddHumanEvidence({
      party,
      name: name.trim(),
      desc: desc.trim(),
    });
    setShowForm(false);
    setName('');
    setDesc('');
    setActiveTab(party);
  };

  return (
    <div
      className={`fixed right-0 top-20 z-40 h-[80vh] w-[360px] transform border-l border-zinc-200 bg-white/96 shadow-2xl backdrop-blur transition-transform duration-300 dark:border-zinc-800 dark:bg-zinc-950/95 ${
        open ? 'translate-x-0' : 'translate-x-[320px]'
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="absolute -left-10 top-8 flex items-center gap-1 rounded-l-xl border border-r-0 border-blue-300 bg-blue-600 px-2 py-2 text-xs font-semibold text-white shadow-md dark:border-blue-700"
      >
        <ChevronRight size={14} className={`transition-transform ${open ? 'rotate-0' : 'rotate-180'}`} />
        <span className="[writing-mode:vertical-rl]">证据链</span>
      </button>

      <div className="h-full overflow-y-auto p-4">
        <h3 className="mb-3 text-sm font-semibold text-blue-700 dark:text-blue-300">庭审证据链</h3>

        {!courtStarted && (
          <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
            ⚠️ 证据链将在宣布开庭后显示。你可以在开庭前通过下方表单预先补充证据。
          </div>
        )}

        {courtStarted && (
          <div className="mb-3 rounded-lg border border-zinc-200 p-2 dark:border-zinc-800">
            <div className="mb-2 text-xs font-semibold text-zinc-500">事实证据（引用）</div>
            {!evidenceList.length ? (
              <p className="text-xs text-zinc-400">庭审开始后将展示证据链。</p>
            ) : (
              <div className="max-h-40 space-y-2 overflow-y-auto pr-1">
                {evidenceList.map((ev) => {
                  const isActive = activeId === ev.id;
                  return (
                    <div
                      key={ev.id}
                      id={ev.id}
                      data-evidence-card="true"
                      className={`rounded-lg border p-2 transition-all ${
                        isActive
                          ? 'border-blue-400 bg-blue-50/50 ring-2 ring-blue-500 dark:border-blue-600 dark:bg-blue-950/40'
                          : 'border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/60'
                      }`}
                    >
                      <div className="mb-0.5 text-[11px] font-semibold text-blue-600 dark:text-blue-400">{ev.id}</div>
                      <div className="mb-1 text-xs font-medium">{ev.title}</div>
                      <div className="line-clamp-2 text-[11px] leading-4 text-zinc-600 dark:text-zinc-300">{ev.content}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {courtStarted && (
          <div className="mb-3 flex gap-2 rounded-lg border border-zinc-200 p-1 dark:border-zinc-800">
            <button
              type="button"
              onClick={() => setActiveTab('plaintiff')}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === 'plaintiff'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                  : 'text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
              }`}
            >
              原告证据
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('defendant')}
              className={`flex-1 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                activeTab === 'defendant'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                  : 'text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
              }`}
            >
              被告证据
            </button>
          </div>
        )}

        {courtStarted && (
          <div className="space-y-2">
            {activePartyEvidence.length === 0 ? (
              <p className="text-xs text-zinc-400">当前暂无该方证据。</p>
            ) : (
              activePartyEvidence.map((ev) => (
                <div key={ev.id} className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/60">
                  <div className="mb-1 text-xs font-semibold text-zinc-500">{ev.id}</div>
                  <div className="mb-1 text-sm font-medium">{ev.name}</div>
                  <div className="text-xs leading-5 text-zinc-600 dark:text-zinc-300">{ev.desc}</div>
                </div>
              ))
            )}
          </div>
        )}

        <div className="mt-4 border-t border-zinc-200 pt-4 dark:border-zinc-800">
          {!courtStarted && (
            <p className="mb-2 text-xs text-zinc-500">开庭前可预先补充证据，庭审将强制使用这些材料：</p>
          )}
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 dark:border-emerald-700"
          >
            <Plus size={14} />
            {showForm ? '收起' : '➕ 补充新证据'}
          </button>

          {showForm && (
            <div className="mt-3 space-y-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/70">
              <select
                value={party}
                onChange={(e) => setParty(e.target.value as TabKey)}
                className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-900"
              >
                <option value="plaintiff">归属方：原告</option>
                <option value="defendant">归属方：被告</option>
              </select>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="证据名称（如：微信聊天记录截图）"
                className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-900"
              />
              <textarea
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="证据描述（如：显示被告于2024年3月承诺退还押金）"
                rows={4}
                className="w-full resize-none rounded border border-zinc-300 bg-white px-2 py-1.5 text-xs dark:border-zinc-700 dark:bg-zinc-900"
              />
              <button
                type="button"
                onClick={handleSubmit}
                className="w-full rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-700"
              >
                保存补充证据
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
