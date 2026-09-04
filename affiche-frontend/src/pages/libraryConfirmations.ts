export type ConfirmAction =
  | 'sync' | 'generate' | 'upload' | 'reset'
  | 'item-sync' | 'item-generate' | 'item-reset'
  | 'selection-reset'
  | 'empty-trash';

export interface ConfirmationCopy {
  title: string;
  message: string;
  confirmLabel: string;
  variant?: 'danger';

  checkboxLabel?: string;
}

interface ConfirmationContext {

  libraryName: string;

  itemName: string;

  selectionCount: number;
}

export function confirmationCopy(
  action: ConfirmAction,
  { libraryName, itemName, selectionCount }: ConfirmationContext
): ConfirmationCopy {
  switch (action) {
    case 'sync':
      return {
        title: 'Sync Library',
        message: `This will sync metadata for ${libraryName}. Continue?`,
        confirmLabel: 'Sync',
      };
    case 'generate':
      return {
        title: 'Generate Posters',
        message: `This will generate posters for ${libraryName}. Continue?`,
        confirmLabel: 'Generate',
      };
    case 'upload':
      return {
        title: 'Upload Posters',
        message: `This will upload generated posters that haven't been uploaded yet in ${libraryName} to the media server. Continue?`,
        confirmLabel: 'Upload',
      };
    case 'reset':
      return {
        title: 'Reset Posters',
        message: `This will reset processed posters in ${libraryName} to their originals. This action cannot be undone.`,
        confirmLabel: 'Reset',
        variant: 'danger',
        checkboxLabel: 'Also reset unprocessed items',
      };
    case 'item-sync':
      return {
        title: 'Sync Metadata',
        message: `This will sync metadata for "${itemName}". Continue?`,
        confirmLabel: 'Sync',
      };
    case 'item-generate':
      return {
        title: 'Generate Poster',
        message: `This will generate a poster for "${itemName}". Continue?`,
        confirmLabel: 'Generate',
      };
    case 'item-reset':
      return {
        title: 'Reset Poster',
        message: `This will reset the poster for "${itemName}" to its original. Continue?`,
        confirmLabel: 'Reset',
        variant: 'danger',
      };
    case 'selection-reset':
      return {
        title: 'Reset Selected Posters',
        message: `This will reset ${selectionCount} selected item${selectionCount === 1 ? '' : 's'} to their original artwork, including any that were never processed. This action cannot be undone.`,
        confirmLabel: `Reset ${selectionCount}`,
        variant: 'danger',
      };
    case 'empty-trash':
      return {
        title: 'Empty Trash',

        message: `This will permanently remove all trashed items in ${libraryName}, including their generated posters, from Affiche's own database. Your media server is never touched — no media, metadata or artwork is deleted there. This action cannot be undone.`,
        confirmLabel: 'Empty trash',
        variant: 'danger',
      };
  }
}
