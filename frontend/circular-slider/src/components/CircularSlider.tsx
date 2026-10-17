import {useCallback, useEffect, useRef, useState} from 'react';
import type {KeyboardEvent, PointerEvent} from 'react';
import {SliderCard, type InvoiceCard} from './SliderCard';
import {SliderControls} from './SliderControls';

export interface CircularSliderProps {
  cards: InvoiceCard[];
  radius?: number;
  /** Degrees per second. Positive values rotate clockwise. */
  rotationSpeed?: number;
  autoRotate?: boolean;
  cardWidth?: number;
  cardHeight?: number;
  perspective?: number;
  onOpen?: (card: InvoiceCard) => void;
}

const modulo = (value: number, count: number) => ((value % count) + count) % count;

export function CircularSlider({cards, radius = 330, rotationSpeed = 3, autoRotate = true,
  cardWidth = 132, cardHeight = 190, perspective = 1200, onOpen}: CircularSliderProps) {
  const stage = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const rotation = useRef(0);
  const velocity = useRef(0);
  const target = useRef<number | null>(null);
  const hover = useRef(false);
  const keyboardFocus = useRef(false);
  const visible = useRef(true);
  const cooldown = useRef(0);
  const active = useRef(0);
  const drag = useRef<{id:number; x:number; y:number; startX:number; startY:number; t:number; moved:boolean; card:number | null} | null>(null);
  const [selected, setSelected] = useState(0);
  const [paused, setPaused] = useState(!autoRotate);
  const [reduced, setReduced] = useState(false);
  const [width, setWidth] = useState(1000);
  const count = cards.length;
  const step = 360 / Math.max(1,count);
  const factor = Math.min(1, Math.max(.55, width / 1000));
  const actualRadius = radius * factor;
  const actualWidth = cardWidth * factor;
  const actualHeight = cardHeight * factor;

  useEffect(() => setPaused(!autoRotate), [autoRotate]);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(media.matches);
    update(); media.addEventListener('change',update);
    const observer = new ResizeObserver(entries => setWidth(entries[0].contentRect.width));
    if (stage.current) observer.observe(stage.current);
    const intersection = new IntersectionObserver(entries => {visible.current = entries[0].isIntersecting;});
    if(stage.current) intersection.observe(stage.current);
    return () => {media.removeEventListener('change',update);observer.disconnect();intersection.disconnect();};
  }, []);

  const updateSelection = useCallback(() => {
    if (!count) return;
    const index = modulo(Math.round(-rotation.current / step), count);
    if (index !== active.current) { active.current = index; setSelected(index); }
  }, [count,step]);
  const paint = useCallback(() => {
    if(ring.current) ring.current.style.transform = `rotateY(${rotation.current}deg)`;
    updateSelection();
  }, [updateSelection]);
  const align = useCallback((index:number) => {
    if (!count) return;
    const desired = -modulo(index,count) * step;
    const nearest = rotation.current + modulo(desired - rotation.current + 180,360) - 180;
    velocity.current = 0;
    cooldown.current = performance.now() + 5000;
    if (reduced) { rotation.current = nearest; target.current = null; paint(); }
    else target.current = nearest;
  }, [count,step,reduced,paint]);

  useEffect(() => {
    let frame:number;
    let previous=performance.now();
    const tick=(now:number) => {
      const dt=Math.min(32,now-previous); previous=now;
      if (!document.hidden && !drag.current && count) {
        if (target.current !== null) {
          rotation.current += (target.current - rotation.current) * (reduced ? 1 : 1 - Math.exp(-dt / 115));
          if(Math.abs(target.current-rotation.current)<.03) {rotation.current=target.current;target.current=null;}
          paint();
        } else if (!reduced && Math.abs(velocity.current) > .003) {
          rotation.current += velocity.current * dt;
          velocity.current *= Math.exp(-dt / 220);
          paint();
          if(Math.abs(velocity.current)<=.003) target.current=Math.round(rotation.current/step)*step;
        } else if(visible.current && !paused && !reduced && !hover.current && !keyboardFocus.current && now>cooldown.current) {
          rotation.current += rotationSpeed * dt / 1000;
          // Keep angles numerically stable through long-running sessions.
          if(Math.abs(rotation.current)>3600) rotation.current%=360;
          paint();
        }
      }
      frame=requestAnimationFrame(tick);
    };
    frame=requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [count,paused,reduced,rotationSpeed,step,paint]);

  function pointerDown(event:PointerEvent<HTMLDivElement>) {
    if(!event.isPrimary || event.button!==0) return;
    const element=(event.target as HTMLElement).closest<HTMLElement>('[data-card-index]');
    drag.current={id:event.pointerId,x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY,t:event.timeStamp,moved:false,card:element ? Number(element.dataset.cardIndex) : null};
    velocity.current=0;target.current=null;cooldown.current=performance.now()+5000;
    event.currentTarget.setPointerCapture(event.pointerId);
    event.currentTarget.classList.add('dragging');
  }
  function pointerMove(event:PointerEvent<HTMLDivElement>) {
    const d=drag.current;
    if(!d || d.id!==event.pointerId) return;
    const dx=event.clientX-d.x, elapsed=Math.max(1,event.timeStamp-d.t);
    if(Math.hypot(event.clientX-d.startX,event.clientY-d.startY)>6) d.moved=true;
    const degrees=dx * (width<640 ? .40 : .25);
    target.current=null;
    rotation.current+=degrees;
    velocity.current=elapsed>90 ? 0 : Math.max(-.6,Math.min(.6,velocity.current*.3+(degrees/elapsed)*.7));
    d.x=event.clientX;d.y=event.clientY;d.t=event.timeStamp;
    paint();
  }
  function pointerEnd(event:PointerEvent<HTMLDivElement>) {
    const d=drag.current;
    if(!d || d.id!==event.pointerId) return;
    drag.current=null;
    event.currentTarget.classList.remove('dragging');
    if(event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    if(event.type==='pointercancel') {velocity.current=0;align(active.current);return;}
    if(!d.moved && d.card!==null) {align(d.card);return;}
    if(reduced || event.timeStamp-d.t>90 || Math.abs(velocity.current)<.003) align(active.current);
    cooldown.current=performance.now()+5000;
  }
  function keyDown(event:KeyboardEvent<HTMLDivElement>) {
    if(event.key==='ArrowLeft' || event.key==='ArrowRight') {
      event.preventDefault();align(active.current+(event.key==='ArrowRight'?1:-1));
    } else if(event.key==='Home' || event.key==='End') {
      event.preventDefault();align(event.key==='Home'?0:count-1);
    }
  }
  if (!count) return <p className="py-12 text-center text-white/60">Henüz gösterilecek belge yok.</p>;
  const card=cards[selected] ?? cards[0];
  return <section aria-roledescription="dönen belge koleksiyonu" aria-label="Faturalarınıza üç boyutlu bakış">
    <div className="slider-stage" ref={stage} tabIndex={0}
      aria-label="Belgeleri sürükleyerek veya sağ ve sol ok tuşlarıyla döndürün"
      onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerEnd} onPointerCancel={pointerEnd}
      onLostPointerCapture={event => {if(drag.current) pointerEnd(event);}}
      onMouseEnter={() => {hover.current=true;}} onMouseLeave={() => {hover.current=false;}}
      onFocusCapture={() => {keyboardFocus.current=true;}} onBlurCapture={event => {if(!event.currentTarget.contains(event.relatedTarget as Node)) keyboardFocus.current=false;}}
      onKeyDown={keyDown} style={{perspective:`${perspective}px`}}>
      <div className="floor-glow" aria-hidden="true" />
      <div className="cylinder-camera"><div className="cylinder-ring" ref={ring}>
        {cards.map((item,index) => <SliderCard key={item.id} card={item} index={index} angle={(360/count)*index}
          radius={actualRadius} width={actualWidth} height={actualHeight} selected={index===selected} onSelect={align}/>) }
      </div></div>
    </div>
    <div className="selection-row flex flex-col items-center justify-center gap-2 sm:flex-row sm:gap-5">
      <div className="min-w-0 text-center sm:text-left"><p className="selected-name" title={card.subtitle}>{card.subtitle}</p><p className="selected-status">{card.status}</p></div>
      {onOpen && card.documentId && <button type="button" className="open-document" onClick={() => onOpen(card)}>İncelemeyi aç <span aria-hidden="true">↗</span></button>}
    </div>
    <SliderControls selectedIndex={selected} count={count} paused={paused} reducedMotion={reduced}
      onPrevious={() => align(active.current-1)} onNext={() => align(active.current+1)} onToggle={() => {setPaused(p=>!p);cooldown.current=0;}}/>
    <p className="gesture-hint">Sürükleyin, döndürün. Bir karta dokunup öne getirin.</p>
  </section>;
}
