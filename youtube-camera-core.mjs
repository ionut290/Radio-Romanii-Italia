/* Shared, testable rules: never broadcast a discovered webcam without a recorded authorization. */
export const DEFAULT_EVERY = 5;
export const DEFAULT_DURATION = 30;
const text = value => typeof value === 'string' ? value.trim() : '';
const placeholder = s => /^(?:tbd|todo|example|pending|test|placeholder|da verificare|da autorizzare)$/i.test(s);
function safePublicHttps(value){
  try {
    const url = new URL(value);
    if(url.protocol !== 'https:' || url.username || url.password || !url.hostname.includes('.')) return false;
    const host = url.hostname.toLowerCase();
    if(host==='localhost'||host.endsWith('.localhost')||host.endsWith('.local')||host.endsWith('.internal'))return false;
    if(/^\d+\.\d+\.\d+\.\d+$/.test(host))return false;
    return true;
  } catch (_) { return false; }
}
export function validateCamera(camera) {
  if(!camera || typeof camera!=='object') return null;
  const id=text(camera.id),city=text(camera.city),country=text(camera.country);
  const src=text(camera.src),credit=text(camera.credit);
  const reference=text(camera.permission_reference),operator=text(camera.operator);
  const kind=text(camera.kind);
  if(camera.youtube_live_rights!==true || camera.audio_muted!==true) return null;
  if(!id||!city||!country||!operator||!credit||!reference||placeholder(reference)||!safePublicHttps(src)) return null;
  if(!['iframe','image','video'].includes(kind)) return null;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(text(camera.authorized_on))) return null;
  if(!/^[-a-zA-Z0-9_]{1,48}$/.test(id)||city.length>70||country.length>70||credit.length>140)return null;
  return {id,city,country,operator,credit,src,kind,reference,verifiedOn:camera.authorized_on};
}
export function parseCameraConfig(config) {
  if(!config||config.enabled!==true) return {enabled:false,every:DEFAULT_EVERY,duration:DEFAULT_DURATION,cameras:[]};
  const every=Number.isInteger(config.after_news_cards)?Math.max(2,Math.min(20,config.after_news_cards)):DEFAULT_EVERY;
  const duration=Number.isInteger(config.duration_seconds)?Math.max(10,Math.min(60,config.duration_seconds)):DEFAULT_DURATION;
  const seen=new Set(),cameras=[];
  for(const candidate of Array.isArray(config.cameras)?config.cameras:[]) {
    const cam=validateCamera(candidate);
    if(cam&&!seen.has(cam.id)){seen.add(cam.id);cameras.push(cam);}
    if(cameras.length>=24)break; // one loaded at a time, bounded catalog
  }
  return {enabled:cameras.length>0,every,duration,cameras};
}
export function slotDue(completedNewsCards,every) {
  return Number.isInteger(completedNewsCards)&&completedNewsCards>0&&completedNewsCards%every===0;
}
