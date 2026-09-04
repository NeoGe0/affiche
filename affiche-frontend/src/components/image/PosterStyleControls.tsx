import { useId, type ReactNode } from 'react';

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
  const fontSizePercent = asPercent(textOptions.max_font_ratio);
  const textHeightPercent = asPercent(textOptions.text_offset_ratio);
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

        <div className={styles.row}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={textOptions.all_caps}
              onChange={(e) => onTextChange({ all_caps: e.target.checked })}
            />
            <span>All caps</span>
          </label>
        </div>

        <div className={styles.row}>
          <label className={styles.label} htmlFor={`${uid}-position`}>Position</label>
          <select
            id={`${uid}-position`}
            className={styles.select}
            value={textOptions.gravity}
            onChange={(e) => onTextChange({ gravity: e.target.value as TextOptions['gravity'] })}
          >
            {GRAVITY_LABELS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <div className={styles.row}>
          <label
            className={styles.label}
            htmlFor={`${uid}-text-height`}
            title="Distance of the title from the poster edge — higher moves it further in"
          >
            Text height
          </label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-text-height`}
              type="range"
              min="0"
              max="100"
              className={styles.slider}
              value={textHeightPercent}
              onChange={(e) => onTextChange({ text_offset_ratio: fromPercent(e.target.value) })}
            />
            <span className={styles.sliderValue}>{textHeightPercent}%</span>
          </div>
        </div>

        <div className={styles.row}>
          <label
            className={styles.label}
            htmlFor={`${uid}-line-spacing`}
            title="Gap between lines of a multi-line title — negative pulls them together"
          >
            Line spacing
          </label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-line-spacing`}
              type="range"
              min="-20"
              max="100"
              className={styles.slider}
              value={lineSpacingPercent}
              onChange={(e) => onTextChange({ line_spacing_ratio: fromPercent(e.target.value) })}
            />
            <span className={styles.sliderValue}>{lineSpacingPercent}%</span>
          </div>
        </div>

        <div className={styles.row}>
          <label
            className={styles.label}
            htmlFor={`${uid}-text-width`}
            title="How much of the poster's width a line of the title may use"
          >
            Text width
          </label>
          <div className={styles.sliderWrapper}>
            <input
              id={`${uid}-text-width`}
              type="range"
              min="10"
              max="100"
              className={styles.slider}
              value={textWidthPercent}
              onChange={(e) => onTextChange({ max_width_ratio: fromPercent(e.target.value) })}
            />
            <span className={styles.sliderValue}>{textWidthPercent}%</span>
          </div>
        </div>

        <div className={styles.row}>
          <label className={styles.checkbox} title="Break a long title across lines by itself, so it can be drawn larger. Line breaks typed into the title are always kept, and turn this off for that title.">
            <input
              type="checkbox"
              checked={textOptions.auto_wrap}
              onChange={(e) => onTextChange({ auto_wrap: e.target.checked })}
            />
            <span>Auto line breaks</span>
          </label>
        </div>

        <div className={styles.row}>
          <label className={styles.checkbox} title="Start a new line where the title contains one of these separators">
            <input
              type="checkbox"
              checked={textOptions.break_on_symbols}
              onChange={(e) => onTextChange({ break_on_symbols: e.target.checked })}
            />
            <span>Break on “ - ”, “: ”</span>
          </label>
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
      </div>

      {jpegQuality !== undefined && onQualityChange && (
        <div className={styles.group} role="group" aria-labelledby={`${uid}-output`}>
          <h4 className={styles.groupTitle} id={`${uid}-output`}>Output</h4>

          <div className={styles.row}>
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
        </div>
      )}
    </div>
  );
}
