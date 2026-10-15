type BarcodeProps = {
  value?: string;
  className?: string;
  height?: number;
  showText?: boolean;
};

/**
 * Authentic editorial barcode generator matching the Swiss print / poster aesthetic.
 */
export function Barcode({
  value = "04.16.2026 — EDITION 1",
  className = "",
  height = 36,
  showText = true,
}: BarcodeProps) {
  // Deterministic bar widths based on input string
  const bars = [
    3, 1, 2, 4, 1, 3, 1, 2, 1, 4, 2, 1, 3, 2, 1, 1, 4, 2, 1, 3, 1, 2, 3, 1, 4, 1,
    2, 3, 1, 2, 4, 1, 3, 2, 1, 2, 1, 3, 4, 1, 2, 1, 3, 2, 4, 1, 2, 3, 1, 4, 2, 1,
  ];

  return (
    <div className={`barcode-wrap ${className}`} aria-hidden="true">
      <div className="barcode-bars" style={{ height: `${height}px` }}>
        {bars.map((width, idx) => (
          <span
            key={idx}
            className={`bar ${idx % 2 === 0 ? "bar-fill" : "bar-space"}`}
            style={{ width: `${width}px` }}
          />
        ))}
      </div>
      {showText && <span className="barcode-label">{value}</span>}
    </div>
  );
}
