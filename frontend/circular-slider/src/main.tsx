import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {CircularSlider} from './components/CircularSlider';
import type {InvoiceCard} from './components/SliderCard';

interface Arguments {cards:InvoiceCard[]; autoRotate:boolean; pending:number; revision?:string;}
const fallback:InvoiceCard[]=Array.from({length:14},(_,i)=>({id:`intro-${i}`,title:`Fatura ${String(i+1).padStart(2,'0')}`,subtitle:'Tanıtım kartı · Gerçek fatura değildir',status:'Örnek belge',statusTone:'demo',tone:i%3===1?'charcoal':'paper'}));

// Streamlit's public custom-component message protocol. Only the parent frame
// supplies arguments; actions contain no invoice content or credentials.
const parentOrigin = document.referrer ? new URL(document.referrer).origin : '*';
function send(type:string, payload:Record<string,unknown>={}) {
  if(window.parent!==window) window.parent.postMessage({isStreamlitMessage:true,type,...payload},parentOrigin);
}
function action(action:string, documentId?:string) {
  send('streamlit:setComponentValue',{value:{action,document_id:documentId,event_id:crypto.randomUUID()},dataType:'json'});
}
function App() {
  const [args,setArgs]=useState<Arguments>({cards:fallback,autoRotate:true,pending:0});
  useEffect(()=>{
    const render=(event:MessageEvent)=>{
      if(event.source!==window.parent || event.data?.type!=='streamlit:render') return;
      if(parentOrigin!=='*' && event.origin!==parentOrigin) return;
      const incoming=event.data.args as Arguments;
      setArgs({cards:Array.isArray(incoming.cards) && incoming.cards.length ? incoming.cards:fallback,autoRotate:incoming.autoRotate!==false,pending:Number(incoming.pending)||0});
    };
    window.addEventListener('message',render);
    send('streamlit:componentReady',{apiVersion:1});
    let previousHeight=0;
    const observer=new ResizeObserver(()=>{
      const height=Math.ceil(document.getElementById('root')!.getBoundingClientRect().height);
      if(height!==previousHeight){previousHeight=height;send('streamlit:setFrameHeight',{height});}
    });
    observer.observe(document.getElementById('root')!);
    return ()=>{window.removeEventListener('message',render);observer.disconnect();};
  },[]);
  return <main className="carousel-shell relative overflow-hidden rounded-[24px] bg-ink text-white">
    <div className="aurora" aria-hidden="true"><i/><i/><i/></div>
    <div className="grid-pattern" aria-hidden="true"/>
    <header className="hero-heading relative z-10 mx-auto flex max-w-4xl flex-col items-center px-5 text-center">
      <p className="hero-kicker"><span className="kicker-mark">✳</span>Kanıta dayalı fatura kontrolü</p>
      <h1>Her faturayı kanıtıyla görün.<br/><span>Kararı güvenle verin.</span></h1>
      <p className="hero-description">Bill Vision faturadaki bilgileri okur, siparişle karşılaştırır ve her alanın belgede<br className="hidden sm:block"/> nerede yazdığını gösterir. Belirsizlikler öne çıkar; son karar her zaman sizde.</p>
      <div className="hero-actions flex flex-wrap justify-center gap-3">
        <button type="button" className="upload-action" onClick={()=>action('upload')}><span aria-hidden="true">+</span> Fatura yükle <b aria-hidden="true">→</b></button>
        {args.pending>0 && <button type="button" className="reviews-action" onClick={()=>action('reviews')}>İncelemelere git <em>{args.pending} bekliyor</em></button>}
        <button type="button" className="video-action" onClick={()=>action('video')}><span aria-hidden="true">▷</span> 12 sn tanıtım</button>
      </div>
      <ul className="trust-row" aria-label="Öne çıkanlar">
        <li><i aria-hidden="true">✓</i>Alan bazında belge kanıtı</li>
        <li><i aria-hidden="true">✓</i>Siparişle otomatik kontrol</li>
        <li><i aria-hidden="true">✓</i>Ödeme yapmaz, karar sizde</li>
      </ul>
    </header>
    <CircularSlider cards={args.cards} autoRotate={args.autoRotate} onOpen={card=>action('open',card.documentId)}/>
    <div className="scene-footnote"><span className="live-dot"/>BELGELERİNİZ · KARAR SİZİN<span className="footnote-divider">/</span><span>Temsili kart görünümü</span></div>
  </main>;
}
createRoot(document.getElementById('root')!).render(<App/>);
