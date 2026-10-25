import React, { forwardRef, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, Fragment } from 'react';

const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect;

const GAUSSIAN_EDGE = Math.exp(-2);

const parseSettings = (settings = '') => {
  const map = new Map();
  if (!settings) return map;
  settings
    .split(',')
    .map(p => p.trim())
    .filter(Boolean)
    .forEach(part => {
      const tokens = part.split(/\s+/);
      if (tokens.length >= 2) {
        const axis = tokens[0].replace(/['"]/g, '');
        const val = parseFloat(tokens[1]);
        if (!isNaN(val)) map.set(axis, val);
      }
    });
  return map;
};

const strengthAt = (distance, radius, falloff = 'linear') => {
  if (distance >= radius) return 0;
  const norm = 1 - distance / radius;
  switch (falloff) {
    case 'exponential':
      return norm * norm;
    case 'gaussian':
      return (Math.exp(-2 * Math.pow(distance / radius, 2)) - GAUSSIAN_EDGE) / (1 - GAUSSIAN_EDGE);
    case 'linear':
    default:
      return norm;
  }
};

/**
 * VariableProximity Component
 * Interactive text animation component that smoothly interpolates font-variation-settings
 * ('wght', 'opsz') and applies a responsive, fluid "giggle" micro-animation on cursor hover.
 * When the cursor leaves or moves away, letters seamlessly glide back to their resting state.
 */
export const VariableProximity = forwardRef((props, ref) => {
  const {
    label = '',
    fromFontVariationSettings = "'wght' 400, 'opsz' 9",
    toFontVariationSettings = "'wght' 1000, 'opsz' 40",
    containerRef,
    radius = 100,
    falloff = 'linear',
    smoothing = 0.2,
    fromColor,
    toColor,
    scale = 1.05,
    lift = 2,
    giggle = true,
    idleWave = false,
    fontSize,
    className = '',
    onClick,
    style,
    ...restProps
  } = props;

  const rootRef = useRef(null);
  const letterRefs = useRef([]);
  const stateRef = useRef({ pointer: { x: -9999, y: -9999, active: false }, levels: [], targets: [] });
  const [lineStarts, setLineStarts] = useState(null);
  const directHoverIdxRef = useRef(-1);

  const setRoot = useCallback(
    node => {
      rootRef.current = node;
      if (typeof ref === 'function') ref(node);
      else if (ref) ref.current = node;
    },
    [ref]
  );

  const axes = useMemo(() => {
    const fromMap = parseSettings(fromFontVariationSettings);
    const toMap = parseSettings(toFontVariationSettings);
    return Array.from(fromMap.entries()).map(([axis, fromValue]) => ({
      axis,
      fromValue,
      toValue: toMap.get(axis) ?? fromValue
    }));
  }, [fromFontVariationSettings, toFontVariationSettings]);

  useIsoLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    let frame = 0;
    let live = true;
    let lastWidth = -1;

    const measure = () => {
      frame = 0;
      if (!live) return;
      const words = Array.from(root.querySelectorAll('[data-word]'));
      const breaks = Array.from(root.querySelectorAll('br'));
      const letters = letterRefs.current.filter(Boolean);
      const saved = letters.map(l => l.style.fontVariationSettings);
      const wrap = root.style.whiteSpace;
      root.style.whiteSpace = 'normal';
      breaks.forEach(node => (node.style.display = 'none'));
      letters.forEach(l => (l.style.fontVariationSettings = fromFontVariationSettings));
      const starts = [];
      let lastTop = null;
      words.forEach((word, index) => {
        const top = word.getBoundingClientRect().top;
        if (lastTop !== null && top > lastTop + 2) starts.push(index);
        lastTop = top;
      });
      letters.forEach((l, index) => (l.style.fontVariationSettings = saved[index]));
      breaks.forEach(node => (node.style.display = ''));
      root.style.whiteSpace = wrap;
      const key = starts.join(',');
      setLineStarts(previous => (previous === key ? previous : key));
    };

    const queue = entries => {
      const width = entries?.[0]?.contentRect?.width;
      if (width !== undefined) {
        if (Math.abs(width - lastWidth) < 1) return;
        lastWidth = width;
      }
      if (!frame) frame = requestAnimationFrame(measure);
    };

    measure();
    const parent = root.parentElement;
    const observer = parent && typeof ResizeObserver !== 'undefined' ? new ResizeObserver(queue) : null;
    if (parent && observer) observer.observe(parent);
    if (document.fonts?.ready) document.fonts.ready.then(() => queue());

    return () => {
      live = false;
      cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [label, fromFontVariationSettings, fontSize]);

  useEffect(() => {
    const { pointer, levels, targets } = stateRef.current;
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    let frame = 0;
    let lastTime = 0;
    let nearAny = false;

    const settingsAt = level =>
      axes.map(({ axis, fromValue, toValue }) => `'${axis}' ${(fromValue + (toValue - fromValue) * level).toFixed(1)}`).join(', ');

    const measure = () => {
      const letters = letterRefs.current;
      targets.length = letters.length;
      targets.fill(0);
      nearAny = false;
      if (!pointer.active) return;

      const area = containerRef?.current?.getBoundingClientRect();
      if (area) {
        const dx = Math.max(area.left - pointer.x, 0, pointer.x - area.right);
        const dy = Math.max(area.top - pointer.y, 0, pointer.y - area.bottom);
        if (dx * dx + dy * dy >= (radius + 80) * (radius + 80)) return;
      }

      letters.forEach((letter, index) => {
        if (!letter) return;
        if (directHoverIdxRef.current === index) {
          targets[index] = 1.0;
          nearAny = true;
          return;
        }
        const rect = letter.getBoundingClientRect();
        const distance = Math.hypot(pointer.x - (rect.left + rect.width / 2), pointer.y - (rect.top + rect.height / 2));
        targets[index] = strengthAt(distance, radius, falloff);
        if (targets[index] > 0) nearAny = true;
      });
    };

    const tick = now => {
      frame = 0;
      const delta = lastTime ? Math.min(now - lastTime, 64) : 16;
      lastTime = now;

      measure();

      const ease = smoothing > 0 ? 1 - Math.exp(-delta / (smoothing * 400)) : 1;
      const timeSec = now / 1000;
      let settling = false;

      letterRefs.current.forEach((letter, index) => {
        if (!letter) return;
        const target = targets[index] ?? 0;
        const current = levels[index] ?? 0;
        let next = current + (target - current) * ease;
        if (Math.abs(target - next) < 0.001) {
          next = target;
        } else {
          settling = true;
        }
        levels[index] = next;

        if (next === 0) {
          letter.style.fontVariationSettings = fromFontVariationSettings;
          letter.style.transform = '';
          letter.style.fontWeight = '';
        } else {
          const settings = settingsAt(next);
          letter.style.fontVariationSettings = settings;

          // Weight fallback
          const fromWght = parseSettings(fromFontVariationSettings).get('wght') || 400;
          const toWght = parseSettings(toFontVariationSettings).get('wght') || 800;
          letter.style.fontWeight = Math.round(fromWght + (toWght - fromWght) * next);

          if (!reduced) {
            const liftVal = -lift * next;
            const scaleVal = 1 + (scale - 1) * next;

            if (giggle && next > 0.02) {
              const isDirect = directHoverIdxRef.current === index;
              const directBoost = isDirect ? 1.25 : 1.0;
              const waveY = Math.sin(timeSec * 15 + index * 0.75) * (2.2 * next * directBoost);
              const waveRot = Math.sin(timeSec * 13 + index * 0.9) * (2.2 * next * directBoost);
              const microScale = scaleVal + Math.sin(timeSec * 17 + index) * (0.015 * next);

              letter.style.transform = `translate3d(0, ${(liftVal + waveY).toFixed(2)}px, 0) rotate(${waveRot.toFixed(2)}deg) scale(${microScale.toFixed(3)})`;
              settling = true;
            } else {
              letter.style.transform = `translate3d(0, ${liftVal.toFixed(2)}px, 0) scale(${scaleVal.toFixed(3)})`;
            }
          }
        }
      });

      if (settling || (nearAny && pointer.active)) {
        frame = requestAnimationFrame(tick);
      } else {
        lastTime = 0;
      }
    };

    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(tick);
    };

    const handleMove = (x, y) => {
      pointer.x = x;
      pointer.y = y;
      pointer.active = true;
      schedule();
    };

    const handleMouseMove = event => handleMove(event.clientX, event.clientY);
    const handleTouchMove = event => {
      const touch = event.touches?.[0];
      if (touch) handleMove(touch.clientX, touch.clientY);
    };
    const handleLeave = () => {
      pointer.active = false;
      directHoverIdxRef.current = -1;
      schedule();
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('touchmove', handleTouchMove, { passive: true });
    window.addEventListener('touchend', handleLeave);
    window.addEventListener('touchcancel', handleLeave);
    window.addEventListener('scroll', schedule, { capture: true, passive: true });
    window.addEventListener('resize', schedule);
    document.documentElement.addEventListener('mouseleave', handleLeave);

    schedule();

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleLeave);
      window.removeEventListener('touchcancel', handleLeave);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      document.documentElement.removeEventListener('mouseleave', handleLeave);
    };
  }, [axes, fromFontVariationSettings, toFontVariationSettings, containerRef, radius, falloff, smoothing, scale, lift, giggle, fontSize, label, lineStarts]);

  const words = label.split(' ');
  const breakSet = new Set(lineStarts ? lineStarts.split(',').map(Number) : []);
  let letterIndex = 0;

  return (
    <span
      ref={setRoot}
      className={`variable-proximity ${className}`}
      onClick={onClick}
      style={{
        display: 'inline',
        ...(fontSize !== undefined ? { fontSize: typeof fontSize === 'number' ? `${fontSize}px` : fontSize } : {}),
        ...(lineStarts !== null ? { whiteSpace: 'nowrap' } : {}),
        ...style
      }}
      {...restProps}
    >
      {words.map((word, wordIndex) => (
        <Fragment key={wordIndex}>
          {breakSet.has(wordIndex) && <br />}
          <span data-word="" style={{ display: 'inline-block', whiteSpace: 'nowrap' }}>
            {word.split('').map(letter => {
              const currentLetterIndex = letterIndex++;
              return (
                <span
                  key={currentLetterIndex}
                  ref={el => {
                    letterRefs.current[currentLetterIndex] = el;
                  }}
                  onMouseEnter={() => {
                    directHoverIdxRef.current = currentLetterIndex;
                  }}
                  onMouseLeave={() => {
                    if (directHoverIdxRef.current === currentLetterIndex) {
                      directHoverIdxRef.current = -1;
                    }
                  }}
                  style={{
                    display: 'inline-block',
                    fontVariationSettings: fromFontVariationSettings,
                    transformOrigin: '50% 85%',
                    willChange: 'transform, font-variation-settings, font-weight',
                    userSelect: 'none',
                    cursor: 'default'
                  }}
                  aria-hidden="true"
                >
                  {letter}
                </span>
              );
            })}
            {wordIndex < words.length - 1 && <span style={{ display: 'inline-block' }}>&nbsp;</span>}
          </span>
        </Fragment>
      ))}
      <span className="sr-only">{label}</span>
    </span>
  );
});

VariableProximity.displayName = 'VariableProximity';
export default VariableProximity;
