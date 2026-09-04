export type UserRole = 'ADMIN' | 'OPERATOR';

export interface UserAccount {
  id: number;
  username: string;
  role: UserRole;
  password_change_required: boolean;
}

export interface AuthStatus {
  setup_required: boolean;
  authenticated: boolean;
  username?: string | null;
  role?: UserRole | null;

  password_change_required: boolean;
}

export interface UserResponse {
  username: string;
  role: UserRole;
  password_change_required: boolean;
}

export interface Library {
  id: number;
  media_server_id: number;
  name: string;
  library_type: string;
  agent?: string;
  scanner?: string;
  language?: string;
  created_at?: string;
  updated_at?: string;
  media_count?: number;
  enabled?: boolean;
}

export type ItemStatusFilter = 'unprocessed' | 'errors' | 'locked';

export const NO_PROVIDER = 'none';

export interface PosterCandidate {
  url: string;
  provider: string;

  rank: number;

  rank_score: number;
}

export type ItemProviderFilter = string | undefined;

export type ItemFilter = 'all' | ItemStatusFilter;

export interface SortState {
  by: string;
  dir: 'asc' | 'desc';
}

export type ViewMode = 'grid' | 'list';

export type TaskKind = 'sync' | 'generate' | 'reset' | 'other';

export interface TaskProgressState {
  current: number;
  total: number;
  message?: string;
}

export interface LibraryItem {
  id: number;
  library_id: number;

  external_id?: string;
  title: string;
  type: string;
  year?: number;

  release_date?: string;
  added_at?: string;
  updated_at?: string;

  last_seen_at?: string;

  poster_uploaded_at?: string;
  imdb_id?: string;
  tmdb_id?: string;
  tvdb_id?: string;
  processed: boolean;

  locked: boolean;

  poster_provider?: string | null;

  error_message?: string | null;

  error_cause?: string | null;

  has_poster?: boolean;

  poster_version?: string | null;

  source_poster_version?: string | null;

  media_resolution?: string | null;
  media_width?: number | null;
  media_height?: number | null;
  video_codec?: string | null;
  audio_codec?: string | null;
  audio_channels?: number | null;
  media_container?: string | null;
  media_bitrate?: number | null;
  media_size_bytes?: number | null;

  deleted_at?: string;
}

export interface ItemSeason {
  id: number;
  show_id: number;
  library_id: number;
  season_number: number;
  title: string;
  added_at?: string;
  updated_at?: string;
  imdb_id?: string;
  tmdb_id?: string;
  tvdb_id?: string;
  poster_url?: string;

  poster_provider?: string | null;
  processed: boolean;
  has_poster?: boolean;

  poster_version?: string | null;

  source_poster_version?: string | null;
}

export interface LibraryItemWithSeasons extends LibraryItem {
  seasons: ItemSeason[];
}

export interface ItemEpisode {
  id: number;
  season_id: number;
  show_id: number;
  library_id: number;
  season_number: number;
  episode_number: number;
  title: string;
  air_date?: string | null;
  added_at?: string | null;
  updated_at?: string | null;
  imdb_id?: string | null;
  tmdb_id?: string | null;
  tvdb_id?: string | null;
  media_resolution?: string | null;
  media_width?: number | null;
  media_height?: number | null;
  video_codec?: string | null;
  audio_codec?: string | null;
  audio_channels?: number | null;
  media_container?: string | null;
  media_bitrate?: number | null;
  media_size_bytes?: number | null;
}

export interface PaginatedLibraryItems {
  items: LibraryItem[];

  total: number;

  total_pages: number;

  page: number;
  page_size: number;
}

export interface AlphaIndexEntry {
  letter: string;

  page: number;
}

export interface LibraryItemCounts extends ItemStatusCounts {

  providers: Record<string, number>;
}

export interface ItemStatusCounts {
  total: number;
  unprocessed: number;
  errors: number;
  locked: number;
}

export interface ItemStats {
  total: number;
  processed: number;
  unprocessed: number;
  errors: number;
  locked: number;
  uploaded: number;
}

export interface DashboardLibrary {
  library_id: number;
  library_name: string;
  library_type: string;
  enabled: boolean;
  media_server_id: number;
  media_server_name: string;
  media_server_type: string;
  stats: ItemStats;
}

export interface ProviderShare {
  provider: string;
  count: number;
}

export interface DashboardTask {
  task_id: string;
  task_name?: string | null;
  status: string;
  created_at?: string | null;
  completed_at?: string | null;
  message?: string | null;
  error?: string | null;
}

export interface DashboardSummary {
  totals: ItemStats;
  library_count: number;
  media_server_count: number;
  libraries: DashboardLibrary[];
  providers: ProviderShare[];

  recent_tasks: DashboardTask[];
}

export interface Collection {

  tmdb_collection_id?: number | null;
  id: number;
  library_id: number;
  external_id?: string;
  title: string;
  sort_title?: string | null;

  child_count?: number | null;

  member_count: number;
  added_at?: string | null;
  updated_at?: string | null;
  poster_uploaded_at?: string | null;
  poster_provider?: string | null;
  processed: boolean;
  locked: boolean;
  error_message?: string | null;
  has_poster?: boolean;
  poster_version?: string | null;
  source_poster_version?: string | null;
}

