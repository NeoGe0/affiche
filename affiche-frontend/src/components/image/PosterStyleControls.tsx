import { useId, type ReactNode } from 'react';

import { useCapsOnlyFont } from '../../hooks/useCapsOnlyFont';

import { fontBaseName } from './fontName';
import { fontChoices } from './fontChoices';
import type { GenerationOptions, OverlayOptions, TextOptions } from '../../types';
import styles from './PosterStyleControls.module.css';

interface PosterStyleControlsProps {
  overlayOptions: OverlayOptions;
  textOptions: TextOptions;
  onOverlayChange: (changes: Partial<OverlayOptions>) => void;
  onTextChange: (changes: Partial<TextOptions>) => void;

  jpegQuality?: number;
  onQualityChange?: (quality: GenerationOptions['jpeg_quality']) => void;

  fonts: string[];

  titleSlot?: ReactNode;
}

const asPercent = (ratio: number) => Math.round(ratio * 100);
const fromPercent = (value: string) => parseInt(value) / 100;

const GRAIN_SIZE_MIN = 0.5;
const GRAIN_SIZE_MAX = 10;

const GRADIENT_DIRECTIONS: { value: OverlayOptions['gradient_direction']; label: string }[] = [
  { value: 'bottom', label: 'Bottom' },
  { value: 'top', label: 'Top' },
  { value: 'left', label: 'Left' },
  { value: 'right', label: 'Right' },
];

const GRAVITY_LABELS: { value: TextOptions['gravity']; label: string }[] = [
  { value: 'south', label: 'Bottom' },
  { value: 'center', label: 'Center' },
  { value: 'north', label: 'Top' },
];

