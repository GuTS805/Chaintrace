"use client";

import { useEffect, useRef } from "react";
import { animate, useMotionValue, useTransform, motion } from "framer-motion";

/**
 * Counts up to `value` whenever it changes — used for the confidence % and
 * risk score readouts, so the verdict feels *calculated* the moment new
 * data lands instead of just appearing.
 */
export function AnimatedNumber({
  value,
  format = (n) => Math.round(n).toString(),
  className = "",
}: {
  value: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const motionValue = useMotionValue(0);
  const rendered = useTransform(motionValue, (v) => format(v));
  const first = useRef(true);

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: first.current ? 0.8 : 0.5,
      ease: "easeOut",
    });
    first.current = false;
    return () => controls.stop();
  }, [value, motionValue]);

  return <motion.span className={className}>{rendered}</motion.span>;
}
