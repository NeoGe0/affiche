import { useEffect, useEffectEvent, useRef, useState } from 'react';

import { collectionsApi, errorMessage } from '../api';
import { useToast } from '../context/ToastContext';
import type { Collection } from '../types';

interface UseCollectionsOptions {
  mediaServerId?: number;
  libraryId?: number;
  search: string;
}

export function useCollections({ mediaServerId, libraryId, search }: UseCollectionsOptions) {
  const toast = useToast();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);
  const latestRequest = useRef(0);

  const listingKey = `${mediaServerId ?? ''}|${libraryId ?? ''}|${search}`;

  const fetchCollections = useEffectEvent(async () => {
    if (!mediaServerId || !libraryId) {
      setCollections([]);
      setIsLoading(false);
      return;
    }
    const request = ++latestRequest.current;
    try {
      const page = await collectionsApi.getCollections(mediaServerId, libraryId,
                                                       { search: search || undefined });
      if (request !== latestRequest.current) return;
      setCollections(page.collections);
    } catch (error) {
      if (request !== latestRequest.current) return;
      toast.error(errorMessage(error, 'Failed to load collections.'), { title: 'Collections' });
      setCollections([]);
    } finally {
      if (request === latestRequest.current) setIsLoading(false);
    }
  });

  useEffect(() => {
    setIsLoading(true);
    void fetchCollections();
  }, [listingKey, refreshToken]);

  const reload = () => setRefreshToken((n) => n + 1);

  const write = async <T,>(action: () => Promise<T>, errorTitle: string, fallback: string) => {
    if (!mediaServerId || !libraryId) return undefined;
    setIsBusy(true);
    try {
      const result = await action();
      reload();
      return result;
    } catch (error) {
      toast.error(errorMessage(error, fallback), { title: errorTitle });
      return undefined;
    } finally {
      setIsBusy(false);
    }
  };

  return {
    collections,
    isLoading,
    isBusy,
    reload,
    create: (title: string, itemIds: number[]) =>
      write(() => collectionsApi.createCollection(mediaServerId!, libraryId!, title, itemIds),
            'Could not create the collection',
            'The media server would not create the collection.'),
    rename: (collectionId: number, title: string) =>
      write(() => collectionsApi.renameCollection(mediaServerId!, libraryId!, collectionId, title),
            'Could not rename the collection',
            'The media server would not rename the collection.'),
    remove: (collectionId: number) =>
      write(() => collectionsApi.deleteCollection(mediaServerId!, libraryId!, collectionId),
            'Could not delete the collection',
            'The media server would not delete the collection.'),
    addItems: (collectionId: number, itemIds: number[]) =>
      write(() => collectionsApi.addItems(mediaServerId!, libraryId!, collectionId, itemIds),
            'Could not add those items',
            'The media server would not add those items.'),
    removeItems: (collectionId: number, itemIds: number[]) =>
      write(() => collectionsApi.removeItems(mediaServerId!, libraryId!, collectionId, itemIds),
            'Could not remove those items',
            'The media server would not remove those items.'),
    setLock: (collectionId: number, locked: boolean) =>
      write(() => collectionsApi.setLock(mediaServerId!, libraryId!, collectionId, locked),
            'Could not change the lock', 'Failed to change the lock on this collection.'),
  };
}
