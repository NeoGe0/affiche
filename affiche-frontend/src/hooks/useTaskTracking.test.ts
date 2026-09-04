import { describe, expect, it } from 'vitest';

import { taskKindFromName } from './useTaskTracking';

describe('taskKindFromName', () => {
  it('maps the library sync to the filling Sync button', () => {
    expect(taskKindFromName('library_sync')).toBe('sync');
    expect(taskKindFromName('library_sync_7')).toBe('sync');
  });

  it('maps poster generation to the determinate bar', () => {
    expect(taskKindFromName('poster_sync')).toBe('generate');
    expect(taskKindFromName('poster_sync_7')).toBe('generate');
  });

  it('maps the poster reset to the determinate bar', () => {

    expect(taskKindFromName('poster_reset')).toBe('reset');
    expect(taskKindFromName('poster_reset_7')).toBe('reset');
  });

  it('does not confuse the reset with the generation it shares a prefix with', () => {
    expect(taskKindFromName('poster_reset')).not.toBe('generate');
  });

  it('falls back to a bar-less kind for anything else', () => {
    expect(taskKindFromName('poster_upload_2')).toBe('other');
    expect(taskKindFromName('something_new')).toBe('other');
    expect(taskKindFromName(undefined)).toBe('other');
  });
});