export function PosterStyleControls({
  overlayOptions,
  textOptions,
  jpegQuality,
  onOverlayChange,
  onTextChange,
  onQualityChange,
  fonts,
  titleSlot,
}: PosterStyleControlsProps) {

  const capsOnlyFont = useCapsOnlyFont(textOptions.font_name, fonts);

  const fontSizePercent = asPercent(textOptions.max_font_ratio);
  const verticalPositionPercent = asPercent(textOptions.text_offset_ratio);
  const textBlockHeightPercent = asPercent(textOptions.max_height_ratio);
  const lineSpacingPercent = asPercent(textOptions.line_spacing_ratio);
  const textWidthPercent = asPercent(textOptions.max_width_ratio);

  const uid = useId();

  return (
    <div className={styles.controls}>
      {

}
      <div className={styles.group} role="group" aria-labelledby={`${uid}-border`}>
        <h4 className={styles.groupTitle} id={`${uid}-border`}>Border</h4>

        <div className={styles.row}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={overlayOptions.border_enabled}
              onChange={(e) => onOverlayChange({ border_enabled: e.target.checked })}
            />
            <span>Enable border</span>
          </label>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-border-color`}>Color</label>
          <div className={styles.colorRow}>
            <input
              id={`${uid}-border-color`}
              type="color"
              className={styles.colorInput}
              value={overlayOptions.border_color}
              disabled={!overlayOptions.border_enabled}
              onChange={(e) => onOverlayChange({ border_color: e.target.value })}
            />
            <span className={styles.colorValue}>{overlayOptions.border_color}</span>
          </div>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-border-width`}>Width</label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-border-width`}
              type="range"
              min="0"
              max="100"
              className={styles.slider}
              value={overlayOptions.border_px}
              disabled={!overlayOptions.border_enabled}
              onChange={(e) => onOverlayChange({ border_px: parseInt(e.target.value) })}
            />
            <span className={styles.sliderValue}>{overlayOptions.border_px}px</span>
          </div>
        </div>
      </div>

      <div className={styles.group} role="group" aria-labelledby={`${uid}-gradient`}>
        <h4 className={styles.groupTitle} id={`${uid}-gradient`}>Gradient</h4>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-gradient-color`}>Color</label>
          <div className={styles.colorRow}>
            <input
              id={`${uid}-gradient-color`}
              type="color"
              className={styles.colorInput}
              value={overlayOptions.gradient_color}
              onChange={(e) => onOverlayChange({ gradient_color: e.target.value })}
            />
            <span className={styles.colorValue}>{overlayOptions.gradient_color}</span>
          </div>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-gradient-direction`}>Direction</label>
          <select
            id={`${uid}-gradient-direction`}
            className={styles.select}
            value={overlayOptions.gradient_direction}
            onChange={(e) => onOverlayChange({
              gradient_direction: e.target.value as OverlayOptions['gradient_direction'],
            })}
          >
            {GRADIENT_DIRECTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {
}
        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-solid-height`}>Solid height</label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-solid-height`}
              type="range"
              min="0"
              max="100"
              className={styles.slider}
              value={asPercent(overlayOptions.matte_height_ratio)}
              onChange={(e) => onOverlayChange({ matte_height_ratio: fromPercent(e.target.value) })}
            />
            <span className={styles.sliderValue}>
              {asPercent(overlayOptions.matte_height_ratio)}%
            </span>
          </div>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-fade-height`}>Fade height</label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-fade-height`}
              type="range"
              min="0"
              max="100"
              className={styles.slider}
              value={asPercent(overlayOptions.fade_height_ratio)}
              onChange={(e) => onOverlayChange({ fade_height_ratio: fromPercent(e.target.value) })}
            />
            <span className={styles.sliderValue}>
              {asPercent(overlayOptions.fade_height_ratio)}%
            </span>
          </div>
        </div>
      </div>

      <div className={styles.group} role="group" aria-labelledby={`${uid}-text`}>
        <h4 className={styles.groupTitle} id={`${uid}-text`}>Text</h4>

        <div className={styles.row}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={textOptions.enabled}
              onChange={(e) => onTextChange({ enabled: e.target.checked })}
            />
            <span>Overlay title text</span>
          </label>
        </div>

        {titleSlot}

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-font`}>Font</label>
          {

}
          <select
            id={`${uid}-font`}
            className={styles.select}
            style={{ fontFamily: `"${fontBaseName(textOptions.font_name)}"` }}
            value={textOptions.font_name}
            onChange={(e) => onTextChange({ font_name: e.target.value })}
          >
            {fontChoices(fonts, textOptions.font_name).map((font) => (
              <option key={font} value={font} style={{ fontFamily: `"${fontBaseName(font)}"` }}>
                {fontBaseName(font)}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-font-size`}>Font size</label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-font-size`}
              type="range"
              min="5"
              max="30"
              className={styles.slider}
              value={fontSizePercent}
              onChange={(e) => onTextChange({ max_font_ratio: fromPercent(e.target.value) })}
            />
            <span className={styles.sliderValue}>{fontSizePercent}%</span>
          </div>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-font-color`}>Color</label>
          <div className={styles.colorRow}>
            <input
              id={`${uid}-font-color`}
              type="color"
              className={styles.colorInput}
              value={textOptions.font_color}
              onChange={(e) => onTextChange({ font_color: e.target.value })}
            />
            <span className={styles.colorValue}>{textOptions.font_color}</span>
          </div>
        </div>

        {
}
        <div className={styles.row}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={textOptions.all_caps}
              disabled={capsOnlyFont}
              onChange={(e) => onTextChange({ all_caps: e.target.checked })}
            />
            <span className={capsOnlyFont ? styles.disabledText : undefined}>All caps</span>
          </label>
          {capsOnlyFont && (
            <span className={styles.hint}>
              {fontBaseName(textOptions.font_name)} has no lowercase, so this changes nothing
            </span>
          )}
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-position`}>Position</label>
          <select
            id={`${uid}-position`}
            className={styles.select}
            value={textOptions.gravity}
            onChange={(e) => {
              const gravity = e.target.value as TextOptions['gravity'];
              onTextChange(
                gravity === 'center' && textOptions.gravity !== 'center'
                  ? { gravity, text_offset_ratio: 0.5 }
                  : { gravity }
              );
            }}
          >
            {GRAVITY_LABELS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-vertical-position`}>
              Vertical position
            </label>
            <div className={styles.sliderWrapper}>
              <input
                id={`${uid}-vertical-position`}
                type="range"
                min="0"
                max="100"
                className={styles.slider}
                value={verticalPositionPercent}
                aria-describedby={`${uid}-vertical-position-help`}
                onChange={(e) => onTextChange({ text_offset_ratio: fromPercent(e.target.value) })}
              />
              <span className={styles.sliderValue}>{verticalPositionPercent}%</span>
            </div>
          </div>
          <p className={styles.help} id={`${uid}-vertical-position-help`}>
            {textOptions.gravity === 'center'
              ? 'Measured from the bottom — 50% is the middle of the poster.'
              : 'Distance from the poster edge — higher moves the title further in.'}
          </p>
        </div>

        {

}
        <details className={styles.fineTune}>
          <summary className={styles.fineTuneSummary}>Fine-tune the title</summary>

          <div className={styles.field}>
            <div className={styles.row}>
              <label className={styles.label} htmlFor={`${uid}-line-spacing`}>Line spacing</label>
              <div className={styles.sliderWrapper}>
                <input
                  id={`${uid}-line-spacing`}
                  type="range"
                  min="-20"
                  max="100"
                  className={styles.slider}
                  value={lineSpacingPercent}
                  aria-describedby={`${uid}-line-spacing-help`}
                  onChange={(e) => onTextChange({ line_spacing_ratio: fromPercent(e.target.value) })}
                />
                <span className={styles.sliderValue}>{lineSpacingPercent}%</span>
              </div>
            </div>
            <p className={styles.help} id={`${uid}-line-spacing-help`}>
              Gap between the lines of a multi-line title. Negative pulls them together.
            </p>
          </div>

          <div className={styles.field}>
            <div className={styles.row}>
              <label className={styles.label} htmlFor={`${uid}-text-width`}>Text width</label>
              <div className={styles.sliderWrapper}>
                <input
                  id={`${uid}-text-width`}
                  type="range"
                  min="10"
                  max="100"
                  className={styles.slider}
                  value={textWidthPercent}
                  aria-describedby={`${uid}-text-width-help`}
                  onChange={(e) => onTextChange({ max_width_ratio: fromPercent(e.target.value) })}
                />
                <span className={styles.sliderValue}>{textWidthPercent}%</span>
              </div>
            </div>
            <p className={styles.help} id={`${uid}-text-width-help`}>
              How much of the poster&apos;s width one line of the title may use.
            </p>
          </div>

          {

}
          <div className={styles.field}>
            <div className={styles.row}>
              <label className={styles.label} htmlFor={`${uid}-text-block-height`}>Text block height</label>
              <div className={styles.sliderWrapper}>
                <input
                  id={`${uid}-text-block-height`}
                  type="range"
                  min="5"
                  max="100"
                  className={styles.slider}
                  value={textBlockHeightPercent}
                  aria-describedby={`${uid}-text-block-height-help`}
                  onChange={(e) => onTextChange({ max_height_ratio: fromPercent(e.target.value) })}
                />
                <span className={styles.sliderValue}>{textBlockHeightPercent}%</span>
              </div>
            </div>
            <p className={styles.help} id={`${uid}-text-block-height-help`}>
              How much of the poster&apos;s height the whole title may fill. Raise it to let line
              spacing spread the lines instead of shrinking the text.
            </p>
          </div>

          <div className={styles.field}>
            <div className={styles.row}>
              <label className={styles.checkbox}>
                <input
                  type="checkbox"
                  checked={textOptions.auto_wrap}
                  aria-describedby={`${uid}-auto-wrap-help`}
                  onChange={(e) => onTextChange({ auto_wrap: e.target.checked })}
                />
                <span>Auto line breaks</span>
              </label>
            </div>
            <p className={styles.help} id={`${uid}-auto-wrap-help`}>
              Breaks a long title across lines so it can be drawn larger. Line breaks typed into a
              title are always kept, and turn this off for that title.
            </p>
          </div>

          <div className={styles.field}>
            <div className={styles.row}>
              <label className={styles.checkbox}>
                <input
                  type="checkbox"
                  checked={textOptions.break_on_symbols}
                  aria-describedby={`${uid}-break-symbols-help`}
                  onChange={(e) => onTextChange({ break_on_symbols: e.target.checked })}
                />
                <span>Break on “ - ”, “: ”</span>
              </label>
            </div>
            <p className={styles.help} id={`${uid}-break-symbols-help`}>
              Starts a new line where the title contains one of these separators.
            </p>
          </div>

          <div className={styles.row}>
            <label className={styles.checkbox}>
              <input
                type="checkbox"
                checked={textOptions.stroke_enabled}
                onChange={(e) => onTextChange({ stroke_enabled: e.target.checked })}
              />
              <span>Text outline</span>
            </label>
            {textOptions.stroke_enabled && (
              <div className={styles.colorRow}>
                {
}
                <input
                  type="color"
                  aria-label="Outline color"
                  className={styles.colorInput}
                  value={textOptions.stroke_color}
                  onChange={(e) => onTextChange({ stroke_color: e.target.value })}
                />
                <span className={styles.colorValue}>{textOptions.stroke_color}</span>
              </div>
            )}
          </div>
        </details>
      </div>

      {

}
      <details className={`${styles.group} ${styles.foldedGroup}`}>
        <summary className={styles.groupSummary} id={`${uid}-effects`}>Effects</summary>

        <div role="group" aria-labelledby={`${uid}-effects`}>
          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-vignette`}>Vignette</label>
            <div className={styles.sliderWrapper}>
              <input
                id={`${uid}-vignette`}
                type="range"
                min="0"
                max="100"
                className={styles.slider}
                value={asPercent(overlayOptions.vignette_strength)}
                onChange={(e) => onOverlayChange({ vignette_strength: fromPercent(e.target.value) })}
              />
              <span className={styles.sliderValue}>{asPercent(overlayOptions.vignette_strength)}%</span>
            </div>
          </div>

          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-vignette-color`}>Vignette color</label>
            <div className={styles.colorRow}>
              <input
                id={`${uid}-vignette-color`}
                type="color"
                className={styles.colorInput}
                value={overlayOptions.vignette_color}
                disabled={overlayOptions.vignette_strength <= 0}
                onChange={(e) => onOverlayChange({ vignette_color: e.target.value })}
              />
              <span className={styles.colorValue}>{overlayOptions.vignette_color}</span>
            </div>
          </div>

          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-glow`}>Inner glow</label>
            <div className={styles.sliderWrapper}>
              <input
                id={`${uid}-glow`}
                type="range"
                min="0"
                max="100"
                className={styles.slider}
                value={asPercent(overlayOptions.inner_glow_strength)}
                onChange={(e) => onOverlayChange({ inner_glow_strength: fromPercent(e.target.value) })}
              />
              <span className={styles.sliderValue}>{asPercent(overlayOptions.inner_glow_strength)}%</span>
            </div>
          </div>

          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-glow-color`}>Glow color</label>
            <div className={styles.colorRow}>
              <input
                id={`${uid}-glow-color`}
                type="color"
                className={styles.colorInput}
                value={overlayOptions.inner_glow_color}
                disabled={overlayOptions.inner_glow_strength <= 0}
                onChange={(e) => onOverlayChange({ inner_glow_color: e.target.value })}
              />
              <span className={styles.colorValue}>{overlayOptions.inner_glow_color}</span>
            </div>
          </div>

          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-grain`}>Grain</label>
            <div className={styles.sliderWrapper}>
              <input
                id={`${uid}-grain`}
                type="range"
                min="0"
                max="100"
                className={styles.slider}
                value={asPercent(overlayOptions.grain_amount)}
                onChange={(e) => onOverlayChange({ grain_amount: fromPercent(e.target.value) })}
              />
              <span className={styles.sliderValue}>{asPercent(overlayOptions.grain_amount)}%</span>
            </div>
          </div>

          <div className={styles.row}>
            <label className={styles.label} htmlFor={`${uid}-grain-size`}>Grain size</label>
            <div className={styles.sliderWrapper}>
              <input
                id={`${uid}-grain-size`}
                type="range"
                min={GRAIN_SIZE_MIN}
                max={GRAIN_SIZE_MAX}
                step="0.5"
                className={styles.slider}
                value={overlayOptions.grain_size}
                disabled={overlayOptions.grain_amount <= 0}
                onChange={(e) => onOverlayChange({ grain_size: parseFloat(e.target.value) })}
              />
              <span className={styles.sliderValue}>{overlayOptions.grain_size}×</span>
            </div>
          </div>
        </div>
      </details>

      {jpegQuality !== undefined && onQualityChange && (
        <details className={`${styles.group} ${styles.foldedGroup}`}>
          <summary className={styles.groupSummary} id={`${uid}-output`}>Output</summary>

          <div className={styles.row} role="group" aria-labelledby={`${uid}-output`}>
            <label className={styles.label} htmlFor={`${uid}-quality`}>Image quality</label>
            <div className={styles.sliderWrapper}>
              <input
                id={`${uid}-quality`}
                type="range"
                min="50"
                max="100"
                className={styles.slider}
                value={jpegQuality}
                onChange={(e) => onQualityChange(parseInt(e.target.value))}
              />
              <span className={styles.sliderValue}>{jpegQuality}</span>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}
