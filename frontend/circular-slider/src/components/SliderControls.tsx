interface SliderControlsProps {
  selectedIndex: number;
  count: number;
  paused: boolean;
  reducedMotion: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onToggle: () => void;
}

export function SliderControls({selectedIndex, count, paused, reducedMotion, onPrevious, onNext, onToggle}: SliderControlsProps) {
  return <div className="slider-controls flex items-center justify-center gap-3" aria-label="Dönen belgeler için kontroller">
    <button type="button" className="round-control" aria-label="Önceki belge" onClick={onPrevious}>←</button>
    <span className="counter tabular-nums" aria-live="off">{String(selectedIndex + 1).padStart(2,'0')} <span>/ {count}</span></span>
    <button type="button" className="round-control" aria-label="Sonraki belge" onClick={onNext}>→</button>
    <span className="control-divider" />
    <button type="button" className="motion-control" onClick={onToggle} disabled={reducedMotion}
      aria-label={reducedMotion ? 'Azaltılmış hareket etkin' : paused ? 'Otomatik dönüşü başlat' : 'Otomatik dönüşü duraklat'}
      aria-pressed={!paused && !reducedMotion}>
      <span aria-hidden="true">{paused || reducedMotion ? '▷' : 'Ⅱ'}</span>
      <span>{reducedMotion ? 'Hareket azaltıldı' : paused ? 'Döndür' : 'Duraklat'}</span>
    </button>
  </div>;
}
