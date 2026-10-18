import {z} from 'zod';
import {base} from '../../shared/schema.ts';

export const schema = z.strictObject({
  ...base(),
  direction: z.enum(['ltr', 'rtl']).default('ltr').describe('the way the edge travels'),
});
export type Props = z.infer<typeof schema>;
