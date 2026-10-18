import {z} from 'zod';
import {anchor, base, text} from '../../shared/schema.ts';

export const schema = z.strictObject({
  ...base(),
  name: text(28, 'the name, on the first line'),
  role: text(40, 'the role or title under the name').default(''),
  corner: anchor.default('bottom-left'),
});
export type Props = z.infer<typeof schema>;
