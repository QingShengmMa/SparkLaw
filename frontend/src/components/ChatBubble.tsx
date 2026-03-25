'use client';

import React, { cloneElement, isValidElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import HoverLawCard from '@/components/HoverLawCard';
import type { LawItem, StreamingMsg, TranscriptMsg } from '@/components/debate-types';

function getBubbleStyle(roleKey: string) {
  if (roleKey === 'plaintiff') {
    return {
      wrapper: 'flex justify-end',
      bubble: 'max-w-[76%] rounded-2xl rounded-tr-sm border border-red-200 bg-red-50 px-5 py-4 shadow-sm dark:border-red-900/50 dark:bg-red-950/20',
      nameBar: 'mb-2 flex items-center justify-end gap-2',
      nameText: 'text-sm font-semibold text-red-700 dark:text-red-400',
      icon: '👨‍⚖️',
    };
  }
  if (roleKey === 'defendant') {
    return {
      wrapper: 'flex justify-start',
      bubble: 'max-w-[76%] rounded-2xl rounded-tl-sm border border-blue-200 bg-blue-50 px-5 py-4 shadow-sm dark:border-blue-900/50 dark:bg-blue-950/20',
      nameBar: 'mb-2 flex items-center gap-2',
      nameText: 'text-sm font-semibold text-blue-700 dark:text-blue-400',
      icon: '👨‍💼',
    };
  }
  return {
    wrapper: 'flex justify-center',
    bubble: 'w-[88%] rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/20',
    nameBar: 'mb-2 flex items-center justify-center gap-2',
    nameText: 'text-sm font-semibold text-amber-700 dark:text-amber-400',
    icon: '⚖️',
  };
}

function renderTextWithCitations(
  text: string,
  onEvidenceClick: (evidenceId: string) => void,
  lawsById: Record<string, LawItem>
): React.ReactNode[] {
  const citationRegex = /(?:\[证据:(evidence_\d+)\])|(?:\[法条:(law_\d+)\])/g;
  const nodes: React.ReactNode[] = [];

  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = citationRegex.exec(text)) !== null) {
    const fullMatch = match[0];
    const evidenceId = match[1];
    const lawId = match[2];
    const matchIndex = match.index;

    if (matchIndex > lastIndex) {
      nodes.push(text.slice(lastIndex, matchIndex));
    }

    if (evidenceId) {
      const evidenceNumber = evidenceId.replace('evidence_', '');
      nodes.push(
        <button
          key={`evidence-${evidenceId}-${matchIndex}`}
          type="button"
          data-citation-link="true"
          onClick={() => onEvidenceClick(evidenceId)}
          className="text-xs text-blue-600 bg-blue-50 rounded px-1.5 py-0.5 mx-1 cursor-pointer hover:bg-blue-100 transition-colors"
        >
          [证据 {evidenceNumber}]
        </button>
      );
    }

    if (lawId) {
      nodes.push(
        <HoverLawCard
          key={`law-${lawId}-${matchIndex}`}
          lawId={lawId}
          law={lawsById[lawId]}
        />
      );
    }

    lastIndex = matchIndex + fullMatch.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function injectCitationsIntoMarkdownNode(
  node: React.ReactNode,
  onEvidenceClick: (evidenceId: string) => void,
  lawsById: Record<string, LawItem>
): React.ReactNode {
  if (typeof node === 'string') {
    return renderTextWithCitations(node, onEvidenceClick, lawsById);
  }

  if (Array.isArray(node)) {
    return node.map((child, idx) => (
      <React.Fragment key={`citation-fragment-${idx}`}>
        {injectCitationsIntoMarkdownNode(child, onEvidenceClick, lawsById)}
      </React.Fragment>
    ));
  }

  if (isValidElement(node)) {
    const currentProps = node.props as { children?: React.ReactNode };
    if (currentProps?.children === undefined) return node;
    return cloneElement(node, {
      ...currentProps,
      children: injectCitationsIntoMarkdownNode(currentProps.children, onEvidenceClick, lawsById),
    });
  }

  return node;
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:120ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60 [animation-delay:240ms]" />
    </span>
  );
}

export function PhaseTag({ phase }: { phase: string }) {
  if (!phase) return null;
  return (
    <div className="mb-3 flex justify-center">
      <span className="rounded-full border border-zinc-300 bg-zinc-100 px-3 py-0.5 text-xs font-medium text-zinc-500 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400">
        【{phase}】
      </span>
    </div>
  );
}

export default function ChatBubble({
  msg,
  streaming,
  onEvidenceClick,
  lawsById,
}: {
  msg: TranscriptMsg | StreamingMsg;
  streaming?: boolean;
  onEvidenceClick: (evidenceId: string) => void;
  lawsById: Record<string, LawItem>;
}) {
  const style = getBubbleStyle(msg.role_key);

  return (
    <div className={style.wrapper}>
      <div className={style.bubble}>
        <div className={style.nameBar}>
          <span className="text-lg">{style.icon}</span>
          <span className={style.nameText}>{msg.role}</span>
          {streaming && <TypingDots />}
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none text-[0.92rem] leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <div>{injectCitationsIntoMarkdownNode(children, onEvidenceClick, lawsById)}</div>,
              li: ({ children }) => <li>{injectCitationsIntoMarkdownNode(children, onEvidenceClick, lawsById)}</li>,
              blockquote: ({ children }) => <blockquote>{injectCitationsIntoMarkdownNode(children, onEvidenceClick, lawsById)}</blockquote>,
              strong: ({ children }) => <strong>{injectCitationsIntoMarkdownNode(children, onEvidenceClick, lawsById)}</strong>,
              em: ({ children }) => <em>{injectCitationsIntoMarkdownNode(children, onEvidenceClick, lawsById)}</em>,
            }}
          >
            {msg.content || '　'}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
