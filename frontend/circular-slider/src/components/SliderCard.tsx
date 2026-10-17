import type { CSSProperties } from 'react';

export interface InvoiceCard {
  id: string;
  title: string;
  subtitle: string;
  status: string;
  tone?: 'paper' | 'charcoal';
  /** Colour of the status dot; mirrors the review status, never changes it. */
  statusTone?: 'warn' | 'ready' | 'ok' | 'danger' | 'info' | 'violet' | 'muted' | 'demo';
  amount?: string;
  documentId?: string;
}

interface SliderCardProps {
  card: InvoiceCard;
  index: number;
  angle: number;
  radius: number;
  width: number;
  height: number;
  selected: boolean;
  onSelect: (index: number) => void;
}

export function SliderCard({ card, index, angle, radius, width, height, selected, onSelect }: SliderCardProps) {
  const style = {
    width, height, marginLeft: -width / 2, marginTop: -height / 2,
    transform: `rotateY(${angle}deg) translateZ(${radius}px)`,
    '--card-unit': `${width / 132}px`,
  } as CSSProperties;
  return (
    <button
      className={`slider-card ${card.tone === 'charcoal' ? 'charcoal' : 'paper'} ${selected ? 'selected' : ''}`}
      style={style} data-card-index={index} data-angle={angle}
      aria-label={`${card.title}, ${card.status}. Öne getir`}
      aria-pressed={selected}
      onClick={event => { if (event.detail === 0) onSelect(index); }}
      onFocus={() => onSelect(index)}
      type="button"
    >
      <span className="card-face card-front">
        <span className="card-top"><span className="card-symbol">✳</span><span>FATURA</span></span>
        <span className="card-index">{String(index + 1).padStart(2, '0')} / BELGE</span>
        <span className="card-title">{card.title}</span>
        <span className="card-subtitle">{card.subtitle}</span>
        {card.amount ? <span className="card-amount">{card.amount}</span>
          : <span className="document-lines" aria-hidden="true"><i /><i /><i /><i /></span>}
        <span className={`card-footer tone-${card.statusTone ?? 'demo'}`}><span className="card-dot" />{card.status}</span>
      </span>
      <span className="card-face card-back" aria-hidden="true">
        <span className="back-brand">✳</span><span className="back-wordmark">bill vision</span>
        <span className="back-lines"><i /><i /><i /></span>
        <span className="back-caption">HER BELGEDE<br />BİRAZ DAHA NETLİK.</span>
      </span>
    </button>
  );
}
