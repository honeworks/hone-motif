import {z} from 'zod';
import {base, text} from '../../shared/schema.ts';

export const schema = z.strictObject({
  ...base(),
  title: text(32, 'the big title'),
  subtitle: text(48, 'a line under the title').default(''),
});
export type Props = z.infer<typeof schema>;
