export type Mode = 'research' | 'chat';
export type View = Mode | 'models' | 'sources' | 'manuscripts';
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
  local?: boolean;
  kind: 'htr' | 'vision' | 'ocr' | 'chat';
  enabled: boolean;
  configured: boolean;
  available: boolean;
  status: string;
  message: string;
  capabilities: string[];
}
export interface Persona { id: string; name: string; description: string; roundtable_only?: boolean }
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
  provenance?: ManuscriptProvenance | null;
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
export type Provider = 'local' | 'mistral' | 'openrouter' | 'alibaba' | 'anthropic' | 'openai' | 'minimax';
export interface Connection {
  id: string; title: string; provider: Provider; model_id: string; base_url: string | null;
  enabled: boolean; configured: boolean; local: boolean; api_key_set: boolean;
}
export interface ChatSettings { local_only: boolean }
export type Collection = 'torah' | 'bible' | 'quran';
export interface ManuscriptUseLimits {
  preview: boolean;
  local_storage: boolean;
  local_ocr: boolean;
  external_processing: boolean;
}
export interface Manuscript {
  id: string; title: string; institution: string; shelfmark: string;
  language: string; collections: Collection[]; date?: string | null; description?: string | null;
  catalog_url: string; manifest_url: string; attribution: string; rights_url?: string | null;
  use_limits: ManuscriptUseLimits;
}
export interface ManuscriptFolio {
  id: string; label: string; index: number; canvas_id: string;
  width: number; height: number; source_url?: string | null; preview_url: string | null;
  use_limits: ManuscriptUseLimits;
}
export interface ManuscriptFolios { manuscript: Manuscript; items: ManuscriptFolio[]; manifest_sha256: string }
export interface ManuscriptProvenance {
  kind: 'manuscript'; manuscript_id: string; manuscript_title: string;
  institution: string; shelfmark: string | null; language: string | null; date?: string | null;
  catalog_url: string | null; manifest_url: string | null; manifest_sha256: string;
  folio_id: string; folio_label: string; canvas_id: string; image_url: string; source_url?: string | null;
  attribution: string | null; rights_url?: string | null; use_limits: ManuscriptUseLimits; retrieved_at: string;
}
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
  provenance?: { record_url?: string };
}
export interface ManuscriptReadingChoice {
  id: string; image_id: string; title: string; folio_label: string; created_at: string;
  kind: 'automatic' | 'user_corrected'; language: string | null; parent_id?: string | null; external_processing: boolean;
}
export interface ManuscriptCitation extends Omit<ManuscriptReadingChoice, 'id' | 'kind' | 'external_processing'> {
  id: string; kind: 'manuscript'; source_type: 'manuscript_transcription'; evidence_type: ManuscriptReadingChoice['kind'];
  edition_title?: string; reference: string; quote: string; quote_sha256: string; excerpt_start: number; excerpt_end: number;
  image_content_url?: string; image_width: number; image_height: number; image_sha256?: string;
  dossier_id: string; transcription_id: string; lineage_id?: string; engine: string; model_id: string;
  source_url?: string | null; provenance?: Partial<ManuscriptProvenance> | null; use_limits?: ManuscriptUseLimits;
  region?: (Region & { coordinate_system: 'original_image_pixels'; kind: 'text_region' | 'input_crop' }) | null;
}
export type Citation = ScriptureCitation | WebCitation | ManuscriptCitation;
export type PassageAlignment = 'same_reference' | 'mapped_reference' | 'compare_only';
export interface ParallelPassage extends PassageSnapshot {
  alignment: PassageAlignment; alignment_note: string;
}
export interface ParallelPassages { anchor: PassageSnapshot; parallels: ParallelPassage[]; warnings: string[] }
export interface WebResearchGrounding {
  status: 'off' | 'used' | 'not_used' | 'no_results' | 'unavailable' | 'restricted';
  source_count?: number; retrieved_count?: number; queries?: string[]; partial?: boolean;
}
export interface ManuscriptGrounding {
  status: 'used' | 'not_used' | 'no_results' | 'restricted';
  retrieved_count: number; source_count: number; blocked_count: number;
}
export interface ChatGrounding {
  mode: string; retrieved_count: number; collections: Collection[]; web_research?: WebResearchGrounding; manuscripts?: ManuscriptGrounding;
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

export interface RoundtableParticipant {
  id: string; name: string; perspective: string; persona_id: string; connection_id: string;
  model_id: string; provider: Provider; local: boolean; pinned: boolean;
  allocation?: 'automatic' | 'manual';
  allocation_basis?: 'orchestrator' | 'single_candidate' | 'configured_order' | 'moderator';
  status: 'ready' | 'speaking' | 'paused'; last_error?: { code: string; message: string } | null;
}
export interface RoundtableScope {
  collection_filter: Collection[]; source_ids?: string[] | null; web_research?: boolean;
  manuscript_dossier_id?: string | null; manuscript_revision_ids?: string[];
}
export interface RoundtableTurn extends Pick<ChatResponse, 'answer' | 'citations' | 'warnings' | 'connection_id' | 'model_id' | 'grounding'> {
  id: string; participant_id: string; moderator_note?: string | null; synthesis?: boolean; created_at: string;
  request_revision?: number;
}
export interface RoundtableRoom {
  id: string; topic: string; language: string; participants: RoundtableParticipant[]; turns: RoundtableTurn[];
  scope: RoundtableScope; status: 'awaiting_moderator' | 'running' | 'stopped'; revision: number;
  evidence: Citation[]; evidence_version: number | null; evidence_sha256?: string | null;
  active_participant_id?: string | null; grounding?: ChatGrounding | null;
}
