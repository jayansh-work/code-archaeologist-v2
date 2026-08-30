export const NODE_W = 188;
export const NODE_H = 72;
export const GAP_X = 56;
export const GAP_Y = 52;
export const GRAPH_PAD = 16;

export function columnCount(width: number): number {
  if (width < 560) {
    return 2;
  }
  if (width < 900) {
    return 3;
  }
  return 4;
}

export function snakePosition(index: number, columns: number): { x: number; y: number } {
  const col = index % columns;
  const row = Math.floor(index / columns);
  return {
    x: GRAPH_PAD + col * (NODE_W + GAP_X),
    y: GRAPH_PAD + row * (NODE_H + GAP_Y),
  };
}

export function isWrapStep(index: number, columns: number): boolean {
  return (index + 1) % columns === 0;
}
