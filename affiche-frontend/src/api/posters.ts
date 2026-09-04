import { api, postForm } from './client';
import type { OverlayOptions, PosterCandidate, TextOptions } from '../types';

export const postersApi = {
  getPosters: (params: {
    tmdb_id?: number;
    tvdb_id?: number;
    media_type: string;
    provider?: string;
    language?: string;
  }): Promise<PosterCandidate[]> => {
    const searchParams = new URLSearchParams();
    if (params.tmdb_id) searchParams.set('tmdb_id', params.tmdb_id.toString());
    if (params.tvdb_id) searchParams.set('tvdb_id', params.tvdb_id.toString());
    searchParams.set('media_type', params.media_type);
    if (params.provider) searchParams.set('provider', params.provider);
    if (params.language) searchParams.set('language', params.language);
    return api.get(`/service/posters?${searchParams.toString()}`);
  },

  searchPosters: (params: {
    name: string;
    year?: number;
    media_type: string;
    provider?: string;
    language?: string;
  }): Promise<PosterCandidate[]> => {
    const searchParams = new URLSearchParams();
    searchParams.set('name', params.name);
    if (params.year) searchParams.set('year', params.year.toString());
    searchParams.set('media_type', params.media_type);
    if (params.provider) searchParams.set('provider', params.provider);
    if (params.language) searchParams.set('language', params.language);
    return api.get(`/service/posters/search?${searchParams.toString()}`);
  },

  getSeasonPosters: (params: {
    season_number: number;
    tmdb_id?: number;
    tvdb_id?: number;
    provider?: string;
    language?: string;
  }): Promise<PosterCandidate[]> => {
    const searchParams = new URLSearchParams();
    searchParams.set('season_number', params.season_number.toString());
    if (params.tmdb_id) searchParams.set('tmdb_id', params.tmdb_id.toString());
    if (params.tvdb_id) searchParams.set('tvdb_id', params.tvdb_id.toString());
    if (params.provider) searchParams.set('provider', params.provider);
    if (params.language) searchParams.set('language', params.language);
    return api.get(`/service/posters/season?${searchParams.toString()}`);
  },

  uploadCustomPoster: (params: { file?: File; url?: string }): Promise<{ token: string }> => {
    const form = new FormData();
    if (params.file) form.append('file', params.file);
    if (params.url) form.append('url', params.url);
    return postForm('/service/custom-poster', form);
  },

  getTranslatedTitle: (params: {
    media_type: string;
    language: string;
    tmdb_id?: number;
    tvdb_id?: number;
    season_number?: number;
  }): Promise<{ title: string | null }> => {
    const searchParams = new URLSearchParams();
    searchParams.set('media_type', params.media_type);
    searchParams.set('language', params.language);
    if (params.tmdb_id) searchParams.set('tmdb_id', params.tmdb_id.toString());
    if (params.tvdb_id) searchParams.set('tvdb_id', params.tvdb_id.toString());
    if (params.season_number !== undefined)
      searchParams.set('season_number', params.season_number.toString());
    return api.get(`/service/title?${searchParams.toString()}`);
  },

  applyPoster: (params: {
    mediaServerId: number;
    libraryId: number;
    itemId: number;
    posterUrl: string;
    seasonNumber?: number;
    jpegQuality?: number;
    title?: string;
    overlayOptions?: OverlayOptions;
    textOptions?: TextOptions;
    upload?: boolean;
  }): Promise<void> => {
    const { mediaServerId, libraryId, itemId, posterUrl, seasonNumber, jpegQuality, title, overlayOptions, textOptions, upload } = params;
    const body = {
      poster_url: posterUrl,
      jpeg_quality: jpegQuality,
      title,
      overlay_options: overlayOptions,
      text_options: textOptions,
      upload,
    };
    if (seasonNumber !== undefined) {
      return api.post(
        `/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/seasons/${seasonNumber}/posters`,
        body
      );
    }
    return api.post(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/items/${itemId}/posters`,
      body
    );
  },

  getCollectionPosters: (params: {
    collectionId: number;
    provider?: string;
    language?: string;
  }): Promise<PosterCandidate[]> => {
    const query = new URLSearchParams({ collection_id: String(params.collectionId) });
    if (params.provider) query.set('provider', params.provider);
    if (params.language) query.set('language', params.language);
    return api.get<PosterCandidate[]>(`/service/collection-posters?${query}`);
  },

  applyCollectionPoster: (params: {
    mediaServerId: number;
    libraryId: number;
    collectionId: number;
    posterUrl: string;
    jpegQuality?: number;
    title?: string;
    overlayOptions?: OverlayOptions;
    textOptions?: TextOptions;
    upload?: boolean;
  }): Promise<void> => {
    const { mediaServerId, libraryId, collectionId, posterUrl, jpegQuality, title,
            overlayOptions, textOptions, upload } = params;
    return api.post(
      `/media-servers/${mediaServerId}/libraries/${libraryId}/collections/${collectionId}/posters`,
      {
        poster_url: posterUrl,
        jpeg_quality: jpegQuality,
        title,
        overlay_options: overlayOptions,
        text_options: textOptions,
        upload,
      }
    );
  },
};
