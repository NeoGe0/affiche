import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { LanguageOrderList } from './LanguageOrderList';

const TEXTLESS = '';

function renderList(languages: string[]) {
  const onChange = vi.fn();
  render(<LanguageOrderList languages={languages} onChange={onChange} />);
  return { onChange };
}

describe('LanguageOrderList', () => {
  it('labels the textless entry rather than showing an empty row', () => {
    renderList([TEXTLESS, 'en']);

    expect(screen.getByText('Textless')).toBeInTheDocument();
    expect(screen.getByText('English')).toBeInTheDocument();
  });

  it('moves an entry up', async () => {
    const user = userEvent.setup();
    const { onChange } = renderList([TEXTLESS, 'en', 'fr']);

    await user.click(screen.getByRole('button', { name: 'Move French up' }));

    expect(onChange).toHaveBeenCalledWith([TEXTLESS, 'fr', 'en']);
  });

  it('moves an entry down', async () => {
    const user = userEvent.setup();
    const { onChange } = renderList([TEXTLESS, 'en', 'fr']);

    await user.click(screen.getByRole('button', { name: 'Move Textless down' }));

    expect(onChange).toHaveBeenCalledWith(['en', TEXTLESS, 'fr']);
  });

  it('cannot move the ends past the list', () => {
    renderList([TEXTLESS, 'en']);

    expect(screen.getByRole('button', { name: 'Move Textless up' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Move English down' })).toBeDisabled();
  });

  it('removes an entry', async () => {
    const user = userEvent.setup();
    const { onChange } = renderList([TEXTLESS, 'en']);

    await user.click(screen.getByRole('button', { name: 'Remove English' }));

    expect(onChange).toHaveBeenCalledWith([TEXTLESS]);
  });

  it('refuses to empty the list', async () => {
    const user = userEvent.setup();
    const { onChange } = renderList([TEXTLESS]);

    const remove = screen.getByRole('button', { name: 'Remove Textless' });
    expect(remove).toBeDisabled();
    await user.click(remove);

    expect(onChange).not.toHaveBeenCalled();
  });

  it('appends a language from the add menu, offering only the ones not in the list', async () => {
    const user = userEvent.setup();
    const { onChange } = renderList([TEXTLESS, 'en']);

    await user.click(screen.getByRole('button', { name: /Add language/ }));

    expect(screen.getAllByText('English')).toHaveLength(1);
    await user.click(screen.getByRole('menuitem', { name: 'German' }));

    expect(onChange).toHaveBeenCalledWith([TEXTLESS, 'en', 'de']);
  });

  it('disables the add button once every language is in the list', () => {
    render(
      <LanguageOrderList
        languages={[TEXTLESS, 'en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'ja', 'ko', 'zh']}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByRole('button', { name: /Add language/ })).toBeDisabled();
  });
});
