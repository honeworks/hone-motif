/** Dark or light ink that reads on a solid `#rrggbb` fill. */
export const inkOn = (hex: string, dark = '#16181b', light = '#ffffff'): string => {
  const n = parseInt(hex.slice(1, 7), 16);
  const lum = 0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255);
  return lum > 150 ? dark : light;
};
