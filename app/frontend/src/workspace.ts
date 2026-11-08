import type { Region } from './types';

export function validRegion(region: Region, imageWidth: number, imageHeight: number): boolean {
  const values = [region.x, region.y, region.width, region.height, imageWidth, imageHeight];
  return values.every(Number.isFinite) && values.every(Number.isInteger)
    && region.x >= 0 && region.y >= 0 && region.width > 0 && region.height > 0
    && region.x + region.width <= imageWidth && region.y + region.height <= imageHeight;
}

export function jobFinished(status: string): boolean {
  return ['complete', 'completed', 'succeeded', 'failed', 'cancelled', 'interrupted'].includes(status);
}

