import { motion } from "motion/react";

type SpotlightProps = {
  className?: string;
  color?: string;
};

/**
 * Aceternity-style spotlight treatment for the hero.
 * Reference: https://ui.aceternity.com/components/spotlight
 */
export function Spotlight({
  className = "",
  color = "rgba(15, 15, 15, 0.09)",
}: SpotlightProps) {
  return (
    <motion.div
      aria-hidden="true"
      initial={{ opacity: 0, scale: 0.86, x: "-10%", y: "-8%" }}
      animate={{ opacity: 1, scale: 1, x: "0%", y: "0%" }}
      transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      className={`spotlight-effect ${className}`}
      style={{
        background: `radial-gradient(ellipse at center, ${color} 0%, transparent 68%)`,
      }}
    />
  );
}
