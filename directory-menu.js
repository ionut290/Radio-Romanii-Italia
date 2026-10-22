(()=>{const buttons=[...document.querySelectorAll("[data-panel]")];
function show(id){
 if(!["home","find","add","manage","volunteer"].includes(id))id="home";
 for(const panel of document.querySelectorAll(".directory-panel")){
  panel.hidden=id==="find"?!["find-panel","businesses"].includes(panel.id):panel.id!==(id==="volunteer"?"volunteer-info":id+"-panel");
 }
 document.body.classList.toggle("view-home",id==="home");
 for(const b of buttons)b.classList.toggle("active",b.dataset.panel===id);
 if(id==="manage")document.dispatchEvent(new Event("directory-manage-open"));
 history.replaceState(null,"",id==="home"?location.pathname:location.pathname+"?tab="+encodeURIComponent(id));
 if(id!=="home")window.scrollTo({top:0,behavior:"instant"});
}
for(const b of buttons)b.addEventListener("click",()=>show(b.dataset.panel));
show(new URLSearchParams(location.search).get("tab")||"home");
document.getElementById("language")?.addEventListener("change",()=>{const l=document.getElementById("language").value;for(const n of document.querySelectorAll("[data-ro]"))n.textContent=n.dataset[l]||n.dataset.ro});
})();