// Pure, Node-testable policy for the RDI DJ schedule live promo.
export const DEFAULT_RULES=Object.freeze({enabled:true,durationSeconds:16,everyNewsCards:12,minMinutesBetween:30});
export function validRules(raw){
  const x=raw&&typeof raw==="object"?raw:{};
  return {
    enabled:x.enabled===true,
    durationSeconds:Math.max(8,Math.min(25,Math.round(Number(x.durationSeconds)||16))),
    everyNewsCards:Math.max(6,Math.min(60,Math.round(Number(x.everyNewsCards)||12))),
    minMinutesBetween:Math.max(15,Math.min(180,Math.round(Number(x.minMinutesBetween)||30)))
  };
}
export function eligible({rules,cardsSince,lastShownAt,now,blocked}){
  if(!rules.enabled||blocked)return false;
  if(!Number.isFinite(now)||!Number.isFinite(cardsSince))return false;
  return cardsSince>=rules.everyNewsCards &&
    (lastShownAt===null||now-lastShownAt>=rules.minMinutesBetween*60000);
}
export function priorityBlocked(w){
 return Boolean(w.rdiSpotActive||w.rdiGeoActive||w.rdiTgActive||
   w.rdiWeatherActive||w.rdiCameraActive||w.rdiLandscapeActive);
}
