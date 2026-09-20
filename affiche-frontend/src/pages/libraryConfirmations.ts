export type ConfirmAction =
  | 'generate' | 'upload' | 'reset'
  | 'item-reset'
  | 'selection-generate' | 'selection-upload' | 'selection-reset'
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

  pendingCount?: number;

  uploadsAutomatically?: boolean;
}

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`;

const KEPT_FOR_RESET = 'The artwork it shows now is kept, so Reset puts it back.';

export function confirmationCopy(
  action: ConfirmAction,
  { libraryName, itemName, selectionCount, pendingCount, uploadsAutomatically }: ConfirmationContext
): ConfirmationCopy {
  switch (action) {
    case 'generate': {
      const scope = pendingCount === undefined
        ? 'the items that have no poster yet'
        : `the items that have no poster yet (${pendingCount.toLocaleString()})`;
      const destination = uploadsAutomatically === undefined
        ? 'Libraries that upload automatically send new posters straight to the media server; the others keep them in Affiche until you upload.'
        : uploadsAutomatically
          ? `This library uploads automatically, so each new poster replaces the media server's artwork as it is made. ${KEPT_FOR_RESET}`
          : 'New posters stay in Affiche until you upload them.';
      return {
        title: 'Generate posters',
        message: `This syncs ${libraryName}, then generates posters for ${scope}. Locked items are skipped. ${destination}`,
        confirmLabel: uploadsAutomatically ? 'Generate & upload' : 'Generate',
      };
    }
    case 'upload':
      return {
        title: 'Upload posters',
        message: `This uploads every poster in ${libraryName} that is generated but not on the media server yet, replacing the artwork the media server shows. ${KEPT_FOR_RESET}`,
        confirmLabel: 'Upload',
      };
    case 'reset':
      return {
        title: 'Reset posters',
        message: `This puts back the artwork the media server had for every item in ${libraryName} that Affiche made a poster for. Those posters are discarded; you can generate them again.`,
        confirmLabel: 'Reset',
        variant: 'danger',
        checkboxLabel: 'Also reset items with no poster yet',
      };
    case 'item-reset':
      return {
        title: 'Reset poster',
        message: `This puts back the artwork the media server had for "${itemName}". Affiche's poster is discarded; you can generate it again.`,
        confirmLabel: 'Reset',
        variant: 'danger',
      };
    case 'selection-generate':
      return {
        title: 'Generate selected posters',
        message: `This generates posters for ${plural(selectionCount, 'selected item')}, replacing any poster Affiche already made for them. Libraries that upload automatically send the new posters straight to the media server.`,
        confirmLabel: `Generate ${selectionCount}`,
      };
    case 'selection-upload':
      return {
        title: 'Upload selected posters',
        message: `This uploads the posters of ${plural(selectionCount, 'selected item')} to the media server, replacing the artwork it shows for them. ${KEPT_FOR_RESET}`,
        confirmLabel: `Upload ${selectionCount}`,
      };
    case 'selection-reset':
      return {
        title: 'Reset selected posters',
        message: `This puts back the original artwork for ${plural(selectionCount, 'selected item')}, including any Affiche never made a poster for. Their Affiche posters are discarded; you can generate them again.`,
        confirmLabel: `Reset ${selectionCount}`,
        variant: 'danger',
      };
    case 'empty-trash':
      return {
        title: 'Empty trash',

        message: `This will permanently remove all trashed items in ${libraryName}, including their generated posters, from Affiche's own database. Your media server is never touched — no media, metadata or artwork is deleted there. This action cannot be undone.`,
        confirmLabel: 'Empty trash',
        variant: 'danger',
      };
  }
}
