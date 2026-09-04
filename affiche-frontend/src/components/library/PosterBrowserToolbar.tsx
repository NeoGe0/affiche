import { Loader2, Search, Upload } from 'lucide-react';

import { POSTER_LANGUAGES } from '../../constants/languages';
import { providerLabel } from '../../constants/providers';
import { POSTER_SORTS, type PosterSort } from './posterSort';
import styles from './PosterBrowserToolbar.module.css';

interface PosterBrowserToolbarProps {

  search: {
    title: string;
    year: string;
    onTitleChange: (value: string) => void;
    onYearChange: (value: string) => void;
    onSubmit: () => void;
    isSearching: boolean;
  };

  filters: {
    language: string;
    onLanguageChange: (value: string) => void;
    provider: string;
    onProviderChange: (value: string) => void;

    availableProviders: string[];

    sort: PosterSort;
    onSortChange: (value: PosterSort) => void;
  };

  custom: {
    url: string;
    onUrlChange: (value: string) => void;
    onAddUrl: () => void;
    onPickFile: (file: File) => void;
    isStaging: boolean;
  };

  seasonSource?: {
    seasonNumber: number;
    onSeasonNumberChange: (value: number) => void;
    useShowArt: boolean;
    onUseShowArtChange: (value: boolean) => void;

    appliesToSeason: number;
  };
}

export function PosterBrowserToolbar({
  search,
  filters,
  custom,
  seasonSource,
}: PosterBrowserToolbarProps) {
  return (
    <div className={styles.toolbar}>
      <div className={styles.toolbarRow}>
        <div className={`${styles.inputGroup} ${styles.titleInput}`}>
          <label htmlFor="search-title">Search by title</label>
          <input
            id="search-title"
            type="text"
            placeholder="Enter movie or show title..."
            value={search.title}
            onChange={(e) => search.onTitleChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search.onSubmit()}
          />
        </div>
        <div className={`${styles.inputGroup} ${styles.yearInput}`}>
          <label htmlFor="search-year">Year</label>
          <input
            id="search-year"
            type="number"
            placeholder="Optional"
            value={search.year}
            onChange={(e) => search.onYearChange(e.target.value)}
          />
        </div>
        <div className={styles.inputGroup}>
          <label htmlFor="poster-language">Language</label>
          <select
            id="poster-language"
            value={filters.language}
            onChange={(e) => filters.onLanguageChange(e.target.value)}
          >
            <option value="">Any / textless</option>
            {POSTER_LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>
        {filters.availableProviders.length > 1 && (
          <div className={styles.inputGroup}>
            <label htmlFor="poster-provider">Provider</label>
            <select
              id="poster-provider"
              value={filters.provider}
              onChange={(e) => filters.onProviderChange(e.target.value)}
            >
              <option value="">All providers</option>
              {filters.availableProviders.map((p) => (
                <option key={p} value={p}>
                  {providerLabel(p)}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className={styles.inputGroup}>
          <label htmlFor="poster-sort">Sort by</label>
          <select
            id="poster-sort"
            value={filters.sort}
            onChange={(e) => filters.onSortChange(e.target.value as PosterSort)}
          >
            {POSTER_SORTS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <button
          className={styles.searchButton}
          onClick={search.onSubmit}
          disabled={!search.title.trim() || search.isSearching}
        >
          {search.isSearching ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
          Search
        </button>
      </div>

      <div className={styles.toolbarRow}>
        <div className={`${styles.inputGroup} ${styles.titleInput}`}>
          <label htmlFor="custom-poster-url">Use your own image</label>
          <input
            id="custom-poster-url"
            type="text"
            placeholder="Paste an image URL…"
            value={custom.url}
            onChange={(e) => custom.onUrlChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && custom.onAddUrl()}
            disabled={custom.isStaging}
          />
        </div>
        <button
          className={styles.searchButton}
          onClick={custom.onAddUrl}
          disabled={!custom.url.trim() || custom.isStaging}
        >
          {custom.isStaging ? <Loader2 size={16} className="spin" /> : 'Add'}
        </button>
        <label
          className={`${styles.searchButton} ${styles.uploadLabel} ${custom.isStaging ? styles.uploadLabelBusy : ''}`}
        >
          <Upload size={16} />
          Upload
          <input
            type="file"
            accept="image/*"
            className={styles.fileInput}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) custom.onPickFile(file);
              e.target.value = '';
            }}
            disabled={custom.isStaging}
          />
        </label>
      </div>

      {seasonSource && (
        <div className={styles.toolbarRow}>
          <div className={styles.sourceGroup}>
            <span className={styles.sourceLabel}>Artwork source</span>
            <div className={styles.segmented} role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={!seasonSource.useShowArt}
                className={`${styles.segment} ${!seasonSource.useShowArt ? styles.segmentActive : ''}`}
                onClick={() => seasonSource.onUseShowArtChange(false)}
              >
                Season art
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={seasonSource.useShowArt}
                className={`${styles.segment} ${seasonSource.useShowArt ? styles.segmentActive : ''}`}
                onClick={() => seasonSource.onUseShowArtChange(true)}
              >
                Show art
              </button>
            </div>
          </div>
          <div className={`${styles.inputGroup} ${styles.seasonInput}`}>
            <label htmlFor="search-season">Season #</label>
            <input
              id="search-season"
              type="number"
              min={0}
              value={seasonSource.seasonNumber}
              onChange={(e) => seasonSource.onSeasonNumberChange(Number(e.target.value))}
              disabled={seasonSource.useShowArt}
            />
          </div>
          {seasonSource.useShowArt && (
            <p className={styles.sourceHint}>
              Browsing the show's posters — the one you pick still applies to Season{' '}
              {seasonSource.appliesToSeason}.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
