/* Reusable validation for Italy/Romania editorial visual interludes.
 * No audio, no adverts, no claims that archive material is a live camera.
 */
const ALLOWED_VIDEO = "videos.pexels.com";
const ALLOWED_POSTER = "images.pexels.com";
const ALLOWED_NASA = "eol.jsc.nasa.gov";
const countryLabel = new Set(["Italia","România"]);
const clean = s => typeof s==="string" ? s.trim() : "";
export function safeLandscapeURL(value,kind) {
  try {
    const u = new URL(value);
    if(u.protocol!=="https:" || u.username || u.password || u.port) return false;
    if(kind==="video") return u.hostname===ALLOWED_VIDEO && /\/video-files\/\d+\/.+\.mp4$/.test(u.pathname);
    if(kind==="poster") return u.hostname===ALLOWED_POSTER && /\/videos\/\d+\/[^/]+\.jpe?g$/i.test(u.pathname);
    if(kind==="nasa") return u.hostname===ALLOWED_NASA && /^\/DatabaseImages\/ESC\/large\/ISS\d+\/ISS\d+-E-\d+\.JPG$/i.test(u.pathname);
    return false;
  }catch{return false;}
}
export function validateLandscape(item){
  if(!item||typeof item!=="object")return null;
  const id=clean(item.id),country=clean(item.country),title=clean(item.title);
  const credit=clean(item.credit),kind=clean(item.kind);
  const license=clean(item.license_url),source=clean(item.source_url),src=clean(item.src);
  if(!/^[a-z0-9_-]{3,52}$/.test(id)||!countryLabel.has(country)||title.length<4||title.length>100)return null;
  if(item.audio_muted!==true||item.editorial_visual===false||item.rights_reviewed!==true)return null;
  if(!credit||credit.length>130||!/^2026-\d\d-\d\d$/.test(clean(item.reviewed_on)))return null;
  if(kind==="video"){
    if(license!=="https://www.pexels.com/license/" && license!=="https://www.pexels.com/it-it/license/")return null;
    if(!safeLandscapeURL(src,"video")||!safeLandscapeURL(item.poster,"poster"))return null;
    if(!/^https:\/\/www\.pexels\.com\/video\/[a-z0-9-]+-\d+\/$/.test(source))return null;
  }else if(kind==="image"){
    if(license!=="https://www.nasa.gov/nasa-brand-center/images-and-media/")return null;
    if(!safeLandscapeURL(src,"nasa")||src!==item.poster)return null;
    if(!/^https:\/\/eol\.jsc\.nasa\.gov\/(?:[Ss]earch[Pp]hotos)\/photo\.pl\?/.test(source))return null;
  }else return null;
  return {id,country,title,credit,kind,src,poster:item.poster,source_url:source,license_url:license};
}
export function parseLandscapeConfig(config){
  if(config?.enabled!==true)return {enabled:false,every:4,duration:20,items:[]};
  const every=Number.isInteger(config.after_news_cards)?Math.max(3,Math.min(15,config.after_news_cards)):4;
  const duration=Number.isInteger(config.duration_seconds)?Math.max(12,Math.min(30,config.duration_seconds)):20;
  const seen=new Set(),items=[];
  for(const raw of Array.isArray(config.items)?config.items:[]){
    const item=validateLandscape(raw);
    if(item && !seen.has(item.id)){items.push(item);seen.add(item.id);}
    if(items.length>=20)break;
  }
  const countries=new Set(items.map(x=>x.country));
  return {enabled:items.length>=2&&countries.size===2,every,duration,items};
}
export function landscapeDue(count,every){
  return Number.isInteger(count)&&count>0&&count%every===0;
}
