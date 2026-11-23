// Same palette as the backend (processor.py, there in BGR), indexed by class id.
const BGR: [number, number, number][] = [
  [56, 56, 255], [151, 157, 255], [31, 112, 255], [29, 178, 255], [49, 210, 207], [10, 249, 72],
  [23, 204, 146], [134, 219, 61], [52, 147, 26], [187, 212, 0], [168, 153, 44], [255, 194, 0],
  [147, 69, 52], [255, 115, 100], [236, 24, 0], [255, 56, 132], [133, 0, 82],
];

export function classColor(index: number): string {
  const [b, g, r] = BGR[((index % BGR.length) + BGR.length) % BGR.length];
  return `rgb(${r}, ${g}, ${b})`;
}
