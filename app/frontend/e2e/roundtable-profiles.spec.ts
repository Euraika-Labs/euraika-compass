import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';
import type { Connection, CorpusSource, Persona, RoundtableRoom, RoundtableScope } from '../src/types';

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

interface ParticipantInput {
  name: string; persona_id: string; perspective: string; connection_id: string | null; pinned: boolean;
}
interface RoomInput extends RoundtableScope {
  topic: string; language: string; participants: ParticipantInput[];
}

async function mockRoundtable(page: Page) {
  const personas: Persona[] = Object.entries(profileNames).map(([id, name], index) => ({
    id, name, description: 'API description fixture', ...(index >= 5 && { roundtable_only: true }),
  }));
  const submissions: RoomInput[] = [];
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
      const input: RoomInput = request.postDataJSON();
      submissions.push(input);
      const { topic, language, participants, ...scope } = input;
      body = {
        id: 'profiles-fixture', topic, language, scope, status: 'awaiting_moderator', revision: 0,
        evidence: [], evidence_version: null, turns: [],
        participants: participants.map((participant, index) => ({
          ...participant, id: `speaker-${index}`, connection_id: route.id, model_id: route.model_id,
          provider: route.provider, local: route.local, status: 'ready',
          allocation: participant.connection_id ? 'manual' : 'automatic',
          allocation_basis: participant.connection_id ? 'moderator' : 'single_candidate',
        })),
      } satisfies RoundtableRoom;
    }
    await intercepted.fulfill({ json: body });
  });
  return submissions;
}

test('a topic alone starts a Roundtable with named perspectives and automatic model selection', async ({ page }) => {
  const submissions = await mockRoundtable(page);
  const topic = 'What differences in historical context matter to this reading?';
  const defaultPerspectives = [
    'What does the passage say in its immediate context?',
    'Which assumptions or counterarguments could change the conclusion?',
  ];
  await page.goto('/');
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  await page.getByRole('button', { name: 'Roundtable', exact: true }).click();
  await expect(page.getByText('Customize participants', { exact: true })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Participant label' })).toHaveCount(0);
  await expect(page.getByRole('combobox', { name: 'Model route' })).toHaveCount(0);
  for (const perspective of defaultPerspectives) {
    await expect(page.getByText(perspective, { exact: true })).toBeVisible();
  }
  const start = page.getByRole('button', { name: 'Start roundtable', exact: true });
  await expect(start).toBeDisabled();
  await page.getByRole('textbox', { name: 'Roundtable topic' }).fill(topic);
  await start.click();
  await expect(page.getByRole('region', { name: 'Roundtable transcript' })).toBeVisible();
  await expect(page.getByRole('heading', { name: profileNames.textual, exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: profileNames.critical, exact: true })).toBeVisible();
  expect(submissions).toHaveLength(1);
  expect(submissions[0]).toMatchObject({ topic, participants: [
    { name: profileNames.textual, persona_id: 'textual', perspective: defaultPerspectives[0], connection_id: null, pinned: false },
    { name: profileNames.critical, persona_id: 'critical', perspective: defaultPerspectives[1], connection_id: null, pinned: false },
  ] });
});

test('built-in Roundtable profiles form a ready-to-use roster and preserve moderator edits', async ({ page }) => {
  const submissions = await mockRoundtable(page);
  const topic = 'How can we compare manuscript witnesses?';
  const expectedParticipants = [
    { name: profileNames.manuscripts, persona_id: 'manuscripts', perspective: expect.stringMatching(/\S/), connection_id: null, pinned: false },
    { name: 'My reviewer', persona_id: 'historical', perspective: 'Question uncertain dates', connection_id: route.id, pinned: true },
    { name: profileNames.source_verification, persona_id: 'source_verification', perspective: expect.stringMatching(/\S/), connection_id: null, pinned: false },
  ];

  await page.goto('/');
  await page.getByRole('button', { name: 'Chat', exact: true }).click();
  const oneToOne = page.getByRole('combobox', { name: 'Persona', exact: true });
  await expect(oneToOne.locator('option')).toHaveCount(5);
  await expect(oneToOne.locator('option[value="manuscripts"]')).toHaveCount(0);
  await page.getByRole('button', { name: 'Roundtable', exact: true }).click();
  await page.getByRole('textbox', { name: 'Roundtable topic' }).fill(topic);
  await page.getByRole('checkbox', { name: 'Torah', exact: true }).uncheck();
  await page.getByText('Customize participants', { exact: true }).click();

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
  await expect(page.getByRole('region', { name: 'Roundtable transcript' })).toBeVisible();
  await expect(page.getByRole('heading', { name: profileNames.manuscripts, exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'My reviewer', exact: true })).toBeVisible();
  expect(submissions).toEqual([expect.objectContaining({
    collection_filter: ['bible', 'quran'], topic, participants: expectedParticipants,
  })]);
});
