export type Mode = 'research' | 'chat';
export type View = Mode | 'models';
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
