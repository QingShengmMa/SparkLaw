export interface TranscriptMsg {
  id: string;
  role: string;
  role_key: string;
  phase: string;
  content: string;
}

export interface StreamingMsg {
  id: string;
  role: string;
  role_key: string;
  phase: string;
  content: string;
  streaming: true;
}

export interface EvidenceItem {
  id: string;
  title: string;
  content: string;
  source?: string;
}

export interface LawItem {
  id: string;
  title: string;
  content: string;
  source?: string;
}

export interface PartyEvidenceItem {
  id: string;
  name: string;
  desc: string;
}

export interface HumanEvidenceInput {
  party: 'plaintiff' | 'defendant';
  name: string;
  desc: string;
}

export interface VerdictResult {
  plaintiff_win_rate: number;
  defendant_win_rate: number;
  verdict_text: string;
}

export interface CourtResult {
  transcript: TranscriptMsg[];
  verdict: string;
  evidence_list: EvidenceItem[];
  law_list: LawItem[];
  laws: LawItem[];
  plaintiff_evidence: PartyEvidenceItem[];
  defendant_evidence: PartyEvidenceItem[];
  legal_basis: string[];
  plaintiff_win_rate: number;
  defendant_win_rate: number;
  verdict_result?: VerdictResult;
}

export type StrategyKey = 'aggressive' | 'conservative' | 'mediator';
