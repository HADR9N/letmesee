import { useRef } from "react";
import { motion, useMotionTemplate, useMotionValue } from "motion/react";
import type { MouseEvent, ReactNode } from "react";

type CardSpotlightProps = {
  children: ReactNode;
  className?: string;
  spotlightColor?: string;
  radius?: number;
};

/**
 * Pointer-reactive spotlight card with warm editorial and graphite lighting.
 */
export function CardSpotlight({
  children,
  className = "",
  spotlightColor = "rgba(241, 90, 36, 0.08)",
  radius = 340,
}: CardSpotlightProps) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const background = useMotionTemplate`radial-gradient(${radius}px circle at ${x}px ${y}px, ${spotlightColor}, transparent 80%)`;

  function handleMove(event: MouseEvent<HTMLDivElement>) {
    const bounds = ref.current?.getBoundingClientRect();
    if (!bounds) return;
    x.set(event.clientX - bounds.left);
    y.set(event.clientY - bounds.top);
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMove}
      style={{ backgroundImage: background }}
      className={`card-spotlight ${className}`}
    >
      {children}
    </motion.div>
  );
}

