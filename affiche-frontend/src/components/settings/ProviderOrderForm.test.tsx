import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ProviderOrderForm } from './ProviderOrderForm';

const BASE = ['tmdb', 'tvdb', 'fanart'];

function renderForm(providers = BASE, onSave = vi.fn().mockResolvedValue(undefined)) {
  const utils = render(
    <ProviderOrderForm
      title="Provider priority"
      description="Order providers"
      providers={providers}
      onSave={onSave}
      isSaving={false}
    />
  );
  return { ...utils, onSave };
}

const shownOrder = () =>
  screen.getAllByText(/^(TMDB|TVDB|Fanart\.tv|MediUX)$/).map((el) => el.textContent);

const saveButton = () => screen.queryByRole('button', { name: /save order/i });

describe('ProviderOrderForm', () => {
  it('renders the given order with no pending changes', () => {
    renderForm();

    expect(shownOrder()).toEqual(['TMDB', 'TVDB', 'Fanart.tv']);
    expect(saveButton()).not.toBeInTheDocument();
  });

  it('reorders and reveals the save footer when moving an entry up', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole('button', { name: 'Move TVDB up' }));

    expect(shownOrder()).toEqual(['TVDB', 'TMDB', 'Fanart.tv']);
    expect(saveButton()).toBeInTheDocument();
  });

  it('saves the edited order and clears the footer', async () => {
    const user = userEvent.setup();
    const { onSave } = renderForm();

    await user.click(screen.getByRole('button', { name: 'Move TMDB down' }));
    await user.click(saveButton()!);

    expect(onSave).toHaveBeenCalledWith(['tvdb', 'tmdb', 'fanart']);
    expect(saveButton()).not.toBeInTheDocument();
  });

  it('reset restores the prop order and drops the draft', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole('button', { name: 'Move Fanart.tv up' }));
    expect(shownOrder()).toEqual(['TMDB', 'Fanart.tv', 'TVDB']);

    await user.click(screen.getByRole('button', { name: /reset/i }));

    expect(shownOrder()).toEqual(['TMDB', 'TVDB', 'Fanart.tv']);
    expect(saveButton()).not.toBeInTheDocument();
  });

  it('adopts a new provider order pushed from the server', async () => {

    const { rerender } = renderForm();

    rerender(
      <ProviderOrderForm
        key="fanart,tmdb,tvdb"
        title="Provider priority"
        description="Order providers"
        providers={['fanart', 'tmdb', 'tvdb']}
        onSave={vi.fn()}
        isSaving={false}
      />
    );

    expect(shownOrder()).toEqual(['Fanart.tv', 'TMDB', 'TVDB']);
  });

  it('disables editing while a save is in flight', () => {
    render(
      <ProviderOrderForm
        title="Provider priority"
        description="Order providers"
        providers={BASE}
        onSave={vi.fn()}
        isSaving
      />
    );

    screen
      .getAllByRole('button', { name: /^Move .+ down$/ })
      .forEach((b) => expect(b).toBeDisabled());
  });
});
