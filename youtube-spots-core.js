export const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[_-]+/g,' ').replace(/\s+/g,' ').trim();
export function selectCampaign(np,config){
 if(!np?.song||!config)return null;
 const title=normalize([np.song.title,np.song.text].filter(Boolean).join(' '));
 const playlist=normalize(np.playlist);
 const inSpotPlaylist=/^(spot|spots|spoturi|publicitate|pubblicita|advertisements)$/.test(playlist);
 // Never mistake an ordinary song mentioning "spot" for an advertisement.
 const taggedSpot=/^(spot|publicitate|pubblicita)(\s|$)/.test(normalize(np.song.title||np.song.text));
 if(!inSpotPlaylist&&!taggedSpot)return null;
 for(const campaign of config.campaigns||[]){
  if((campaign.songIds||[]).includes(np.song.id)||(campaign.matchAny||[]).some(term=>title.includes(normalize(term))))return campaign;
 }
 // Future spots get nine branded scenes immediately, without paid API calls.
 // This reuses artwork; it does not claim to create new AI photographs.
 const cleanTitle=String(np.song.title||np.song.text||'Spot RDI').replace(/\d{9,}/g,'').replace(/[_]+/g,' ').trim().slice(0,140)||'Spot RDI';
 const art=typeof np.song.art==='string'&&/^https:\/\//.test(np.song.art)?np.song.art:'./RADIO-COVER.jpg';
 const labels=['În direct la RDI','Radio Românii din Italia','Acasă, oriunde ai fi!'];
 return {id:'automatic',title:cleanTitle,footer:'Radio Românii din Italia',sceneSeconds:5,scenes:Array.from({length:9},(_,i)=>({image:art,title:cleanTitle,text:labels[i%labels.length],poster:i%3===0}))};
}
export function sceneAt(campaign,elapsed){
 const index=Math.floor(Math.max(0,Number(elapsed)||0)/(Number(campaign.sceneSeconds)||5))%campaign.scenes.length;
 return {index,scene:campaign.scenes[index]};
}
