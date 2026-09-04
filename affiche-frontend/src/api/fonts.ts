import { api, postForm } from './client';

export const fontsApi = {

  getFonts: (): Promise<string[]> => api.get('/service/fonts'),

  getUserFonts: (): Promise<string[]> => api.get('/service/user-fonts'),

  uploadFont: (file: File): Promise<{ name: string }> => {
    const form = new FormData();
    form.append('file', file);
    return postForm('/service/fonts', form);
  },

  deleteFont: (name: string): Promise<void> =>
    api.delete(`/service/fonts/${encodeURIComponent(name)}`),
};
