import { expect, test } from '@playwright/test';
import type { Connection, CorpusSource, Persona, RoundtableRoom } from '../src/types';

const profileNames = {
  supportive: 'Supportive conversation partner',
  wisdom: 'Wisdom guide',
  textual: 'Text researcher',
  comparative: 'Comparative scholar',
  critical: 'Critical interlocutor',
  historical: 'Historical context researcher',
  philology: 'Language and translation analyst',
  manuscripts: 'Manuscript and transmission analyst',
  literary: 'Literary context analyst',
  reception: 'History of interpretation researcher',
  source_verification: 'Source verifier',
};

const route: Connection = {
  id: 'profile-test-model', title: 'Fixture model', provider: 'local', model_id: 'profile-fixture',
  base_url: null, local: true, enabled: true, configured: true, api_key_set: false,
};

const source: CorpusSource = {
  id: 'profile-test-source', title: 'Source fixture', url: null, source_type: 'text', provenance: null,
  use_limits: { external_processing: true },
  editions: [{ id: 'profile-test-edition', title: 'Edition fixture', language: 'en', revision: 'test',
    collection_memberships: ['bible'], passage_count: 1 }],
};

test('built-in Roundtable profiles form a ready-to-use roster and preserve moderator edits', async ({ page }) => {
  const personas: (Persona & { roundtable_only?: boolean })[] = Object.entries(profileNames).map(([id, name], index) => ({
    id, name, description: 'API description fixture', ...(index >= 5 && { roundtable_only: true }),
  }));
  const topic = 'How can we compare manuscript witnesses?';
  const submissions: unknown[] = [];
  const expectedParticipants = [
    { name: profileNames.manuscripts, persona_id: 'manuscripts', perspective: '', connection_id: null, pinned: false },
    { name: 'My reviewer', persona_id: 'historical', perspective: 'Question uncertain dates', connection_id: route.id, pinned: true },
    { name: profileNames.source_verification, persona_id: 'source_verification', perspective: '', connection_id: null, pinned: false },
  ];
  const scope = { collection_filter: ['bible', 'quran'] } as const;
  const room: RoundtableRoom = {
    id: 'profiles-fixture', topic, language: 'auto', status: 'awaiting_moderator', revision: 0,
    scope: { collection_filter: [...scope.collection_filter] }, evidence: [], evidence_version: null, turns: [],
    participants: expectedParticipants.map((participant, index) => ({
      ...participant, id: `speaker-${index}`, connection_id: route.id, model_id: route.model_id,
      provider: route.provider, local: route.local, status: 'ready',
      allocation: participant.pinned ? 'manual' : 'automatic',
      allocation_basis: participant.pinned ? 'moderator' : 'single_candidate',
    })),
  };
  await page.route('**/api/v1/**', async intercepted => {
    const request = intercepted.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    let body: unknown = { items: [] };
    if (path === '/health') body = { status: 'ok', version: 'test', database: { ready: true }, features: { roundtable_generation: true } };
    else if (path === '/personas') body = { items: personas };
    else if (path === '/connections') body = { items: [route] };
    else if (path === '/chat-settings') body = { local_only: true };
    else if (path === '/corpus') body = { items: [source] };
    else if (path === '/roundtables' && request.method() === 'POST') {
      submissions.push(request.postDataJSON());
      body = room;
    }
    await intercepted.fulfill({ json: body });
  });

  await page.goto('/');
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  const oneToOne = page.getByRole('combobox', { name: 'Persona', exact: true });
  await expect(oneToOne.locator('option')).toHaveCount(5);
  await expect(oneToOne.locator('option[value="manuscripts"]')).toHaveCount(0);
  await page.getByRole('button', { name: 'Roundtable', exact: true }).click();
  await page.getByRole('textbox', { name: 'Roundtable topic' }).fill(topic);
  await page.getByRole('checkbox', { name: 'Torah', exact: true }).uncheck();

  const forms = page.locator('.roundtable-participant-form');
  const persona = (index: number) => forms.nth(index).getByRole('combobox', { name: 'Persona', exact: true });
  const participantLabel = (index: number) => forms.nth(index).getByRole('textbox', { name: 'Participant label' });
  await expect(persona(0).locator('option')).toHaveCount(11);
  await expect(participantLabel(0)).toHaveAttribute('placeholder', profileNames.textual);
  await page.getByRole('button', { name: 'Manuscript study', exact: true }).click();
  await expect(forms).toHaveCount(3);
  for (const [index, id] of ['manuscripts', 'philology', 'source_verification'].entries()) {
    await expect(persona(index)).toHaveValue(id);
  }
  await expect(participantLabel(0)).toHaveAttribute('placeholder', profileNames.manuscripts);
  await expect(participantLabel(2)).toHaveAttribute('placeholder', profileNames.source_verification);

  await participantLabel(1).fill('My reviewer');
  await forms.nth(1).getByRole('textbox', { name: 'Analytical perspective' }).fill('Question uncertain dates');
  await forms.nth(1).getByRole('combobox', { name: 'Model route' }).selectOption(route.id);
  await forms.nth(1).getByRole('checkbox', { name: 'Pin assignment' }).check();
  await persona(1).selectOption('historical');
  await expect(forms.nth(1).getByText(/historical setting/i)).toBeVisible();
  await page.getByRole('button', { name: 'Text & context', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Replace participants' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(persona(1)).toHaveValue('historical');
  await expect(participantLabel(1)).toHaveValue('My reviewer');
  expect(submissions).toHaveLength(0);

  await page.getByRole('button', { name: 'Start roundtable' }).click();
  await expect(page.getByRole('heading', { name: profileNames.manuscripts, exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'My reviewer', exact: true })).toBeVisible();
  expect(submissions).toEqual([expect.objectContaining({ ...scope, topic, participants: expectedParticipants })]);
});
