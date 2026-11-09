export type Mode = 'research' | 'chat';
export type View = Mode | 'models' | 'sources';
export type Locale = 'en' | 'nl' | 'ar' | 'fr' | 'de';

export interface Health {
  status: string;
  version: string;
  database: { ready: boolean; message: string };
  features: Record<string, unknown>;
}
export interface ModelRoute {
  id: string;
  title: string;
  model_id: string;
  provider: string;
  kind: 'htr' | 'vision' | 'ocr' | 'chat';
  enabled: boolean;
  configured: boolean;
  available: boolean;
  status: string;
  message: string;
  capabilities: string[];
}
export interface Persona { id: string; name: string; description: string }
export interface Dossier {
  id: string;
  title: string;
  question: string;
  notes: string;
  revision: number;
  created_at: string;
  updated_at: string;
}
export interface ImageAsset {
  id: string;
  dossier_id: string;
  filename: string;
  media_type: string;
  width: number;
  height: number;
  sha256: string;
  created_at: string;
}
export interface Region { x: number; y: number; width: number; height: number }
export interface Transcription {
  id: string;
  image_id: string;
  parent_id: string | null;
  text: string;
  kind: 'automatic' | 'user_corrected';
  engine: string;
  model_id: string;
  language: string | null;
  regions: Record<string, unknown>[];
  warnings: string[];
  created_at: string;
}
export interface Job {
  id: string;
  image_id: string;
  route_id: string;
  status: string;
  message: string;
  created_at: string;
  updated_at: string;
  transcription_id?: string | null;
}
export interface Participant {
  id: number;
  persona: string;
  perspective: string;
  routeId: string;
  pinned: boolean;
}

export type Provider = 'local' | 'mistral' | 'openrouter' | 'alibaba' | 'anthropic' | 'openai' | 'minimax';
export interface Connection {
  id: string; title: string; provider: Provider; model_id: string; base_url: string | null;
  enabled: boolean; configured: boolean; local: boolean; api_key_set: boolean;
}
export interface ChatSettings { local_only: boolean }
export type Collection = 'torah' | 'bible' | 'quran';
export interface CorpusEdition {
  id: string; title: string; language: string; revision: string;
  collection_memberships: Collection[]; passage_count: number;
}
export interface CorpusSource {
  id: string; title: string; url: string | null; source_type: string;
  provenance: unknown; use_limits: SourceUseLimits;
  editions: CorpusEdition[];
}
export interface CorpusStarter {
  id: string; title: string; language: string; collections: Collection[]; description?: string; source_type?: string;
}
export interface PassageSnapshot {
  passage_id: string; source_id: string; source_title: string; edition_title: string;
  reference: string; quote: string; url: string | null; collection_memberships: Collection[];
  language: string; revision: string; content_sha256: string | null;
  source_type?: string; edition_id?: string; quote_sha256?: string;
  use_limits?: SourceUseLimits; licence_url?: string | null;
}
interface SourceUseLimits { external_processing: boolean; rights_note?: string | null; licence_url?: string | null }
export interface ScriptureCitation extends PassageSnapshot { id: string; kind?: 'scripture' }
export interface WebCitation {
  id: string; kind: 'web'; title: string; source_url: string; quote: string;
  source_type: string; retrieved_at: string; content_sha256?: string | null;
  source_title?: string; edition_title?: string; publication?: string; language?: string;
  provider?: string; evidence_type?: string; authors?: string[]; issued_date?: string;
  license?: string; license_url?: string;
}
export type Citation = ScriptureCitation | WebCitation;
export type PassageAlignment = 'same_reference' | 'mapped_reference' | 'compare_only';
export interface ParallelPassage extends PassageSnapshot {
  alignment: PassageAlignment; alignment_note: string;
}
export interface ParallelPassages { anchor: PassageSnapshot; parallels: ParallelPassage[]; warnings: string[] }
export interface WebResearchGrounding {
  status: 'off' | 'used' | 'not_used' | 'no_results' | 'unavailable' | 'restricted';
  source_count?: number; retrieved_count?: number; queries?: string[]; partial?: boolean;
}
export interface ChatGrounding {
  mode: string; retrieved_count: number; collections: Collection[]; web_research?: WebResearchGrounding;
}
export interface ChatResponse {
  answer: string; citations: Citation[]; warnings: string[]; connection_id: string; model_id: string;
  grounding: ChatGrounding; turn_id?: string; session_id?: string;
}
export interface ChatTurn extends ChatResponse { question: string; id: string }
export interface ConversationSummary { id: string; title: string; dossier_id: string | null; created_at: string }
export interface ConversationRecord extends ConversationSummary {
  turns: { id: string; question: string; answer: string; citations: Citation[]; warnings: string[]; connection_id: string; model_id: string; created_at: string; grounding?: Partial<ChatGrounding> | null }[];
}