export interface CollectionWithMembers extends Collection {
  members: LibraryItem[];
}

export interface PaginatedCollections {
  collections: Collection[];
  total: number;
  page: number;
  page_size: number;
}

export interface SyncTaskResponse {
  status: string;
  task_id: string;
  message?: string;
}

export interface ServiceConfiguration {
  name: string;
  type: string;
  url: string;
  enabled: boolean;

  configured: boolean;

  token_hint: string | null;
}

export type MediaServerType = 'PLEX' | 'JELLYFIN';

export interface MediaServerLibrary {
  id: string;
  name: string;
  type: string;
  item_count: number;
  agent?: string;
  language: string;
  uuid?: string;
  created_at?: string;
  updated_at?: string;
}

export interface MediaServerTestResult {
  name: string;
  libraries: MediaServerLibrary[];
}

export interface MediaServerCreate {
  name: string;
  type: MediaServerType;
  url: string;
  token: string;
  enabled?: boolean;
  libraries: MediaServerLibrary[];
}

export interface MediaServerResponse {
  id: number;
  name: string;
  type: MediaServerType;
  url: string;
  enabled: boolean;

  language_order: string[];

  fallback_to_server_poster: boolean;

  skip_style_when_not_textless: boolean;
  webhook_enabled: boolean;
  webhook_token: string | null;
  last_sync: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppSettings {
  new_library_enabled: boolean;
  new_library_upload_enabled: boolean;
  new_library_provider_order: string[];
  log_level: string;
  trash_retention_days: number;
}

export type NewLibraryDefaults = Partial<Pick<AppSettings,
  'new_library_enabled' | 'new_library_upload_enabled' | 'new_library_provider_order'>>;

export interface AppSettingsInfo {
  version: string;
  encryption_key_secure: boolean;
  database: string;
}

export type AutoPickupAction = 'sync' | 'generate' | 'upload';

export interface LibrarySettings {
  library_id: number;
  enabled: boolean;
  upload_enabled: boolean;
  provider_order: string[];

  overlay_options?: Record<string, unknown> | null;
  text_options?: Record<string, unknown> | null;

  style_profile_id?: number | null;
  track_episodes: boolean;
  track_collections: boolean;
  auto_sync_enabled: boolean;
  auto_sync_interval_minutes: number;
  auto_pickup_action: AutoPickupAction;
  last_auto_sync_at: string | null;

  last_full_sync_at: string | null;
}

export type OverlayType = 'poster' | 'background';
export type Gravity = 'north' | 'center' | 'south';

export interface OverlayOptions {
  overlay_type: OverlayType;
  border_enabled: boolean;
  border_px: number;
  border_color: string;
  corner_radius: number;
  matte_height_ratio: number;
  fade_height_ratio: number;
  gradient_color: string;
  vignette_strength: number;
  vignette_color: string;
  inner_glow_strength: number;
  inner_glow_color: string;
  grain_amount: number;
  grain_size: number;
  blur_amount: number;
  show_text_area: boolean;
  text_box_w: number;
  text_box_h: number;
  text_box_offset: number;
}

export interface TextOptions {
  enabled: boolean;
  font_name: string;
  font_color: string;
  all_caps: boolean;
  min_font_ratio: number;
  max_font_ratio: number;
  max_width_ratio: number;
  max_height_ratio: number;
  text_offset_ratio: number;
  border_padding_ratio: number;
  gravity: Gravity;
  stroke_enabled: boolean;
  stroke_color: string;
  stroke_width_ratio: number;
  line_spacing_ratio: number;
  break_on_symbols: boolean;
  break_symbols: string[];
  auto_wrap: boolean;
  auto_wrap_threshold_ratio: number;
}

export interface GenerationOptions {
  jpeg_quality: number;
}

export interface LibraryStyleStaleness {
  stale: number;
  total: number;
}

export interface StyleProfile {
  id: number;
  name: string;
  overlay_options?: Record<string, unknown> | null;
  text_options?: Record<string, unknown> | null;

  library_count: number;
}

export interface PosterConfig {
  overlay_options: OverlayOptions;
  text_options: TextOptions;
  generation_options: GenerationOptions;
}

export interface SearchHit extends LibraryItem {
  library_name: string;
  library_type: string;
  media_server_id: number;
  media_server_name: string;
  media_server_type: MediaServerType;
}

export interface SearchResults {
  items: SearchHit[];

  total: number;

  total_pages: number;
  page: number;
  page_size: number;
}

export interface ProviderDay {
  day: string;
  provider: string;
  count: number;
}

export interface ProviderHistory {
  days: number;
  series: ProviderDay[];
  totals: ProviderShare[];
}

export type NotificationType = 'discord' | 'gotify' | 'apprise' | 'webhook';

export interface NotificationTarget {
  id: number;
  name: string;
  type: NotificationType;
  url_hint: string;
  enabled: boolean;
  on_task_completed: boolean;
  on_task_failed: boolean;
  on_items_errored: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}
