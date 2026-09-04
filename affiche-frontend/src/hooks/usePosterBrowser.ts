import { useCallback, useState } from 'react';
import { errorMessage, libraryApi, postersApi } from '../api';
import { useToast } from '../context/ToastContext';
import type { ItemSeason, LibraryItem, OverlayOptions, TextOptions } from '../types';

export interface ApplyPosterOptions {
  overlayOptions?: OverlayOptions;
  textOptions?: TextOptions;
  jpegQuality?: number;
  title?: string;
  upload?: boolean;
}

interface UsePosterBrowserOptions {

  item: Pick<LibraryItem, 'id' | 'library_id'> | null;

  mediaServerId?: number;

  onApplied: (target: 'item' | 'season') => void;
}

export function usePosterBrowser({ item, mediaServerId, onApplied }: UsePosterBrowserOptions) {
  const toast = useToast();
  const [isOpen, setIsOpen] = useState(false);
  const [season, setSeason] = useState<ItemSeason | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [uploadDefault, setUploadDefault] = useState(false);

  const loadUploadDefault = useCallback(async (libraryId: number) => {
    if (mediaServerId == null) {
      setUploadDefault(false);
      return;
    }
    try {
      const settings = await libraryApi.getLibrarySettings(mediaServerId, libraryId);
      setUploadDefault(settings.upload_enabled);
    } catch {
      setUploadDefault(false);
    }
  }, [mediaServerId]);

  const open = useCallback(async (forSeason: ItemSeason | null) => {
    if (item) await loadUploadDefault(item.library_id);
    setSeason(forSeason);
    setIsOpen(true);
  }, [item, loadUploadDefault]);

  const close = useCallback(() => {
    setIsOpen(false);
    setSeason(null);
  }, []);

  const save = useCallback(async (posterUrl: string, opts: ApplyPosterOptions) => {
    if (!item || mediaServerId == null) return;

    const target = season ? 'season' : 'item';
    setIsSaving(true);
    try {
      await postersApi.applyPoster({
        mediaServerId,
        libraryId: item.library_id,
        itemId: item.id,
        posterUrl,
        seasonNumber: season?.season_number,
        jpegQuality: opts.jpegQuality,
        title: opts.title,
        overlayOptions: opts.overlayOptions,
        textOptions: opts.textOptions,
        upload: opts.upload,
      });

      setIsOpen(false);
      setSeason(null);
      onApplied(target);
    } catch (error) {
      console.error('Failed to apply poster:', error);
      toast.error(errorMessage(error, 'Failed to apply poster. Please try again.'), {
        title: 'Apply failed',
      });
    } finally {
      setIsSaving(false);
    }
  }, [item, mediaServerId, season, onApplied, toast]);

  return { isOpen, season, isSaving, uploadDefault, open, close, save };
}
