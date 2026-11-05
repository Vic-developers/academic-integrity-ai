import type { PageViewport } from "pdfjs-dist";
import type { EvidenceView } from "./evidence";
type Geometry = NonNullable<EvidenceView["page_geometry"]>;
/** pdfplumber uses the rotated MediaBox, while PDF.js renders the visible CropBox.
 * Invert pdfminer's page CTM first, then let PDF.js apply crop, rotation and UserUnit.
 * This also supports immutable extractions created before the viewer correction.
 */
export function pdfProjection(
  g: Geometry | null,
  rotation: number,
  view: number[],
  viewport: PageViewport,
) {
  if (
    !g ||
    ![0, 90, 180, 270].includes(g.rotation) ||
    g.rotation !== ((rotation % 360) + 360) % 360 ||
    g.bbox.length !== 4 ||
    view.length !== 4 ||
    ![...g.bbox, ...view, g.width, g.height].every(Number.isFinite) ||
    g.width <= 0 ||
    g.height <= 0 ||
    Math.abs(g.bbox[2] - g.bbox[0] - g.width) > 0.1 ||
    Math.abs(g.bbox[3] - g.bbox[1] - g.height) > 0.1
  )
    return null;
  const normalized = [g.bbox[0], -g.bbox[1], g.bbox[2], g.height - g.bbox[1]];
  const media =
    g.rotation === 90 || g.rotation === 270
      ? [normalized[1], normalized[0], normalized[3], normalized[2]]
      : normalized;
  if (
    view[0] < media[0] - 0.1 ||
    view[1] < media[1] - 0.1 ||
    view[2] > media[2] + 0.1 ||
    view[3] > media[3] + 0.1 ||
    view[2] <= view[0] ||
    view[3] <= view[1]
  )
    return null;
  return (box: number[]): number[] | null => {
    if (
      box.length !== 4 ||
      !box.every(Number.isFinite) ||
      box[2] <= box[0] ||
      box[3] <= box[1]
    )
      return null;
    const points = [
      [box[0], box[1]],
      [box[2], box[1]],
      [box[0], box[3]],
      [box[2], box[3]],
    ].map(([x, top]) => {
      const u = x - g.bbox[0],
        v = g.height - (top - g.bbox[1]);
      const [px, py] =
        g.rotation === 90
          ? [media[2] - v, media[1] + u]
          : g.rotation === 180
            ? [media[2] - u, media[3] - v]
            : g.rotation === 270
              ? [media[0] + v, media[3] - u]
              : [media[0] + u, media[1] + v];
      return viewport.convertToViewportPoint(px, py);
    });
    const left = Math.max(0, Math.min(...points.map((p) => p[0]))),
      top = Math.max(0, Math.min(...points.map((p) => p[1])));
    const right = Math.min(
        viewport.width,
        Math.max(...points.map((p) => p[0])),
      ),
      bottom = Math.min(viewport.height, Math.max(...points.map((p) => p[1])));
    return right > left && bottom > top ? [left, top, right, bottom] : null;
  };
}
