import { describe, expect, it } from 'vitest';
import { jobFinished, validRegion } from './workspace';
import { catalog, direction, locales, translate } from './i18n';

describe('image coordinates', () => {
  it('allows an exact full image and a contained original-pixel crop', () => {
    expect(validRegion({ x: 0, y: 0, width: 1200, height: 1800 }, 1200, 1800)).toBe(true);
    expect(validRegion({ x: 200, y: 450, width: 600, height: 200 }, 1200, 1800)).toBe(true);
  });
  it('rejects crops outside the source, empty areas and non-pixel values', () => {
    expect(validRegion({ x: 1199, y: 0, width: 2, height: 20 }, 1200, 1800)).toBe(false);
    expect(validRegion({ x: -1, y: 0, width: 20, height: 20 }, 1200, 1800)).toBe(false);
    expect(validRegion({ x: 0, y: 0, width: 0, height: 20 }, 1200, 1800)).toBe(false);
    expect(validRegion({ x: 0.5, y: 0, width: 20, height: 20 }, 1200, 1800)).toBe(false);
    expect(validRegion({ x: 0, y: Number.NaN, width: 20, height: 20 }, 1200, 1800)).toBe(false);
  });
});

describe('job and language state', () => {
  it('keeps queued and running work polling and stops for actual terminal states', () => {
    expect(jobFinished('queued')).toBe(false);
    expect(jobFinished('running')).toBe(false);
    expect(jobFinished('completed')).toBe(true);
    expect(jobFinished('cancelled')).toBe(true);
    expect(jobFinished('failed')).toBe(true);
    expect(jobFinished('interrupted')).toBe(true);
  });
  it('provides every visible message in all five language catalogs', () => {
    for (const translations of Object.values(catalog)) {
      expect(translations).toHaveLength(5);
      expect(translations.every(value => value.trim().length > 0)).toBe(true);
    }
    expect(locales.map(item => item.id)).toEqual(['en', 'nl', 'ar', 'fr', 'de']);
    expect(direction('ar')).toBe('rtl');
    expect(direction('en')).toBe('ltr');
    expect(translate('nl', 'research')).toBe('Onderzoek');
  });
});
